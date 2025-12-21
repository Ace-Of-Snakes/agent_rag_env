"""
Database initialization and startup utilities.
"""

from sqlalchemy import text

from app.core.logging import get_logger
from app.db.postgres import get_db_session, get_engine
from app.models.domain import Base

logger = get_logger(__name__)


async def create_extensions() -> None:
    """Create required PostgreSQL extensions."""
    async with get_db_session() as session:
        # Enable pgvector for vector similarity search
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # Enable pg_trgm for fuzzy text matching
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        
        logger.info("PostgreSQL extensions created")


async def create_tables() -> None:
    """Create all database tables."""
    engine = get_engine()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created")


async def init_database() -> None:
    """
    Initialize the database with extensions and tables.
    
    This should be called on application startup.
    """
    logger.info("Initializing database schema")
    
    await create_extensions()
    await create_tables()
    
    logger.info("Database initialization complete")