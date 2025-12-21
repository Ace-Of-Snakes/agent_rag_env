"""
Web search service using DuckDuckGo.
"""

from dataclasses import dataclass
from typing import List, Optional

import httpx

from app.core.constants import AgentConstants
from app.core.exceptions import WebSearchError
from app.core.logging import get_logger

logger = get_logger(__name__)

# DuckDuckGo HTML search URL (no API key needed)
DUCKDUCKGO_URL = "https://html.duckduckgo.com/html/"


@dataclass
class WebResult:
    """A single web search result."""
    
    title: str
    url: str
    snippet: str


@dataclass
class WebSearchResponse:
    """Complete web search response."""
    
    query: str
    results: List[WebResult]


class WebSearchService:
    """Service for web search using DuckDuckGo."""
    
    def __init__(
        self,
        timeout: int = AgentConstants.WEB_SEARCH_TIMEOUT_SECONDS,
        max_results: int = AgentConstants.DUCKDUCKGO_MAX_RESULTS
    ):
        self.timeout = timeout
        self.max_results = max_results
    
    async def search(
        self,
        query: str,
        max_results: Optional[int] = None
    ) -> WebSearchResponse:
        """
        Search the web using DuckDuckGo.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            WebSearchResponse with results
        """
        max_results = max_results or self.max_results
        
        logger.info("Performing web search", query=query[:50])
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    DUCKDUCKGO_URL,
                    data={"q": query},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )
                response.raise_for_status()
                
                results = self._parse_results(response.text, max_results)
                
                logger.info(
                    "Web search completed",
                    query=query[:50],
                    results=len(results)
                )
                
                return WebSearchResponse(query=query, results=results)
                
        except httpx.TimeoutException:
            raise WebSearchError(query, "Request timed out")
        except httpx.RequestError as e:
            raise WebSearchError(query, str(e))
    
    def _parse_results(self, html: str, max_results: int) -> List[WebResult]:
        """
        Parse search results from DuckDuckGo HTML response.
        
        Uses simple string parsing to avoid BeautifulSoup dependency.
        """
        results = []
        
        # Find result blocks
        # DuckDuckGo uses class="result" for each result
        result_marker = 'class="result '
        current_pos = 0
        
        while len(results) < max_results:
            # Find next result block
            result_start = html.find(result_marker, current_pos)
            if result_start == -1:
                break
            
            # Find the end of this result block
            next_result = html.find(result_marker, result_start + 1)
            if next_result == -1:
                result_block = html[result_start:]
            else:
                result_block = html[result_start:next_result]
            
            # Extract title and URL
            title, url = self._extract_title_url(result_block)
            
            # Extract snippet
            snippet = self._extract_snippet(result_block)
            
            if title and url:
                results.append(WebResult(
                    title=title,
                    url=url,
                    snippet=snippet or ""
                ))
            
            current_pos = result_start + len(result_marker)
        
        return results
    
    def _extract_title_url(self, block: str) -> tuple[str, str]:
        """Extract title and URL from a result block."""
        title = ""
        url = ""
        
        # Look for the result link
        # Pattern: <a class="result__a" href="...">title</a>
        link_marker = 'class="result__a"'
        link_pos = block.find(link_marker)
        
        if link_pos != -1:
            # Find href
            href_start = block.find('href="', link_pos)
            if href_start != -1:
                href_start += 6
                href_end = block.find('"', href_start)
                if href_end != -1:
                    url = block[href_start:href_end]
                    # DuckDuckGo uses redirect URLs, try to extract actual URL
                    if "uddg=" in url:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                        if "uddg" in parsed:
                            url = urllib.parse.unquote(parsed["uddg"][0])
            
            # Find title text (between > and </a>)
            tag_end = block.find('>', link_pos)
            if tag_end != -1:
                title_end = block.find('</a>', tag_end)
                if title_end != -1:
                    title = block[tag_end + 1:title_end]
                    title = self._clean_html(title)
        
        return title, url
    
    def _extract_snippet(self, block: str) -> str:
        """Extract snippet from a result block."""
        # Look for snippet class
        snippet_marker = 'class="result__snippet"'
        snippet_pos = block.find(snippet_marker)
        
        if snippet_pos != -1:
            tag_end = block.find('>', snippet_pos)
            if tag_end != -1:
                snippet_end = block.find('</a>', tag_end)
                if snippet_end == -1:
                    snippet_end = block.find('</span>', tag_end)
                if snippet_end != -1:
                    snippet = block[tag_end + 1:snippet_end]
                    return self._clean_html(snippet)
        
        return ""
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and decode entities."""
        import html
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Clean whitespace
        text = ' '.join(text.split())
        
        return text.strip()


# Singleton instance
web_search_service = WebSearchService()
