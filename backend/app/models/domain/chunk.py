"""
Chunk domain model for document segments.
"""

import uuid
from typing import TYPE_CHECKING, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DatabaseConstants
from app.models.domain.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.domain.document import Document


class Chunk(Base, UUIDMixin, TimestampMixin):
    """
    Represents a chunk of document content.
    
    Chunks are segments of documents used for fine-grained retrieval.
    Each chunk has its own embedding for semantic search.
    """
    
    __tablename__ = "chunks"
    
    # Foreign key to parent document
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Chunk ordering within document
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Page reference (if applicable)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Content type (text, vision_description, merged)
    content_type: Mapped[str] = mapped_column(
        String(50),
        default="text",
        nullable=False
    )
    
    # Token count for context management
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Vector embedding for semantic search
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(DatabaseConstants.EMBEDDING_DIMENSIONS),
        nullable=True
    )
    
    # Full-text search vector
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR, nullable=True)
    
    # Additional metadata (position info, source details)
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Relationship to parent document
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks"
    )
    
    def __repr__(self) -> str:
        return (
            f"<Chunk(id={self.id}, document_id={self.document_id}, "
            f"index={self.chunk_index})>"
        )


class ChunkContentType:
    """Content type constants for chunks."""
    
    TEXT = "text"
    VISION = "vision_description"
    MERGED = "merged"
