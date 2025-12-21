"""
RAG search tool for document retrieval.
"""

import uuid
from typing import Any, Dict, List, Optional

from app.agents.tools.base import BaseTool, ToolParameter, ToolResult
from app.core.constants import AgentConstants, SearchConstants
from app.core.logging import get_logger
from app.services.search.vector import vector_search_service

logger = get_logger(__name__)


class RAGSearchTool(BaseTool):
    """
    Tool for searching the document knowledge base.
    
    Uses vector similarity search to find relevant document chunks.
    """
    
    @property
    def name(self) -> str:
        return AgentConstants.TOOL_RAG_SEARCH
    
    @property
    def description(self) -> str:
        return (
            "Search through uploaded documents to find relevant information. "
            "Use this tool when the user asks questions that might be answered "
            "by the documents in the knowledge base. Returns the most relevant "
            "text passages from the documents."
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="The search query to find relevant documents",
                required=True
            ),
            ToolParameter(
                name="top_k",
                type="number",
                description=f"Number of results to return (1-{SearchConstants.MAX_TOP_K})",
                required=False,
                default=SearchConstants.DEFAULT_TOP_K
            ),
            ToolParameter(
                name="document_ids",
                type="array",
                description="Optional list of document IDs to search within",
                required=False,
                default=None
            )
        ]
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        Execute RAG search.
        
        Args:
            params: Must contain 'query', optionally 'top_k' and 'document_ids'
            
        Returns:
            ToolResult with search results or error
        """
        # Validate
        error = self.validate_params(params)
        if error:
            return ToolResult.error_result(error)
        
        query = params["query"]
        top_k = params.get("top_k", SearchConstants.DEFAULT_TOP_K)
        document_ids = params.get("document_ids")
        
        # Parse document IDs if provided
        parsed_doc_ids: Optional[List[uuid.UUID]] = None
        if document_ids:
            try:
                parsed_doc_ids = [uuid.UUID(did) for did in document_ids]
            except (ValueError, TypeError) as e:
                return ToolResult.error_result(f"Invalid document ID format: {e}")
        
        try:
            # Perform search
            response = await vector_search_service.search(
                query=query,
                top_k=top_k,
                document_ids=parsed_doc_ids
            )
            
            # Format results for LLM
            if not response.results:
                return ToolResult.success_result(
                    result="No relevant documents found for this query.",
                    query=query,
                    num_results=0
                )
            
            # Build context from results
            context_parts = []
            sources = []
            
            for i, result in enumerate(response.results, 1):
                context_parts.append(
                    f"[Source {i}: {result.document_filename}"
                    f"{f', Page {result.page_number}' if result.page_number else ''}]\n"
                    f"{result.content}"
                )
                sources.append({
                    "index": i,
                    "document": result.document_filename,
                    "page": result.page_number,
                    "chunk_id": str(result.chunk_id),
                    "similarity": result.similarity_score
                })
            
            context = "\n\n---\n\n".join(context_parts)
            
            logger.info(
                "RAG search completed",
                query=query[:50],
                num_results=len(response.results)
            )
            
            return ToolResult.success_result(
                result=context,
                query=query,
                num_results=len(response.results),
                sources=sources,
                search_time_ms=response.search_time_ms
            )
            
        except Exception as e:
            logger.error("RAG search failed", error=str(e))
            return ToolResult.error_result(f"Search failed: {str(e)}")


# Singleton instance
rag_search_tool = RAGSearchTool()