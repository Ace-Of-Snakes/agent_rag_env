"""
API module for FastAPI routes and middleware.
"""

from app.api.dependencies import CommonDeps, get_db, get_request_id, get_session_id
from app.api.middleware import (
    RequestLoggingMiddleware,
    setup_exception_handlers,
    setup_middleware,
)
from app.api.routes import create_api_router

__all__ = [
    # Dependencies
    "CommonDeps",
    "get_db",
    "get_request_id",
    "get_session_id",
    # Middleware
    "RequestLoggingMiddleware",
    "setup_middleware",
    "setup_exception_handlers",
    # Routes
    "create_api_router",
]
