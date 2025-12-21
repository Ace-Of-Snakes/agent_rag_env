"""
Pydantic schemas for document-related API endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from app.models.domain.document import DocumentStatus


# =============================================================================
# Base Schemas
# =============================================================================

class DocumentBase(BaseModel):
    """Base schema for document data."""
    
    filename: str
    original_filename: str
    mime_type: str
    file_size_bytes: int


# =============================================================================
# Request Schemas
# =============================================================================

class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    filename: str
    original_filename: str
    status: DocumentStatus
    message: str = "Document uploaded successfully. Processing started."


# =============================================================================
# Response Schemas
# =============================================================================

class ChunkResponse(BaseModel):
    """Response schema for a document chunk."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    chunk_index: int
    page_number: Optional[int] = None
    content: str
    content_type: str
    token_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(BaseModel):
    """Response schema for a single document."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    filename: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    status: DocumentStatus
    error_message: Optional[str] = None
    page_count: Optional[int] = None
    total_chunks: int = 0
    summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    """Response schema for listing documents."""
    
    documents: List[DocumentResponse]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False


class DocumentDetailResponse(DocumentResponse):
    """Detailed document response including chunks."""
    
    chunks: List[ChunkResponse] = Field(default_factory=list)


# =============================================================================
# Processing Schemas
# =============================================================================

class ProcessingStatus(BaseModel):
    """Schema for document processing status updates."""
    
    document_id: uuid.UUID
    status: DocumentStatus
    progress: float = Field(ge=0, le=100, description="Processing progress percentage")
    current_step: str = ""
    error_message: Optional[str] = None


class ProcessingProgress(BaseModel):
    """Schema for SSE progress updates during processing."""
    
    document_id: uuid.UUID
    step: str
    progress: float
    message: str
    details: Optional[Dict[str, Any]] = None


# =============================================================================
# Search Schemas
# =============================================================================

class SearchResult(BaseModel):
    """Schema for a single search result."""
    
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_filename: str
    content: str
    page_number: Optional[int] = None
    similarity_score: float
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Response schema for document search."""
    
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
