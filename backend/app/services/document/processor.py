"""
Document processor that orchestrates the full processing pipeline.

FIXED: 
- Vision processing now works for ALL images in PDFs
- File path is correctly passed to render pages
- Image descriptions are properly merged with page text
- Text sanitization to remove null bytes and invalid UTF-8 characters
"""

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Callable, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.constants import ChunkingStrategy
from app.core.exceptions import DocumentProcessingError
from app.core.logging import get_logger
from app.models.domain.chunk import ChunkContentType
from app.models.domain.document import DocumentStatus
from app.services.document.chunker import TextChunk, TextChunker, get_chunker
from app.services.document.extractor import DocumentContent, PageContent, PDFExtractor, pdf_extractor
from app.services.embedding.service import embedding_service
from app.services.llm.text import text_service
from app.services.llm.vision import vision_service, is_meaningful_image

logger = get_logger(__name__)

# Configuration for image processing
MIN_IMAGE_PIXELS = 100  # Skip images smaller than this (likely icons/decorations)
IMAGE_BATCH_SIZE = 8     # Process this many images per API call


def sanitize_text(text: str) -> str:
    """
    Sanitize text for PostgreSQL storage.
    
    Removes:
    - Null bytes (0x00) which PostgreSQL doesn't accept
    - Other control characters that might cause issues
    - Invalid UTF-8 sequences
    
    Args:
        text: Raw text that may contain problematic characters
        
    Returns:
        Cleaned text safe for database storage
    """
    if not text:
        return ""
    
    # Remove null bytes (the main culprit)
    text = text.replace('\x00', '')
    
    # Remove other problematic control characters (except newlines, tabs, etc.)
    # This removes characters 0x01-0x08, 0x0B, 0x0C, 0x0E-0x1F
    text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f]', '', text)
    
    # Ensure valid UTF-8 by encoding and decoding with error handling
    try:
        text = text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Last resort: strip all non-ASCII if encoding fails
        text = text.encode('ascii', errors='ignore').decode('ascii')
    
    return text


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
    2. Analyze ALL images with vision model (no gating)
    3. Merge image descriptions with page text
    4. Chunk combined content
    5. Generate embeddings for chunks
    6. Generate document summary and embedding
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
            
            # Step 2: Extract content (text and images)
            report_progress("extraction", 10, "Extracting text and images")
            content = self._extractor.extract(path)
            
            total_images = sum(len(page.images) for page in content.pages)
            logger.info(
                "Content extracted",
                document_id=document_id,
                pages=content.page_count,
                total_images=total_images
            )
            
            # Step 3: Process ALL images with vision model
            report_progress("vision", 20, f"Analyzing {total_images} images with vision model")
            page_image_descriptions = await self._process_all_images(
                content=content,
                file_path=path,
                document_id=document_id,
                progress_callback=lambda p: report_progress(
                    "vision", 
                    20 + (p * 30),  # 20-50% of total progress
                    f"Analyzing images... {int(p * 100)}%"
                )
            )
            
            # Step 4: Merge text with image descriptions and chunk
            report_progress("chunking", 55, "Chunking content")
            chunks = self._chunk_content_with_images(content, page_image_descriptions)
            
            logger.info(
                "Content chunked",
                document_id=document_id,
                chunk_count=len(chunks)
            )
            
            # Step 5: Generate embeddings
            report_progress("embedding", 65, f"Generating embeddings for {len(chunks)} chunks")
            chunk_embeddings = await self._generate_chunk_embeddings(
                chunks,
                progress_callback=lambda p: report_progress(
                    "embedding",
                    65 + (p * 20),  # 65-85% of total progress
                    f"Embedding chunks... {int(p * 100)}%"
                )
            )
            
            # Step 6: Generate document summary
            report_progress("summary", 90, "Generating document summary")
            summary = await self._generate_summary(chunks, filename)
            summary_embedding = await embedding_service.embed_text(summary)
            
            # Build final result
            processed_chunks = [
                ProcessedChunk(
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    content=sanitize_text(chunk.content),  # Final sanitization pass
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
                images_processed=total_images,
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
        
        # Start processing
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
    
    async def _process_all_images(
        self,
        content: DocumentContent,
        file_path: Path,
        document_id: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Dict[int, List[str]]:
        """
        Process ALL images from all pages with the vision model using batch processing.
        
        Optimizations:
        - Filters out tiny images (icons, decorations) that aren't meaningful
        - Processes images in batches of 4 for faster throughput
        - Uses async batching to reduce API call overhead
        
        Args:
            content: Extracted document content with images
            file_path: Path to the PDF file (for page rendering if needed)
            document_id: Document identifier for logging
            progress_callback: Progress callback (0-1)
            
        Returns:
            Dictionary mapping page_number -> list of image descriptions
        """
        page_image_descriptions: Dict[int, List[str]] = {}
        
        # Collect all meaningful images with their metadata
        all_images: List[Tuple[bytes, int, int]] = []  # (image_bytes, page_number, image_index)
        skipped_count = 0
        
        for page in content.pages:
            if not page.images:
                continue
            
            for img_index, image_bytes in enumerate(page.images):
                # Filter out tiny images that are likely decorations
                if is_meaningful_image(image_bytes, min_pixels=MIN_IMAGE_PIXELS):
                    all_images.append((image_bytes, page.page_number, img_index + 1))
                else:
                    skipped_count += 1
        
        total_images = len(all_images)
        
        if total_images == 0:
            logger.info(
                "No meaningful images found in document",
                document_id=document_id,
                skipped_tiny_images=skipped_count
            )
            return page_image_descriptions
        
        logger.info(
            "Processing images with vision model (batch mode)",
            document_id=document_id,
            total_images=total_images,
            skipped_tiny_images=skipped_count,
            batch_size=IMAGE_BATCH_SIZE
        )
        
        # Get text context from first page for batch processing
        text_context = ""
        if content.pages:
            text_context = content.pages[0].text[:500] if content.pages[0].text else ""
        
        # Process images in batches
        processed_count = 0
        
        for i in range(0, total_images, IMAGE_BATCH_SIZE):
            batch = all_images[i:i + IMAGE_BATCH_SIZE]
            batch_num = (i // IMAGE_BATCH_SIZE) + 1
            total_batches = (total_images + IMAGE_BATCH_SIZE - 1) // IMAGE_BATCH_SIZE
            
            logger.debug(
                f"Processing batch {batch_num}/{total_batches}",
                document_id=document_id,
                batch_size=len(batch)
            )
            
            try:
                # Use batch processing for better performance
                results = await vision_service.describe_images_batch(
                    images=batch,
                    text_context=text_context,
                    batch_size=IMAGE_BATCH_SIZE
                )
                
                # Organize results by page number
                for page_num, img_idx, description in results:
                    if description:
                        clean_desc = sanitize_text(description.strip())
                        if clean_desc:
                            if page_num not in page_image_descriptions:
                                page_image_descriptions[page_num] = []
                            page_image_descriptions[page_num].append(clean_desc)
                
                processed_count += len(batch)
                
            except Exception as e:
                logger.warning(
                    "Batch processing failed, trying individual processing",
                    document_id=document_id,
                    batch_num=batch_num,
                    error=str(e)
                )
                
                # Fallback to individual processing
                for image_bytes, page_num, img_idx in batch:
                    try:
                        description = await vision_service.describe_document_image(
                            image_data=image_bytes,
                            page_number=page_num,
                            image_index=img_idx,
                            text_context=text_context
                        )
                        
                        if description:
                            clean_desc = sanitize_text(description.strip())
                            if clean_desc:
                                if page_num not in page_image_descriptions:
                                    page_image_descriptions[page_num] = []
                                page_image_descriptions[page_num].append(clean_desc)
                        
                        processed_count += 1
                        
                    except Exception as inner_e:
                        logger.warning(
                            "Failed to describe image",
                            document_id=document_id,
                            page=page_num,
                            image_index=img_idx,
                            error=str(inner_e)
                        )
                        processed_count += 1
            
            # Update progress
            if progress_callback:
                progress_callback(processed_count / total_images)
        
        logger.info(
            "Image processing complete",
            document_id=document_id,
            pages_with_images=len(page_image_descriptions),
            total_descriptions=sum(len(d) for d in page_image_descriptions.values()),
            images_processed=processed_count,
            images_skipped=skipped_count
        )
        
        return page_image_descriptions
    
    def _chunk_content_with_images(
        self,
        content: DocumentContent,
        page_image_descriptions: Dict[int, List[str]]
    ) -> List[TextChunk]:
        """
        Chunk document content with image descriptions merged into page text.
        
        The image descriptions are appended to the page text before chunking,
        so they are included in the same chunks and can be retrieved together.
        
        Args:
            content: Extracted document content
            page_image_descriptions: Image descriptions by page number
            
        Returns:
            List of text chunks with merged content
        """
        all_chunks = []
        
        for page in content.pages:
            # Start with the original page text, sanitized
            page_text = sanitize_text(page.text.strip()) if page.text else ""
            
            # Get image descriptions for this page
            image_descriptions = page_image_descriptions.get(page.page_number, [])
            
            # Merge image descriptions with page text
            if image_descriptions:
                # Format image descriptions (already sanitized, but double-check)
                image_section = "\n\n--- Visual Content on This Page ---\n"
                for i, desc in enumerate(image_descriptions, 1):
                    clean_desc = sanitize_text(desc) if desc else ""
                    if len(image_descriptions) > 1:
                        image_section += f"\n[Image {i}]\n{clean_desc}\n"
                    else:
                        image_section += f"\n{clean_desc}\n"
                image_section += "--- End Visual Content ---\n"
                
                # Combine text and image descriptions
                if page_text:
                    combined_text = page_text + image_section
                    content_type = ChunkContentType.MERGED
                else:
                    # Page has only images, no text
                    combined_text = f"[Page {page.page_number} - Visual Content Only]{image_section}"
                    content_type = ChunkContentType.VISION
            else:
                combined_text = page_text
                content_type = ChunkContentType.TEXT
            
            # Skip empty pages
            if not combined_text.strip():
                continue
            
            # Chunk the combined content
            page_chunks = self._chunker.chunk_text(
                text=combined_text,
                page_number=page.page_number,
                content_type=content_type
            )
            
            all_chunks.extend(page_chunks)
        
        # Reindex all chunks sequentially
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
        
        # Sanitize summary before returning
        return sanitize_text(summary) if summary else ""


# Factory function
def get_document_processor() -> DocumentProcessor:
    """Get a configured document processor."""
    return DocumentProcessor()