"""
File reader tool for reading uploaded files.
"""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.base import BaseTool, ToolParameter, ToolResult
from app.core.constants import AgentConstants
from app.core.logging import get_logger
from app.db.postgres import get_db_session
from app.models.domain import Document, DocumentStatus

logger = get_logger(__name__)


class FileReaderTool(BaseTool):
    """
    Tool for reading content from uploaded files.
    
    Retrieves the full text content of a document from the database.
    """
    
    @property
    def name(self) -> str:
        return AgentConstants.TOOL_FILE_READER
    
    @property
    def description(self) -> str:
        return (
            "Read the full content of an uploaded document. Use this when you need "
            "to see the complete text of a specific document rather than just "
            "searching for relevant passages. Provide either the document ID or filename."
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="document_id",
                type="string",
                description="The UUID of the document to read",
                required=False
            ),
            ToolParameter(
                name="filename",
                type="string",
                description="The filename of the document to read",
                required=False
            ),
            ToolParameter(
                name="page_numbers",
                type="array",
                description="Optional list of specific page numbers to read",
                required=False,
                default=None
            )
        ]
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        Execute file reading.
        
        Args:
            params: Must contain either 'document_id' or 'filename'
            
        Returns:
            ToolResult with document content or error
        """
        document_id = params.get("document_id")
        filename = params.get("filename")
        page_numbers = params.get("page_numbers")
        
        if not document_id and not filename:
            return ToolResult.error_result(
                "Must provide either 'document_id' or 'filename'"
            )
        
        try:
            async with get_db_session() as session:
                # Find the document
                document = await self._find_document(
                    session, document_id, filename
                )
                
                if not document:
                    return ToolResult.error_result(
                        f"Document not found: {document_id or filename}"
                    )
                
                if document.status != DocumentStatus.COMPLETED:
                    return ToolResult.error_result(
                        f"Document is not ready (status: {document.status})"
                    )
                
                # Get chunks
                content = await self._get_document_content(
                    session, document, page_numbers
                )
                
                logger.info(
                    "File read completed",
                    document_id=str(document.id),
                    filename=document.filename
                )
                
                return ToolResult.success_result(
                    result=content,
                    document_id=str(document.id),
                    filename=document.filename,
                    page_count=document.page_count
                )
                
        except Exception as e:
            logger.error("File read failed", error=str(e))
            return ToolResult.error_result(f"Failed to read file: {str(e)}")
    
    async def _find_document(
        self,
        session: AsyncSession,
        document_id: Optional[str],
        filename: Optional[str]
    ) -> Optional[Document]:
        """Find document by ID or filename."""
        if document_id:
            try:
                doc_uuid = uuid.UUID(document_id)
                result = await session.execute(
                    select(Document).where(
                        Document.id == doc_uuid,
                        Document.is_deleted == False
                    )
                )
                return result.scalar_one_or_none()
            except ValueError:
                return None
        
        if filename:
            result = await session.execute(
                select(Document).where(
                    Document.filename == filename,
                    Document.is_deleted == False
                ).order_by(Document.created_at.desc())
            )
            return result.scalar_one_or_none()
        
        return None
    
    async def _get_document_content(
        self,
        session: AsyncSession,
        document: Document,
        page_numbers: Optional[List[int]]
    ) -> str:
        """Get document content from chunks."""
        from sqlalchemy import select as sa_select
        from app.models.domain import Chunk
        
        query = sa_select(Chunk).where(
            Chunk.document_id == document.id
        ).order_by(Chunk.chunk_index)
        
        if page_numbers:
            query = query.where(Chunk.page_number.in_(page_numbers))
        
        result = await session.execute(query)
        chunks = result.scalars().all()
        
        if not chunks:
            return document.summary or "No content available."
        
        # Format content with page markers
        content_parts = []
        current_page = None
        
        for chunk in chunks:
            if chunk.page_number and chunk.page_number != current_page:
                content_parts.append(f"\n--- Page {chunk.page_number} ---\n")
                current_page = chunk.page_number
            content_parts.append(chunk.content)
        
        return "\n".join(content_parts)


# Singleton instance
file_reader_tool = FileReaderTool()