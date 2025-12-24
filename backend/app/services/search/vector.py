"""
Vector search service using pgvector with SQLAlchemy ORM.

This implementation uses pgvector's native SQLAlchemy operators instead of raw SQL,
which avoids parameter binding issues with asyncpg and provides better type safety.
"""

import time
import uuid
from dataclasses import dataclass
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import select, func, and_, literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import DatabaseConstants, SearchConstants
from app.core.exceptions import VectorSearchError
from app.core.logging import get_logger
from app.db.postgres import get_db_session
from app.models.domain import Chunk, Document
from app.services.embedding.service import embedding_service

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_filename: str
    content: str
    page_number: Optional[int]
    similarity_score: float
    metadata: Optional[dict] = None


@dataclass
class SearchResponse:
    """Complete search response."""
    
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float


class VectorSearchService:
    """Service for semantic vector search using pgvector."""
    
    def __init__(self):
        self._settings = get_settings()
    
    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        document_ids: Optional[List[uuid.UUID]] = None,
        session: Optional[AsyncSession] = None
    ) -> SearchResponse:
        """
        Search for relevant chunks using vector similarity.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            document_ids: Filter to specific documents
            session: Database session (creates one if not provided)
            
        Returns:
            SearchResponse with ranked results
        """
        start_time = time.time()
        
        settings = self._settings.search
        top_k = min(top_k or settings.default_top_k, settings.max_top_k)
        min_similarity = min_similarity or settings.min_similarity_threshold
        
        # Generate query embedding
        query_embedding = await embedding_service.embed_text(query)
        
        async def execute_search(session: AsyncSession) -> List[SearchResult]:
            # Use pgvector's cosine_distance operator
            # cosine_distance returns 0 for identical vectors, 2 for opposite
            # similarity = 1 - distance gives us 1 for identical, -1 for opposite
            distance = Chunk.embedding.cosine_distance(query_embedding)
            similarity = (literal(1) - distance).label('similarity')
            
            # Build the query using SQLAlchemy ORM
            stmt = (
                select(
                    Chunk.id.label('chunk_id'),
                    Chunk.document_id,
                    Document.original_filename.label('document_filename'),
                    Chunk.content,
                    Chunk.page_number,
                    Chunk.chunk_metadata.label('metadata'),
                    similarity
                )
                .join(Document, Chunk.document_id == Document.id)
                .where(
                    and_(
                        Chunk.embedding.isnot(None),
                        Document.is_deleted == False,
                        Document.status == 'completed',
                    )
                )
                .order_by(distance)  # Order by distance (ascending = most similar first)
                .limit(top_k)
            )
            
            # Add document filter if specified
            if document_ids:
                stmt = stmt.where(Chunk.document_id.in_(document_ids))
            
            result = await session.execute(stmt)
            rows = result.fetchall()
            
            # Filter by minimum similarity in Python to avoid complex SQL expressions
            # (pgvector distance operators in WHERE clauses can be tricky)
            return [
                SearchResult(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    document_filename=row.document_filename,
                    content=row.content,
                    page_number=row.page_number,
                    similarity_score=float(row.similarity),
                    metadata=row.metadata
                )
                for row in rows
                if float(row.similarity) >= min_similarity
            ]
        
        try:
            if session:
                results = await execute_search(session)
            else:
                async with get_db_session() as session:
                    results = await execute_search(session)
            
            search_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                "Vector search completed",
                query_length=len(query),
                results=len(results),
                search_time_ms=search_time_ms
            )
            
            return SearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                search_time_ms=search_time_ms
            )
            
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            raise VectorSearchError(f"Search failed: {str(e)}")
    
    async def hybrid_search(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        document_ids: Optional[List[uuid.UUID]] = None,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        session: Optional[AsyncSession] = None
    ) -> SearchResponse:
        """
        Hybrid search combining vector similarity and full-text search.
        
        Uses weighted combination of:
        - Vector similarity (cosine distance)
        - Full-text search (ts_rank)
        
        Args:
            query: Search query text
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            document_ids: Filter to specific documents
            vector_weight: Weight for vector similarity (0-1)
            text_weight: Weight for text search (0-1)
            session: Database session
            
        Returns:
            SearchResponse with ranked results
        """
        start_time = time.time()
        
        settings = self._settings.search
        top_k = min(top_k or settings.default_top_k, settings.max_top_k)
        min_similarity = min_similarity or settings.min_similarity_threshold
        
        # Generate query embedding
        query_embedding = await embedding_service.embed_text(query)
        
        async def execute_search(session: AsyncSession) -> List[SearchResult]:
            # Vector similarity score
            distance = Chunk.embedding.cosine_distance(query_embedding)
            vector_score = (literal(1) - distance).label('vector_score')
            
            # Full-text search score using ts_rank
            ts_query = func.plainto_tsquery('english', query)
            text_score = func.coalesce(
                func.ts_rank(Chunk.search_vector, ts_query),
                literal(0)
            ).label('text_score')
            
            # Combined score with weights
            combined_score = (
                literal(vector_weight) * (literal(1) - distance) +
                literal(text_weight) * func.coalesce(func.ts_rank(Chunk.search_vector, ts_query), literal(0))
            ).label('combined_score')
            
            # Build the query
            stmt = (
                select(
                    Chunk.id.label('chunk_id'),
                    Chunk.document_id,
                    Document.original_filename.label('document_filename'),
                    Chunk.content,
                    Chunk.page_number,
                    Chunk.chunk_metadata.label('metadata'),
                    vector_score,
                    text_score,
                    combined_score
                )
                .join(Document, Chunk.document_id == Document.id)
                .where(
                    and_(
                        Chunk.embedding.isnot(None),
                        Document.is_deleted == False,
                        Document.status == 'completed',
                    )
                )
                .order_by(combined_score.desc())  # Higher combined score = better
                .limit(top_k)
            )
            
            # Add document filter if specified
            if document_ids:
                stmt = stmt.where(Chunk.document_id.in_(document_ids))
            
            result = await session.execute(stmt)
            rows = result.fetchall()
            
            return [
                SearchResult(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    document_filename=row.document_filename,
                    content=row.content,
                    page_number=row.page_number,
                    similarity_score=float(row.combined_score),
                    metadata=row.metadata
                )
                for row in rows
                if float(row.vector_score) >= min_similarity
            ]
        
        try:
            if session:
                results = await execute_search(session)
            else:
                async with get_db_session() as session:
                    results = await execute_search(session)
            
            search_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                "Hybrid search completed",
                query=query[:50],
                results=len(results),
                search_time_ms=search_time_ms
            )
            
            return SearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                search_time_ms=search_time_ms
            )
            
        except Exception as e:
            logger.error("Hybrid search failed", error=str(e))
            raise VectorSearchError(f"Hybrid search failed: {str(e)}")
    
    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        session: Optional[AsyncSession] = None
    ) -> List[dict]:
        """
        Search at the document level using summary embeddings.
        
        Args:
            query: Search query
            top_k: Number of documents to return
            
        Returns:
            List of matching documents with scores
        """
        query_embedding = await embedding_service.embed_text(query)
        
        async def execute_search(session: AsyncSession) -> List[dict]:
            # Use document summary embedding for search
            distance = Document.summary_embedding.cosine_distance(query_embedding)
            similarity = (literal(1) - distance).label('similarity')
            
            stmt = (
                select(
                    Document.id,
                    Document.original_filename.label('filename'),
                    Document.summary,
                    similarity
                )
                .where(
                    and_(
                        Document.summary_embedding.isnot(None),
                        Document.is_deleted == False,
                        Document.status == 'completed',
                    )
                )
                .order_by(distance)
                .limit(top_k)
            )
            
            result = await session.execute(stmt)
            
            return [
                {
                    "document_id": str(row.id),
                    "filename": row.filename,
                    "summary": row.summary,
                    "similarity": float(row.similarity)
                }
                for row in result.fetchall()
            ]
        
        if session:
            return await execute_search(session)
        else:
            async with get_db_session() as session:
                return await execute_search(session)


# Singleton instance
vector_search_service = VectorSearchService()