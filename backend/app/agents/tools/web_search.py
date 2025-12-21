"""
Web search tool for external information retrieval.
"""

from typing import Any, Dict, List

from app.agents.tools.base import BaseTool, ToolParameter, ToolResult
from app.core.constants import AgentConstants
from app.core.logging import get_logger
from app.services.search.web import web_search_service

logger = get_logger(__name__)


class WebSearchTool(BaseTool):
    """
    Tool for searching the web.
    
    Uses DuckDuckGo to find relevant web pages.
    """
    
    @property
    def name(self) -> str:
        return AgentConstants.TOOL_WEB_SEARCH
    
    @property
    def description(self) -> str:
        return (
            "Search the web for current information. Use this tool when you need "
            "to find information that might not be in the uploaded documents, "
            "such as recent news, general knowledge, or external references. "
            "Returns titles, URLs, and snippets from web pages."
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="The search query",
                required=True
            ),
            ToolParameter(
                name="max_results",
                type="number",
                description="Maximum number of results (1-10)",
                required=False,
                default=AgentConstants.DUCKDUCKGO_MAX_RESULTS
            )
        ]
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        Execute web search.
        
        Args:
            params: Must contain 'query', optionally 'max_results'
            
        Returns:
            ToolResult with search results or error
        """
        # Validate
        error = self.validate_params(params)
        if error:
            return ToolResult.error_result(error)
        
        query = params["query"]
        max_results = min(params.get("max_results", 5), 10)
        
        try:
            # Perform search
            response = await web_search_service.search(
                query=query,
                max_results=max_results
            )
            
            # Format results for LLM
            if not response.results:
                return ToolResult.success_result(
                    result="No web results found for this query.",
                    query=query,
                    num_results=0
                )
            
            # Build formatted results
            result_parts = []
            sources = []
            
            for i, result in enumerate(response.results, 1):
                result_parts.append(
                    f"[{i}] {result.title}\n"
                    f"URL: {result.url}\n"
                    f"{result.snippet}"
                )
                sources.append({
                    "index": i,
                    "title": result.title,
                    "url": result.url
                })
            
            formatted_results = "\n\n".join(result_parts)
            
            logger.info(
                "Web search completed",
                query=query[:50],
                num_results=len(response.results)
            )
            
            return ToolResult.success_result(
                result=formatted_results,
                query=query,
                num_results=len(response.results),
                sources=sources
            )
            
        except Exception as e:
            logger.error("Web search failed", error=str(e))
            return ToolResult.error_result(f"Web search failed: {str(e)}")


# Singleton instance
web_search_tool = WebSearchTool()