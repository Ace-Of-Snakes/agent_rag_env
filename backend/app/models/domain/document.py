"""
Document domain model.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DatabaseConstants
from app.models.domain.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.domain.chunk import Chunk


class DocumentStatus(str, Enum):
    """Document processing status."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base, UUIDMixin, TimestampMixin):
    """
    Represents an uploaded document.
    
    Documents are processed into chunks for RAG retrieval.
    The summary embedding allows for document-level semantic search.
    """
    
    __tablename__ = "documents"
    
    # Basic metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Processing status
    status: Mapped[DocumentStatus] = mapped_column(
        String(20),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Content metadata
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Document summary (for document-level search)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(DatabaseConstants.EMBEDDING_DIMENSIONS),
        nullable=True
    )
    
    # Full-text search vector for keyword search
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR, nullable=True)
    
    # Additional metadata (extracted from document)
    document_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Processing timestamps
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    chunks: Mapped[List["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, filename={self.filename}, "
            f"status={self.status})>"
        )
    
    def mark_processing(self) -> None:
        """Mark document as currently processing."""
        self.status = DocumentStatus.PROCESSING
        self.processing_started_at = datetime.utcnow()
    
    def mark_completed(self, summary: str, page_count: int, total_chunks: int) -> None:
        """Mark document processing as completed."""
        self.status = DocumentStatus.COMPLETED
        self.summary = summary
        self.page_count = page_count
        self.total_chunks = total_chunks
        self.processing_completed_at = datetime.utcnow()
    
    def mark_failed(self, error_message: str) -> None:
        """Mark document processing as failed."""
        self.status = DocumentStatus.FAILED
        self.error_message = error_message
        self.processing_completed_at = datetime.utcnow()
    
    def soft_delete(self) -> None:
        """Soft delete the document."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
