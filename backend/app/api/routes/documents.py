"""
Document API routes for upload, processing, and search.
"""

import hashlib
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.core.constants import DocumentConstants
from app.core.exceptions import (
    DocumentNotFoundError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.core.logging import get_logger
from app.models.domain import Document, DocumentStatus
from app.models.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    ProcessingProgress,
    SearchResponse,
    SearchResult,
)
from app.services.document import get_document_processor, ProcessingProgress as ProgressData
from app.services.search import vector_search_service

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Upload directory
UPLOAD_DIR = Path("/tmp/ragent/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document for processing.
    
    The document will be queued for processing which includes:
    - Text extraction
    - Vision analysis (for pages with images)
    - Chunking and embedding
    - Summary generation
    
    Use the /documents/{id}/status endpoint to check processing progress.
    """
    settings = get_settings()
    
    # Validate file type
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in DocumentConstants.SUPPORTED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                ext,
                list(DocumentConstants.SUPPORTED_EXTENSIONS)
            )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > settings.document.max_upload_size_bytes:
        raise FileTooLargeError(
            len(content),
            settings.document.max_upload_size_bytes
        )
    
    # Calculate file hash
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Check for duplicate
    result = await db.execute(
        select(Document).where(
            Document.file_hash == file_hash,
            Document.is_deleted == False
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return DocumentUploadResponse(
            id=existing.id,
            filename=existing.filename,
            original_filename=existing.original_filename,
            status=existing.status,
            message="Document already exists"
        )
    
    # Generate unique filename
    doc_id = uuid.uuid4()
    stored_filename = f"{doc_id}{Path(file.filename or 'document.pdf').suffix}"
    file_path = UPLOAD_DIR / stored_filename
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create document record
    document = Document(
        id=doc_id,
        filename=stored_filename,
        original_filename=file.filename or "document.pdf",
        mime_type=file.content_type or "application/pdf",
        file_size_bytes=len(content),
        file_hash=file_hash,
        status=DocumentStatus.PENDING
    )
    
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    logger.info(
        "Document uploaded",
        document_id=str(doc_id),
        filename=file.filename,
        size=len(content)
    )
    
    # Start processing (in background for real implementation)
    # For now, process synchronously
    await _process_document(document, file_path, db)
    
    await db.refresh(document)
    
    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        original_filename=document.original_filename,
        status=document.status,
        message="Document uploaded and processing started"
    )


async def _process_document(
    document: Document,
    file_path: Path,
    db: AsyncSession
):
    """Process a document (should be moved to background task)."""
    processor = get_document_processor()
    
    document.mark_processing()
    await db.commit()
    
    try:
        result = await processor.process_document(
            document_id=str(document.id),
            file_path=file_path,
            filename=document.original_filename
        )
        
        # Update document with results
        document.mark_completed(
            summary=result.summary,
            page_count=result.page_count,
            total_chunks=len(result.chunks)
        )
        document.summary_embedding = result.summary_embedding
        document.metadata = result.metadata
        
        # Save chunks
        from app.models.domain import Chunk
        
        for chunk_data in result.chunks:
            chunk = Chunk(
                document_id=document.id,
                chunk_index=chunk_data.chunk_index,
                page_number=chunk_data.page_number,
                content=chunk_data.content,
                content_type=chunk_data.content_type,
                token_count=chunk_data.token_count,
                embedding=chunk_data.embedding,
                metadata=chunk_data.metadata
            )
            db.add(chunk)
        
        await db.commit()
        
        logger.info(
            "Document processed",
            document_id=str(document.id),
            chunks=len(result.chunks)
        )
        
    except Exception as e:
        document.mark_failed(str(e))
        await db.commit()
        
        logger.error(
            "Document processing failed",
            document_id=str(document.id),
            error=str(e)
        )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[DocumentStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all documents with optional status filter."""
    query = select(Document).where(Document.is_deleted == False)
    
    if status:
        query = query.where(Document.status == status)
    
    query = query.order_by(Document.created_at.desc())
    
    # Count total
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    
    # Get page
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    documents = list(result.scalars().all())
    
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get document details including chunks."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.is_deleted == False
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise DocumentNotFoundError(str(document_id))
    
    return DocumentDetailResponse.model_validate(document)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document (soft delete)."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.is_deleted == False
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise DocumentNotFoundError(str(document_id))
    
    document.soft_delete()
    await db.commit()
    
    logger.info("Document deleted", document_id=str(document_id))


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get document processing status."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise DocumentNotFoundError(str(document_id))
    
    return {
        "document_id": str(document.id),
        "status": document.status,
        "error_message": document.error_message,
        "page_count": document.page_count,
        "total_chunks": document.total_chunks,
        "processing_started_at": document.processing_started_at,
        "processing_completed_at": document.processing_completed_at
    }


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    query: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    document_ids: Optional[str] = Query(None, description="Comma-separated document IDs"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search documents using semantic similarity.
    
    Returns the most relevant chunks from the document collection.
    """
    # Parse document IDs if provided
    doc_ids = None
    if document_ids:
        try:
            doc_ids = [uuid.UUID(did.strip()) for did in document_ids.split(",")]
        except ValueError:
            raise HTTPException(400, "Invalid document ID format")
    
    response = await vector_search_service.search(
        query=query,
        top_k=top_k,
        document_ids=doc_ids,
        session=db
    )
    
    return SearchResponse(
        query=response.query,
        results=[
            SearchResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_filename=r.document_filename,
                content=r.content,
                page_number=r.page_number,
                similarity_score=r.similarity_score,
                metadata=r.metadata
            )
            for r in response.results
        ],
        total_results=response.total_results,
        search_time_ms=response.search_time_ms
    )
