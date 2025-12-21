"""
Agent tools module.

Provides the tool registry and default tools for the agent.
"""

from app.agents.tools.base import BaseTool, Tool, ToolDefinition, ToolParameter, ToolResult
from app.agents.tools.file_reader import FileReaderTool, file_reader_tool
from app.agents.tools.rag import RAGSearchTool, rag_search_tool
from app.agents.tools.registry import ToolRegistry, get_tool, register_tool, tool_registry
from app.agents.tools.web_search import WebSearchTool, web_search_tool


def register_default_tools() -> None:
    """Register all default tools in the global registry."""
    tool_registry.register(rag_search_tool)
    tool_registry.register(web_search_tool)
    tool_registry.register(file_reader_tool)


__all__ = [
    # Base
    "BaseTool",
    "Tool",
    "ToolDefinition",
    "ToolParameter",
    "ToolResult",
    # Registry
    "ToolRegistry",
    "tool_registry",
    "register_tool",
    "get_tool",
    "register_default_tools",
    # Tools
    "RAGSearchTool",
    "rag_search_tool",
    "WebSearchTool",
    "web_search_tool",
    "FileReaderTool",
    "file_reader_tool",
]
