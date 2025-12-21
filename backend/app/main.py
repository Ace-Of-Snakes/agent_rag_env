"""
RAGent - Local RAG System with Multi-Modal Document Processing

Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import create_api_router, setup_exception_handlers, setup_middleware
from app.agents import register_default_tools
from app.core import get_settings, setup_logging
from app.core.logging import get_logger
from app.db import close_db, close_redis, init_db, init_database, init_redis

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Handles startup and shutdown events:
    - Startup: Initialize databases, register tools
    - Shutdown: Close connections gracefully
    """
    # Startup
    logger.info("Starting RAGent application")
    
    # Setup logging
    setup_logging()
    
    # Initialize databases
    await init_db()
    await init_redis()
    
    # Create tables if needed
    await init_database()
    
    # Register agent tools
    register_default_tools()
    
    logger.info("RAGent application started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAGent application")
    
    await close_db()
    await close_redis()
    
    logger.info("RAGent application stopped")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Local RAG System with Multi-Modal Document Processing",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup custom middleware
    setup_middleware(app)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Include API routes
    app.include_router(create_api_router())
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health"
        }
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.debug,
        log_level="info"
    )
