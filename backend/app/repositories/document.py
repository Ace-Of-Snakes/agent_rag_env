"""
Document repository for document-related database operations.
"""

import uuid
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Document, DocumentStatus
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document entities."""
    
    model = Document
    
    async def get_by_id(
        self,
        id: uuid.UUID,
        include_deleted: bool = False
    ) -> Optional[Document]:
        """
        Get document by ID.
        
        Args:
            id: Document UUID
            include_deleted: Whether to include soft-deleted documents
            
        Returns:
            Document or None
        """
        query = select(Document).where(Document.id == id)
        
        if not include_deleted:
            query = query.where(Document.is_deleted == False)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_hash(self, file_hash: str) -> Optional[Document]:
        """
        Get document by file hash (for deduplication).
        
        Args:
            file_hash: SHA-256 hash of file content
            
        Returns:
            Document or None
        """
        result = await self.session.execute(
            select(Document).where(
                Document.file_hash == file_hash,
                Document.is_deleted == False
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_filename(
        self,
        filename: str,
        original: bool = False
    ) -> Optional[Document]:
        """
        Get document by filename.
        
        Args:
            filename: Filename to search
            original: Search original_filename instead of stored filename
            
        Returns:
            Document or None
        """
        field = Document.original_filename if original else Document.filename
        
        result = await self.session.execute(
            select(Document).where(
                field == filename,
                Document.is_deleted == False
            ).order_by(Document.created_at.desc())
        )
        return result.scalar_one_or_none()
    
    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 20,
        status: Optional[DocumentStatus] = None,
        include_deleted: bool = False
    ) -> tuple[List[Document], int]:
        """
        List documents with filtering and pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            status: Filter by status
            include_deleted: Include soft-deleted documents
            
        Returns:
            Tuple of (documents, total_count)
        """
        # Build base query
        query = select(Document)
        count_query = select(func.count()).select_from(Document)
        
        # Apply filters
        if not include_deleted:
            query = query.where(Document.is_deleted == False)
            count_query = count_query.where(Document.is_deleted == False)
        
        if status:
            query = query.where(Document.status == status)
            count_query = count_query.where(Document.status == status)
        
        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0
        
        # Get paginated results
        query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        documents = list(result.scalars().all())
        
        return documents, total
    
    async def get_pending_documents(self) -> List[Document]:
        """Get all documents pending processing."""
        result = await self.session.execute(
            select(Document).where(
                Document.status == DocumentStatus.PENDING,
                Document.is_deleted == False
            ).order_by(Document.created_at)
        )
        return list(result.scalars().all())
    
    async def get_processing_documents(self) -> List[Document]:
        """Get all documents currently processing."""
        result = await self.session.execute(
            select(Document).where(
                Document.status == DocumentStatus.PROCESSING,
                Document.is_deleted == False
            )
        )
        return list(result.scalars().all())
    
    async def update_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        error_message: Optional[str] = None
    ) -> Optional[Document]:
        """
        Update document processing status.
        
        Args:
            document_id: Document UUID
            status: New status
            error_message: Error message if failed
            
        Returns:
            Updated document or None
        """
        document = await self.get_by_id(document_id)
        if not document:
            return None
        
        document.status = status
        if error_message:
            document.error_message = error_message
        
        await self.session.flush()
        await self.session.refresh(document)
        return document
    
    async def soft_delete(self, document_id: uuid.UUID) -> bool:
        """
        Soft delete a document.
        
        Args:
            document_id: Document UUID
            
        Returns:
            True if deleted, False if not found
        """
        document = await self.get_by_id(document_id)
        if not document:
            return False
        
        document.soft_delete()
        await self.session.flush()
        return True
    
    async def search_by_summary(
        self,
        query_embedding: List[float],
        limit: int = 5
    ) -> List[Document]:
        """
        Search documents by summary embedding similarity.
        
        Args:
            query_embedding: Query vector
            limit: Maximum results
            
        Returns:
            List of matching documents
        """
        from sqlalchemy import text
        
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
        
        result = await self.session.execute(
            text("""
                SELECT * FROM documents
                WHERE summary_embedding IS NOT NULL
                AND is_deleted = false
                AND status = 'completed'
                ORDER BY summary_embedding <=> :embedding::vector
                LIMIT :limit
            """),
            {"embedding": embedding_str, "limit": limit}
        )
        
        return list(result.fetchall())
