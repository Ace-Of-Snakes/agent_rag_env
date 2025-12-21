"""
Redis connection and session management with TTL helpers.
"""

import json
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.constants import RedisConstants
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global Redis client (initialized on startup)
_redis_client: Redis | None = None


def get_redis() -> Redis:
    """
    Get the Redis client instance.
    
    Returns:
        Redis: The Redis client
        
    Raises:
        RuntimeError: If Redis is not initialized
    """
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_client


async def init_redis() -> None:
    """Initialize Redis connection."""
    global _redis_client
    
    settings = get_settings()
    
    logger.info("Initializing Redis connection", host=settings.redis.host, port=settings.redis.port)
    
    _redis_client = await redis.from_url(
        settings.redis.url,
        encoding="utf-8",
        decode_responses=True,
    )
    
    # Test connection
    await _redis_client.ping()
    
    logger.info("Redis connection initialized")


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    
    if _redis_client is not None:
        logger.info("Closing Redis connection")
        await _redis_client.close()
        _redis_client = None


class RedisHelper:
    """Helper class for common Redis operations with TTL management."""
    
    def __init__(self, client: Optional[Redis] = None):
        self._client = client
    
    @property
    def client(self) -> Redis:
        """Get Redis client."""
        return self._client or get_redis()
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        key = RedisConstants.SESSION_KEY.format(session_id=session_id)
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def set_session(
        self,
        session_id: str,
        data: dict,
        ttl: Optional[int] = None
    ) -> None:
        """Set session data with TTL."""
        key = RedisConstants.SESSION_KEY.format(session_id=session_id)
        ttl = ttl or get_settings().redis.session_ttl
        await self.client.setex(key, ttl, json.dumps(data))
    
    async def refresh_session(self, session_id: str) -> bool:
        """
        Refresh session TTL on activity.
        
        Returns:
            True if session exists and was refreshed, False otherwise
        """
        key = RedisConstants.SESSION_KEY.format(session_id=session_id)
        ttl = get_settings().redis.session_ttl
        return await self.client.expire(key, ttl)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        key = RedisConstants.SESSION_KEY.format(session_id=session_id)
        return await self.client.delete(key) > 0
    
    # =========================================================================
    # Chat History (Hot Cache)
    # =========================================================================
    
    async def get_chat_history(self, chat_id: str) -> Optional[list]:
        """Get cached chat history."""
        key = RedisConstants.CHAT_HISTORY_KEY.format(chat_id=chat_id)
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def set_chat_history(
        self,
        chat_id: str,
        history: list,
        ttl: Optional[int] = None
    ) -> None:
        """Cache chat history with TTL."""
        key = RedisConstants.CHAT_HISTORY_KEY.format(chat_id=chat_id)
        ttl = ttl or get_settings().redis.chat_history_ttl
        await self.client.setex(key, ttl, json.dumps(history))
    
    async def refresh_chat_history(self, chat_id: str) -> bool:
        """Refresh chat history TTL on message."""
        key = RedisConstants.CHAT_HISTORY_KEY.format(chat_id=chat_id)
        ttl = get_settings().redis.chat_history_ttl
        return await self.client.expire(key, ttl)
    
    async def invalidate_chat_history(self, chat_id: str) -> bool:
        """Invalidate cached chat history."""
        key = RedisConstants.CHAT_HISTORY_KEY.format(chat_id=chat_id)
        return await self.client.delete(key) > 0
    
    # =========================================================================
    # Processing Jobs
    # =========================================================================
    
    async def set_processing_status(
        self,
        job_id: str,
        status: dict,
        ttl: Optional[int] = None
    ) -> None:
        """Set processing job status."""
        key = RedisConstants.PROCESSING_JOB_KEY.format(job_id=job_id)
        ttl = ttl or get_settings().redis.processing_job_ttl
        await self.client.setex(key, ttl, json.dumps(status))
    
    async def get_processing_status(self, job_id: str) -> Optional[dict]:
        """Get processing job status."""
        key = RedisConstants.PROCESSING_JOB_KEY.format(job_id=job_id)
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def delete_processing_status(self, job_id: str) -> bool:
        """Delete processing job status."""
        key = RedisConstants.PROCESSING_JOB_KEY.format(job_id=job_id)
        return await self.client.delete(key) > 0
    
    # =========================================================================
    # Response Cache
    # =========================================================================
    
    async def get_cached_response(self, query_hash: str) -> Optional[dict]:
        """Get cached response for a query."""
        key = RedisConstants.RESPONSE_CACHE_KEY.format(query_hash=query_hash)
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def set_cached_response(
        self,
        query_hash: str,
        response: dict,
        ttl: Optional[int] = None
    ) -> None:
        """Cache a response with TTL."""
        settings = get_settings()
        if not settings.performance.response_cache_enabled:
            return
        
        key = RedisConstants.RESPONSE_CACHE_KEY.format(query_hash=query_hash)
        ttl = ttl or settings.performance.response_cache_ttl
        await self.client.setex(key, ttl, json.dumps(response))
    
    # =========================================================================
    # Generic Operations
    # =========================================================================
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        return await self.client.get(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set a value with optional TTL."""
        if ttl:
            await self.client.setex(key, ttl, json.dumps(value))
        else:
            await self.client.set(key, json.dumps(value))
    
    async def delete(self, key: str) -> bool:
        """Delete a key."""
        return await self.client.delete(key) > 0
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return await self.client.exists(key) > 0


# Singleton instance
redis_helper = RedisHelper()
