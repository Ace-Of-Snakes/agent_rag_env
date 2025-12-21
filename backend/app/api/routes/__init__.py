"""
API routes module.
"""

from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router


def create_api_router() -> APIRouter:
    """Create the main API router with all sub-routers."""
    api_router = APIRouter(prefix="/api/v1")
    
    # Include all route modules
    api_router.include_router(health_router)
    api_router.include_router(chat_router)
    api_router.include_router(documents_router)
    
    return api_router


__all__ = [
    "create_api_router",
    "chat_router",
    "documents_router",
    "health_router",
]
