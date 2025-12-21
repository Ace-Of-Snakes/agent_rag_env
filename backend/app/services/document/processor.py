"""
Document processor that orchestrates the full processing pipeline.
"""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Callable, List, Optional

from app.core.config import get_settings
from app.core.constants import ChunkingStrategy
from app.core.exceptions import DocumentProcessingError
from app.core.logging import get_logger
from app.models.domain.chunk import ChunkContentType
from app.models.domain.document import DocumentStatus
from app.services.document.chunker import TextChunk, TextChunker, get_chunker
from app.services.document.extractor import DocumentContent, PDFExtractor, pdf_extractor
from app.services.embedding.service import embedding_service
from app.services.llm.text import text_service
from app.services.llm.vision import vision_service

logger = get_logger(__name__)


@dataclass
class ProcessingProgress:
    """Progress update during document processing."""
    
    document_id: str
    step: str
    progress: float  # 0-100
    message: str
    details: Optional[dict] = None


@dataclass
class ProcessedChunk:
    """A fully processed chunk ready for storage."""
    
    chunk_index: int
    page_number: Optional[int]
    content: str
    content_type: str
    token_count: int
    embedding: List[float]
    metadata: Optional[dict] = None


@dataclass
class ProcessedDocument:
    """Result of document processing."""
    
    document_id: str
    filename: str
    file_hash: str
    page_count: int
    summary: str
    summary_embedding: List[float]
    chunks: List[ProcessedChunk]
    metadata: dict
    processing_time_seconds: float


