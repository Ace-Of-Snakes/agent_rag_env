"""
Chunk repository for chunk-related database operations.
"""

import uuid
from typing import List, Optional

from sqlalchemy import select, func, text, and_, literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Chunk, Document
from app.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[Chunk]):
    """Repository for Chunk entities."""
    
    model = Chunk
    
    async def get_by_document(
        self,
        document_id: uuid.UUID,
        page_numbers: Optional[List[int]] = None
    ) -> List[Chunk]:
        """
        Get all chunks for a document.
        
        Args:
            document_id: Document UUID
            page_numbers: Optional filter for specific pages
            
        Returns:
            List of chunks ordered by index
        """
        query = select(Chunk).where(
            Chunk.document_id == document_id
        )
        
        if page_numbers:
            query = query.where(Chunk.page_number.in_(page_numbers))
        
        query = query.order_by(Chunk.chunk_index)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_page(
        self,
        document_id: uuid.UUID,
        page_number: int
    ) -> List[Chunk]:
        """
        Get chunks for a specific page.
        
        Args:
            document_id: Document UUID
            page_number: Page number
            
        Returns:
            List of chunks for the page
        """
        result = await self.session.execute(
            select(Chunk).where(
                Chunk.document_id == document_id,
                Chunk.page_number == page_number
            ).order_by(Chunk.chunk_index)
        )
        return list(result.scalars().all())
    
    async def count_by_document(self, document_id: uuid.UUID) -> int:
        """
        Count chunks for a document.
        
        Args:
            document_id: Document UUID
            
        Returns:
            Chunk count
        """
        result = await self.session.execute(
            select(func.count()).select_from(Chunk).where(
                Chunk.document_id == document_id
            )
        )
        return result.scalar() or 0
    
    async def delete_by_document(self, document_id: uuid.UUID) -> int:
        """
        Delete all chunks for a document.
        
        Args:
            document_id: Document UUID
            
        Returns:
            Number of deleted chunks
        """
        from sqlalchemy import delete
        
        result = await self.session.execute(
            delete(Chunk).where(Chunk.document_id == document_id)
        )
        await self.session.flush()
        return result.rowcount or 0
    
    async def create_many(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Create multiple chunks efficiently.
        
        Args:
            chunks: List of chunks to create
            
        Returns:
            Created chunks
        """
        self.session.add_all(chunks)
        await self.session.flush()
        return chunks
    
    async def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 5,
        min_similarity: float = 0.3,
        document_ids: Optional[List[uuid.UUID]] = None
    ) -> List[dict]:
        """
        Search for similar chunks using vector similarity.
        
        Uses pgvector's native SQLAlchemy operators for clean parameter handling.
        
        Args:
            query_embedding: Query vector
            limit: Maximum results
            min_similarity: Minimum similarity threshold (0-1)
            document_ids: Optional filter to specific documents
            
        Returns:
            List of results with chunk info and similarity
        """
        # Calculate cosine distance and similarity using pgvector operators
        distance = Chunk.embedding.cosine_distance(query_embedding)
        similarity = (literal(1) - distance).label('similarity')
        
        # Build the query using SQLAlchemy ORM
        stmt = (
            select(
                Chunk.id,
                Chunk.document_id,
                Chunk.content,
                Chunk.page_number,
                Chunk.chunk_index,
                Chunk.content_type,
                Chunk.chunk_metadata.label('metadata'),
                Document.original_filename,
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
            .order_by(distance)  # Ascending = most similar first
            .limit(limit)
        )
        
        # Add document filter if specified
        if document_ids:
            stmt = stmt.where(Chunk.document_id.in_(document_ids))
        
        result = await self.session.execute(stmt)
        rows = result.fetchall()
        
        # Filter by minimum similarity and build result list
        return [
            {
                "chunk_id": row.id,
                "document_id": row.document_id,
                "content": row.content,
                "page_number": row.page_number,
                "chunk_index": row.chunk_index,
                "content_type": row.content_type,
                "metadata": row.metadata,
                "filename": row.original_filename,
                "original_filename": row.original_filename,
                "similarity": float(row.similarity)
            }
            for row in rows
            if float(row.similarity) >= min_similarity
        ]
    
    async def update_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: List[float]
    ) -> Optional[Chunk]:
        """
        Update a chunk's embedding.
        
        Args:
            chunk_id: Chunk UUID
            embedding: New embedding vector
            
        Returns:
            Updated chunk or None
        """
        chunk = await self.get_by_id(chunk_id)
        if not chunk:
            return None
        
        chunk.embedding = embedding
        await self.session.flush()
        await self.session.refresh(chunk)
        return chunk
    
    async def update_search_vector(self, chunk_id: uuid.UUID) -> Optional[Chunk]:
        """
        Update the full-text search vector for a chunk.
        
        Args:
            chunk_id: Chunk UUID
            
        Returns:
            Updated chunk or None
        """
        from sqlalchemy import update
        
        await self.session.execute(
            text("""
                UPDATE chunks 
                SET search_vector = to_tsvector('english', content)
                WHERE id = :chunk_id
            """),
            {"chunk_id": str(chunk_id)}
        )
        await self.session.flush()
        
        return await self.get_by_id(chunk_id)
