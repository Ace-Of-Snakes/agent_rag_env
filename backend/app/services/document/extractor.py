"""
PDF text and image extraction utilities.
"""

import io
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import fitz  # PyMuPDF

from app.core.constants import DocumentConstants
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PageContent:
    """Content extracted from a single page."""
    
    page_number: int
    text: str
    images: List[bytes]
    image_rects: List[Tuple[float, float, float, float]]  # (x0, y0, x1, y1)
    page_width: float
    page_height: float
    
    @property
    def page_area(self) -> float:
        """Total page area."""
        return self.page_width * self.page_height
    
    @property
    def image_areas(self) -> List[float]:
        """List of image areas."""
        return [
            (x1 - x0) * (y1 - y0)
            for x0, y0, x1, y1 in self.image_rects
        ]
    
    @property
    def total_image_area(self) -> float:
        """Total area covered by images."""
        return sum(self.image_areas)
    
    @property
    def image_coverage_ratio(self) -> float:
        """Ratio of page covered by images."""
        if self.page_area == 0:
            return 0
        return self.total_image_area / self.page_area


@dataclass
class DocumentContent:
    """Complete content extracted from a document."""
    
    pages: List[PageContent]
    metadata: dict
    
    @property
    def page_count(self) -> int:
        """Number of pages."""
        return len(self.pages)
    
    @property
    def full_text(self) -> str:
        """Concatenated text from all pages."""
        return "\n\n".join(page.text for page in self.pages if page.text)


class PDFExtractor:
    """Extract text and images from PDF documents."""
    
    def __init__(
        self,
        dpi: int = DocumentConstants.PDF_DPI,
        image_format: str = DocumentConstants.PDF_IMAGE_FORMAT
    ):
        self.dpi = dpi
        self.image_format = image_format
    
    def extract(self, pdf_path: Path | str) -> DocumentContent:
        """
        Extract all content from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            DocumentContent with pages and metadata
        """
        path = Path(pdf_path)
        
        logger.info("Extracting PDF content", path=str(path))
        
        doc = fitz.open(path)
        
        try:
            pages = []
            for page_num in range(len(doc)):
                page_content = self._extract_page(doc, page_num)
                pages.append(page_content)
            
            metadata = self._extract_metadata(doc)
            
            logger.info(
                "PDF extraction complete",
                pages=len(pages),
                total_images=sum(len(p.images) for p in pages)
            )
            
            return DocumentContent(pages=pages, metadata=metadata)
            
        finally:
            doc.close()
    
    def extract_from_bytes(self, pdf_bytes: bytes) -> DocumentContent:
        """
        Extract content from PDF bytes.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            DocumentContent with pages and metadata
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        try:
            pages = []
            for page_num in range(len(doc)):
                page_content = self._extract_page(doc, page_num)
                pages.append(page_content)
            
            metadata = self._extract_metadata(doc)
            
            return DocumentContent(pages=pages, metadata=metadata)
            
        finally:
            doc.close()
    
    def _extract_page(self, doc: fitz.Document, page_num: int) -> PageContent:
        """Extract content from a single page."""
        page = doc[page_num]
        
        # Extract text
        text = page.get_text("text")
        
        # Get page dimensions
        rect = page.rect
        width = rect.width
        height = rect.height
        
        # Extract images
        images = []
        image_rects = []
        
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                images.append(image_bytes)
                
                # Get image position on page
                for img_rect in page.get_image_rects(xref):
                    image_rects.append((
                        img_rect.x0,
                        img_rect.y0,
                        img_rect.x1,
                        img_rect.y1
                    ))
                    break  # Take first rect for this image
                    
            except Exception as e:
                logger.warning(
                    "Failed to extract image",
                    page=page_num + 1,
                    xref=xref,
                    error=str(e)
                )
        
        return PageContent(
            page_number=page_num + 1,  # 1-indexed
            text=text,
            images=images,
            image_rects=image_rects,
            page_width=width,
            page_height=height
        )
    
    def _extract_metadata(self, doc: fitz.Document) -> dict:
        """Extract document metadata."""
        metadata = doc.metadata or {}
        
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "keywords": metadata.get("keywords", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "page_count": len(doc),
        }
    
    def render_page_as_image(
        self,
        pdf_path: Path | str,
        page_num: int,
        dpi: Optional[int] = None
    ) -> bytes:
        """
        Render a page as an image.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            dpi: Resolution (defaults to instance setting)
            
        Returns:
            PNG image bytes
        """
        dpi = dpi or self.dpi
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        
        doc = fitz.open(pdf_path)
        try:
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix)
            return pix.tobytes(output=self.image_format)
        finally:
            doc.close()
    
    def render_page_from_bytes(
        self,
        pdf_bytes: bytes,
        page_num: int,
        dpi: Optional[int] = None
    ) -> bytes:
        """
        Render a page as an image from PDF bytes.
        
        Args:
            pdf_bytes: PDF file content
            page_num: Page number (0-indexed)
            dpi: Resolution
            
        Returns:
            PNG image bytes
        """
        dpi = dpi or self.dpi
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix)
            return pix.tobytes(output=self.image_format)
        finally:
            doc.close()


# Singleton instance
pdf_extractor = PDFExtractor()