class DocumentProcessor:
    """
    Orchestrates the full document processing pipeline.
    
    Pipeline steps:
    1. Extract text and images from PDF
    2. Analyze pages with vision model (if significant images)
    3. Chunk content (text + vision descriptions)
    4. Generate embeddings for chunks
    5. Generate document summary and embedding
    """
    
    def __init__(
        self,
        extractor: Optional[PDFExtractor] = None,
        chunker: Optional[TextChunker] = None
    ):
        self._settings = get_settings()
        self._extractor = extractor or pdf_extractor
        self._chunker = chunker or get_chunker(ChunkingStrategy.FIXED_SIZE)
    
    async def process_document(
        self,
        document_id: str,
        file_path: Path | str,
        filename: str,
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None
    ) -> ProcessedDocument:
        """
        Process a document through the full pipeline.
        
        Args:
            document_id: Unique document identifier
            file_path: Path to the document file
            filename: Original filename
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessedDocument with all chunks and embeddings
        """
        start_time = datetime.utcnow()
        path = Path(file_path)
        
        def report_progress(step: str, progress: float, message: str, details: dict = None):
            if progress_callback:
                progress_callback(ProcessingProgress(
                    document_id=document_id,
                    step=step,
                    progress=progress,
                    message=message,
                    details=details
                ))
        
        try:
            # Step 1: Calculate file hash
            report_progress("hashing", 5, "Calculating file hash")
            file_hash = self._calculate_hash(path)
            
            # Step 2: Extract content
            report_progress("extraction", 10, "Extracting text and images")
            content = self._extractor.extract(path)
            
            logger.info(
                "Content extracted",
                document_id=document_id,
                pages=content.page_count
            )
            
            # Step 3: Process with vision model (if needed)
            report_progress("vision", 20, "Analyzing visual content")
            vision_descriptions = await self._process_vision(
                content,
                document_id,
                lambda p: report_progress("vision", 20 + p * 0.2, f"Analyzing page visuals")
            )
            
            # Step 4: Chunk content
            report_progress("chunking", 45, "Splitting into chunks")
            chunks = self._chunk_content(content, vision_descriptions)
            
            logger.info(
                "Content chunked",
                document_id=document_id,
                num_chunks=len(chunks)
            )
            
            # Step 5: Generate embeddings
            report_progress("embedding", 50, "Generating embeddings")
            chunk_embeddings = await self._generate_chunk_embeddings(
                chunks,
                lambda p: report_progress("embedding", 50 + p * 0.3, f"Embedding chunks")
            )
            
            # Step 6: Generate summary
            report_progress("summarization", 85, "Generating document summary")
            summary = await self._generate_summary(chunks, filename)
            
            # Step 7: Embed summary
            report_progress("summary_embedding", 95, "Embedding summary")
            summary_embedding = await embedding_service.embed_text(summary)
            
            # Build processed chunks
            processed_chunks = [
                ProcessedChunk(
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    content=chunk.content,
                    content_type=chunk.content_type,
                    token_count=chunk.estimate_tokens(),
                    embedding=embedding,
                    metadata=chunk.metadata
                )
                for chunk, embedding in zip(chunks, chunk_embeddings)
            ]
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            report_progress("complete", 100, "Processing complete")
            
            logger.info(
                "Document processing complete",
                document_id=document_id,
                chunks=len(processed_chunks),
                processing_time_seconds=processing_time
            )
            
            return ProcessedDocument(
                document_id=document_id,
                filename=filename,
                file_hash=file_hash,
                page_count=content.page_count,
                summary=summary,
                summary_embedding=summary_embedding,
                chunks=processed_chunks,
                metadata=content.metadata,
                processing_time_seconds=processing_time
            )
            
        except Exception as e:
            logger.error(
                "Document processing failed",
                document_id=document_id,
                error=str(e)
            )
            raise DocumentProcessingError(document_id, str(e))
    
    async def process_document_stream(
        self,
        document_id: str,
        file_path: Path | str,
        filename: str
    ) -> AsyncGenerator[ProcessingProgress, None]:
        """
        Process document with streaming progress updates.
        
        Yields:
            ProcessingProgress updates during processing
        """
        progress_updates = []
        
        def collect_progress(progress: ProcessingProgress):
            progress_updates.append(progress)
        
        # Start processing in background-ish manner
        # For true async, would need task queue
        result = await self.process_document(
            document_id=document_id,
            file_path=file_path,
            filename=filename,
            progress_callback=collect_progress
        )
        
        for progress in progress_updates:
            yield progress
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    async def _process_vision(
        self,
        content: DocumentContent,
        document_id: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> List[TextChunk]:
        """
        Process pages with vision model where appropriate.
        
        Args:
            content: Extracted document content
            document_id: Document identifier for logging
            progress_callback: Progress callback (0-1)
            
        Returns:
            List of vision description chunks
        """
        vision_chunks = []
        pages_to_analyze = []
        
        # Determine which pages need vision analysis
        for page in content.pages:
            if vision_service.should_analyze_page(
                page_image_bytes=b"",  # Not used with current implementation
                page_area=page.page_area,
                image_areas=page.image_areas
            ):
                pages_to_analyze.append(page)
        
        if not pages_to_analyze:
            logger.info(
                "No pages require vision analysis",
                document_id=document_id
            )
            return vision_chunks
        
        logger.info(
            "Analyzing pages with vision model",
            document_id=document_id,
            pages_to_analyze=len(pages_to_analyze)
        )
        
        for i, page in enumerate(pages_to_analyze):
            if progress_callback:
                progress_callback(i / len(pages_to_analyze))
            
            try:
                # Get page image
                page_image = self._extractor.render_page_as_image(
                    pdf_path=Path(),  # Would need actual path
                    page_num=page.page_number - 1
                )
                
                # Analyze with vision model
                description = await vision_service.analyze_page(
                    page_image=page_image,
                    page_number=page.page_number,
                    extracted_text=page.text[:500] if page.text else ""
                )
                
                if description and "no significant visual elements" not in description.lower():
                    vision_chunks.append(TextChunk(
                        content=description,
                        chunk_index=0,
                        page_number=page.page_number,
                        content_type=ChunkContentType.VISION
                    ))
                    
            except Exception as e:
                logger.warning(
                    "Vision analysis failed for page",
                    document_id=document_id,
                    page=page.page_number,
                    error=str(e)
                )
        
        return vision_chunks
    
    def _chunk_content(
        self,
        content: DocumentContent,
        vision_chunks: List[TextChunk]
    ) -> List[TextChunk]:
        """
        Chunk document content with vision descriptions.
        
        Args:
            content: Extracted document content
            vision_chunks: Vision model descriptions
            
        Returns:
            List of merged and indexed chunks
        """
        all_chunks = []
        
        for page in content.pages:
            if not page.text.strip():
                continue
            
            # Chunk this page's text
            page_chunks = self._chunker.chunk_text(
                text=page.text,
                page_number=page.page_number,
                content_type=ChunkContentType.TEXT
            )
            
            # Get vision chunks for this page
            page_vision = [
                v for v in vision_chunks
                if v.page_number == page.page_number
            ]
            
            # Merge if there are vision chunks
            if page_vision:
                page_chunks = self._chunker.merge_page_chunks(
                    text_chunks=page_chunks,
                    vision_chunks=page_vision
                )
            
            all_chunks.extend(page_chunks)
        
        # Reindex all chunks
        for i, chunk in enumerate(all_chunks):
            chunk.chunk_index = i
        
        return all_chunks
    
    async def _generate_chunk_embeddings(
        self,
        chunks: List[TextChunk],
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> List[List[float]]:
        """Generate embeddings for all chunks."""
        texts = [chunk.content for chunk in chunks]
        
        embeddings = await embedding_service.embed_texts(texts)
        
        if progress_callback:
            progress_callback(1.0)
        
        return embeddings
    
    async def _generate_summary(
        self,
        chunks: List[TextChunk],
        filename: str
    ) -> str:
        """Generate document summary from chunks."""
        # Use first N chunks for summary
        sample_chunks = [c.content for c in chunks[:10]]
        
        summary = await text_service.summarize_document(
            chunks=sample_chunks,
            filename=filename
        )
        
        return summary


# Factory function
def get_document_processor() -> DocumentProcessor:
    """Get a configured document processor."""
    return DocumentProcessor()
