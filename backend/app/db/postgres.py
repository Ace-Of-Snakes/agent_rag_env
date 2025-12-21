"""
PostgreSQL database connection and session management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global engine and session factory (initialized on startup)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Get the database engine instance.
    
    Returns:
        AsyncEngine: The database engine
        
    Raises:
        RuntimeError: If engine is not initialized
    """
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get the session factory instance.
    
    Returns:
        async_sessionmaker: The session factory
        
    Raises:
        RuntimeError: If session factory is not initialized
    """
    if _session_factory is None:
        raise RuntimeError("Session factory not initialized. Call init_db() first.")
    return _session_factory


async def init_db() -> None:
    """Initialize database engine and session factory."""
    global _engine, _session_factory
    
    settings = get_settings()
    
    logger.info("Initializing database connection", url=settings.database.async_url.split("@")[1])
    
    _engine = create_async_engine(
        settings.database.async_url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_timeout=settings.database.pool_timeout,
        pool_recycle=settings.database.pool_recycle,
        echo=settings.debug,
    )
    
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    logger.info("Database connection initialized")


async def close_db() -> None:
    """Close database connections."""
    global _engine, _session_factory
    
    if _engine is not None:
        logger.info("Closing database connection")
        await _engine.dispose()
        _engine = None
        _session_factory = None


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as an async context manager.
    
    Yields:
        AsyncSession: Database session
        
    Example:
        async with get_db_session() as session:
            result = await session.execute(query)
    """
    session_factory = get_session_factory()
    session = session_factory()
    
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get a database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with get_db_session() as session:
        yield session