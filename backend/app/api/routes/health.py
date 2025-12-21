"""
Health check API routes.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.db.redis import get_redis
from app.services.llm.client import ollama_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db)
):
    """
    Detailed health check with dependency status.
    
    Checks:
    - PostgreSQL connection
    - Redis connection
    - Ollama availability
    """
    settings = get_settings()
    health = {
        "status": "healthy",
        "version": settings.app_version,
        "services": {}
    }
    
    # Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        health["services"]["postgres"] = {
            "status": "healthy",
            "host": settings.database.host
        }
    except Exception as e:
        health["services"]["postgres"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"
    
    # Check Redis
    try:
        redis = get_redis()
        await redis.ping()
        health["services"]["redis"] = {
            "status": "healthy",
            "host": settings.redis.host
        }
    except Exception as e:
        health["services"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"
    
    # Check Ollama
    try:
        is_healthy = await ollama_client.health_check()
        if is_healthy:
            models = await ollama_client.list_models()
            health["services"]["ollama"] = {
                "status": "healthy",
                "url": settings.ollama.base_url,
                "available_models": len(models)
            }
        else:
            health["services"]["ollama"] = {
                "status": "unhealthy",
                "error": "Health check failed"
            }
            health["status"] = "degraded"
    except Exception as e:
        health["services"]["ollama"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"
    
    return health


@router.get("/health/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db)
):
    """
    Readiness check for container orchestration.
    
    Returns 200 only if all critical dependencies are available.
    """
    try:
        # Check critical dependencies
        await db.execute(text("SELECT 1"))
        
        redis = get_redis()
        await redis.ping()
        
        # Ollama is optional for readiness
        return {"ready": True}
        
    except Exception as e:
        return {"ready": False, "error": str(e)}, 503
