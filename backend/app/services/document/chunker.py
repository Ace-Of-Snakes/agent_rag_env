"""
Text chunking service with multiple strategies.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from app.core.config import get_settings
from app.core.constants import ChunkingStrategy
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """A chunk of text with metadata."""
    
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    start_char: int = 0
    end_char: int = 0
    content_type: str = "text"
    metadata: Optional[dict] = None
    
    @property
    def char_count(self) -> int:
        """Number of characters in the chunk."""
        return len(self.content)
    
    def estimate_tokens(self) -> int:
        """Rough estimate of token count (avg 4 chars per token)."""
        return len(self.content) // 4


class TextChunker:
    """Service for splitting text into chunks."""
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        strategy: str = ChunkingStrategy.FIXED_SIZE
    ):
        settings = get_settings()
        self.chunk_size = chunk_size or settings.document.chunk_size
        self.chunk_overlap = chunk_overlap or settings.document.chunk_overlap
        self.strategy = strategy
    
    def chunk_text(
        self,
        text: str,
        page_number: Optional[int] = None,
        content_type: str = "text"
    ) -> List[TextChunk]:
        """
        Split text into chunks using the configured strategy.
        
        Args:
            text: Text to chunk
            page_number: Source page number
            content_type: Type of content (text, vision_description, merged)
            
        Returns:
            List of TextChunk objects
        """
        if not text.strip():
            return []
        
        if self.strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_by_paragraph(text, page_number, content_type)
        elif self.strategy == ChunkingStrategy.SEMANTIC:
            return self._chunk_semantic(text, page_number, content_type)
        else:
            return self._chunk_fixed_size(text, page_number, content_type)
    
    def _chunk_fixed_size(
        self,
        text: str,
        page_number: Optional[int],
        content_type: str
    ) -> List[TextChunk]:
        """Chunk by fixed character count with overlap."""
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end in last 20% of chunk
                search_start = end - int(self.chunk_size * 0.2)
                search_text = text[search_start:end]
                
                # Find last sentence boundary
                for sep in ['. ', '.\n', '? ', '?\n', '! ', '!\n']:
                    last_sep = search_text.rfind(sep)
                    if last_sep != -1:
                        end = search_start + last_sep + len(sep)
                        break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append(TextChunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    page_number=page_number,
                    start_char=start,
                    end_char=end,
                    content_type=content_type
                ))
                chunk_index += 1
            
            # Move start with overlap
            start = end - self.chunk_overlap
            if start >= len(text) - self.chunk_overlap:
                break
        
        return chunks
    
    def _chunk_by_paragraph(
        self,
        text: str,
        page_number: Optional[int],
        content_type: str
    ) -> List[TextChunk]:
        """Chunk by paragraphs, combining small ones."""
        # Split on double newlines or multiple newlines
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        char_pos = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                char_pos += 2  # Account for split characters
                continue
            
            # If adding this paragraph exceeds chunk size
            if current_chunk and len(current_chunk) + len(para) > self.chunk_size:
                chunks.append(TextChunk(
                    content=current_chunk,
                    chunk_index=chunk_index,
                    page_number=page_number,
                    start_char=current_start,
                    end_char=char_pos,
                    content_type=content_type
                ))
                chunk_index += 1
                current_chunk = para
                current_start = char_pos
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                    current_start = char_pos
            
            char_pos += len(para) + 2
        
        # Add remaining content
        if current_chunk:
            chunks.append(TextChunk(
                content=current_chunk,
                chunk_index=chunk_index,
                page_number=page_number,
                start_char=current_start,
                end_char=len(text),
                content_type=content_type
            ))
        
        return chunks
    
    def _chunk_semantic(
        self,
        text: str,
        page_number: Optional[int],
        content_type: str
    ) -> List[TextChunk]:
        """
        Chunk by semantic boundaries (headers, sections).
        Falls back to paragraph chunking for now.
        """
        # Simple implementation: split on headers or large gaps
        # Could be enhanced with actual semantic analysis
        
        # Try to find section headers
        header_pattern = r'^(?:#{1,6}\s+.+|[A-Z][A-Za-z\s]+:|\d+\.\s+.+)$'
        
        lines = text.split('\n')
        chunks = []
        current_section = []
        current_start = 0
        chunk_index = 0
        char_pos = 0
        
        for line in lines:
            # Check if this looks like a header
            is_header = re.match(header_pattern, line.strip())
            
            if is_header and current_section:
                # Start new section
                section_text = '\n'.join(current_section).strip()
                if section_text:
                    chunks.append(TextChunk(
                        content=section_text,
                        chunk_index=chunk_index,
                        page_number=page_number,
                        start_char=current_start,
                        end_char=char_pos,
                        content_type=content_type
                    ))
                    chunk_index += 1
                
                current_section = [line]
                current_start = char_pos
            else:
                current_section.append(line)
            
            char_pos += len(line) + 1
        
        # Add remaining content
        if current_section:
            section_text = '\n'.join(current_section).strip()
            if section_text:
                chunks.append(TextChunk(
                    content=section_text,
                    chunk_index=chunk_index,
                    page_number=page_number,
                    start_char=current_start,
                    end_char=len(text),
                    content_type=content_type
                ))
        
        # If chunks are too large, sub-chunk them
        final_chunks = []
        for chunk in chunks:
            if len(chunk.content) > self.chunk_size * 1.5:
                sub_chunks = self._chunk_fixed_size(
                    chunk.content,
                    chunk.page_number,
                    chunk.content_type
                )
                for i, sub in enumerate(sub_chunks):
                    sub.chunk_index = len(final_chunks)
                    final_chunks.append(sub)
            else:
                chunk.chunk_index = len(final_chunks)
                final_chunks.append(chunk)
        
        return final_chunks
    
    def merge_page_chunks(
        self,
        text_chunks: List[TextChunk],
        vision_chunks: List[TextChunk]
    ) -> List[TextChunk]:
        """
        Merge text and vision description chunks.
        
        Args:
            text_chunks: Chunks from text extraction
            vision_chunks: Chunks from vision model descriptions
            
        Returns:
            Merged chunks with combined content
        """
        if not vision_chunks:
            return text_chunks
        
        if not text_chunks:
            return vision_chunks
        
        # Simple merge: append vision descriptions to text chunks
        # Could be more sophisticated with positional merging
        merged = []
        
        for i, text_chunk in enumerate(text_chunks):
            # Find vision chunks for the same page
            page_vision = [
                v for v in vision_chunks
                if v.page_number == text_chunk.page_number
            ]
            
            if page_vision:
                # Append vision descriptions
                vision_text = "\n\n[Visual Content]\n" + "\n".join(
                    v.content for v in page_vision
                )
                merged_content = text_chunk.content + vision_text
                
                merged.append(TextChunk(
                    content=merged_content,
                    chunk_index=i,
                    page_number=text_chunk.page_number,
                    start_char=text_chunk.start_char,
                    end_char=text_chunk.end_char,
                    content_type="merged"
                ))
            else:
                text_chunk.chunk_index = i
                merged.append(text_chunk)
        
        # Re-chunk if merged chunks are too large
        final_chunks = []
        for chunk in merged:
            if len(chunk.content) > self.chunk_size * 1.5:
                sub_chunks = self._chunk_fixed_size(
                    chunk.content,
                    chunk.page_number,
                    chunk.content_type
                )
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)
        
        # Reindex
        for i, chunk in enumerate(final_chunks):
            chunk.chunk_index = i
        
        return final_chunks


# Factory function
def get_chunker(strategy: str = ChunkingStrategy.FIXED_SIZE) -> TextChunker:
    """Get a chunker with the specified strategy."""
    return TextChunker(strategy=strategy)
