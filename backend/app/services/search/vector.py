"""
Vector search service using pgvector.
"""

import uuid
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select, text
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
    """Service for semantic vector search."""
    
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
            min_similarity: Minimum similarity threshold
            document_ids: Filter to specific documents
            session: Database session (creates one if not provided)
            
        Returns:
            SearchResponse with ranked results
        """
        import time
        start_time = time.time()
        
        settings = self._settings.search
        top_k = min(top_k or settings.default_top_k, settings.max_top_k)
        min_similarity = min_similarity or settings.min_similarity_threshold
        
        # Generate query embedding
        query_embedding = await embedding_service.embed_text(query)
        
        async def execute_search(session: AsyncSession) -> List[SearchResult]:
            # Build the query using pgvector's cosine distance
            # Lower distance = higher similarity
            # similarity = 1 - distance
            
            embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
            
            # Base query with similarity calculation
            query_sql = text("""
                SELECT 
                    c.id as chunk_id,
                    c.document_id,
                    d.filename as document_filename,
                    c.content,
                    c.page_number,
                    c.metadata,
                    1 - (c.embedding <=> :embedding::vector) as similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE 
                    c.embedding IS NOT NULL
                    AND d.is_deleted = false
                    AND d.status = 'completed'
                    AND 1 - (c.embedding <=> :embedding::vector) >= :min_similarity
                    {document_filter}
                ORDER BY c.embedding <=> :embedding::vector
                LIMIT :top_k
            """.format(
                document_filter="AND c.document_id = ANY(:document_ids)" if document_ids else ""
            ))
            
            params = {
                "embedding": embedding_str,
                "min_similarity": min_similarity,
                "top_k": top_k,
            }
            
            if document_ids:
                params["document_ids"] = [str(did) for did in document_ids]
            
            result = await session.execute(query_sql, params)
            rows = result.fetchall()
            
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
        session: Optional[AsyncSession] = None
    ) -> SearchResponse:
        """
        Hybrid search combining vector similarity and keyword matching.
        
        Uses weighted combination of:
        - Vector similarity (cosine)
        - Full-text search (tsvector)
        """
        import time
        start_time = time.time()
        
        settings = self._settings.search
        top_k = min(top_k or settings.default_top_k, settings.max_top_k)
        min_similarity = min_similarity or settings.min_similarity_threshold
        
        # Generate query embedding
        query_embedding = await embedding_service.embed_text(query)
        
        async def execute_search(session: AsyncSession) -> List[SearchResult]:
            embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
            
            # Hybrid query combining vector and text search
            query_sql = text("""
                WITH vector_results AS (
                    SELECT 
                        c.id,
                        c.document_id,
                        c.content,
                        c.page_number,
                        c.metadata,
                        1 - (c.embedding <=> :embedding::vector) as vector_score
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE 
                        c.embedding IS NOT NULL
                        AND d.is_deleted = false
                        AND d.status = 'completed'
                        {document_filter}
                ),
                text_results AS (
                    SELECT 
                        c.id,
                        ts_rank(c.search_vector, plainto_tsquery(:query)) as text_score
                    FROM chunks c
                    WHERE c.search_vector IS NOT NULL
                )
                SELECT 
                    v.id as chunk_id,
                    v.document_id,
                    d.filename as document_filename,
                    v.content,
                    v.page_number,
                    v.metadata,
                    (v.vector_score * :vector_weight + COALESCE(t.text_score, 0) * :keyword_weight) as combined_score
                FROM vector_results v
                LEFT JOIN text_results t ON v.id = t.id
                JOIN documents d ON v.document_id = d.id
                WHERE v.vector_score >= :min_similarity
                ORDER BY combined_score DESC
                LIMIT :top_k
            """.format(
                document_filter="AND c.document_id = ANY(:document_ids)" if document_ids else ""
            ))
            
            params = {
                "embedding": embedding_str,
                "query": query,
                "min_similarity": min_similarity,
                "top_k": top_k,
                "vector_weight": settings.vector_weight,
                "keyword_weight": settings.keyword_weight,
            }
            
            if document_ids:
                params["document_ids"] = [str(did) for did in document_ids]
            
            result = await session.execute(query_sql, params)
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
            embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
            
            query_sql = text("""
                SELECT 
                    id,
                    filename,
                    summary,
                    1 - (summary_embedding <=> :embedding::vector) as similarity
                FROM documents
                WHERE 
                    summary_embedding IS NOT NULL
                    AND is_deleted = false
                    AND status = 'completed'
                ORDER BY summary_embedding <=> :embedding::vector
                LIMIT :top_k
            """)
            
            result = await session.execute(query_sql, {
                "embedding": embedding_str,
                "top_k": top_k
            })
            
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
