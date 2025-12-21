"""
FastAPI dependencies for request handling.
"""

import uuid
from typing import Optional

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.db.redis import redis_helper


async def get_request_id(
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
) -> str:
    """
    Get or generate a request ID for tracing.
    
    Uses X-Request-ID header if provided, otherwise generates a new UUID.
    """
    return x_request_id or str(uuid.uuid4())


async def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Optional[str]:
    """Get session ID from header if provided."""
    return x_session_id


async def refresh_session(
    session_id: Optional[str] = Depends(get_session_id)
) -> None:
    """
    Refresh session TTL on activity.
    
    Called as a dependency to automatically extend session lifetime
    when the user makes requests.
    """
    if session_id:
        await redis_helper.refresh_session(session_id)


class CommonDeps:
    """
    Common dependencies bundled together.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(deps: CommonDeps = Depends()):
            db = deps.db
            request_id = deps.request_id
    """
    
    def __init__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
        request_id: str = Depends(get_request_id),
        session_id: Optional[str] = Depends(get_session_id),
        _: None = Depends(refresh_session)
    ):
        self.request = request
        self.db = db
        self.request_id = request_id
        self.session_id = session_id
