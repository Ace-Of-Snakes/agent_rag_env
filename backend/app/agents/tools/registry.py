"""
Tool registry for dynamic tool management.
"""

from typing import Dict, List, Optional, Type

from app.agents.tools.base import BaseTool, Tool, ToolDefinition
from app.core.exceptions import ToolNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """
    Registry for managing available tools.
    
    Provides registration, lookup, and enumeration of tools.
    Implements the registry pattern for extensibility.
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """
        Register a tool instance.
        
        Args:
            tool: Tool instance to register
        """
        if tool.name in self._tools:
            logger.warning(
                "Overwriting existing tool",
                tool_name=tool.name
            )
        
        self._tools[tool.name] = tool
        logger.info("Tool registered", tool_name=tool.name)
    
    def register_class(self, tool_class: Type[BaseTool]) -> None:
        """
        Register a tool class (instantiates it).
        
        Args:
            tool_class: Tool class to instantiate and register
        """
        tool = tool_class()
        self.register(tool)
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a tool by name.
        
        Args:
            name: Tool name to unregister
            
        Returns:
            True if tool was removed, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            logger.info("Tool unregistered", tool_name=name)
            return True
        return False
    
    def get(self, name: str) -> Tool:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance
            
        Raises:
            ToolNotFoundError: If tool not found
        """
        if name not in self._tools:
            raise ToolNotFoundError(name, self.list_names())
        return self._tools[name]
    
    def get_optional(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name, returning None if not found.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None
        """
        return self._tools.get(name)
    
    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
    
    def list_names(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())
    
    def list_tools(self) -> List[Tool]:
        """Get list of all registered tools."""
        return list(self._tools.values())
    
    def get_definitions(self) -> List[ToolDefinition]:
        """Get definitions of all registered tools."""
        return [tool.definition for tool in self._tools.values()]
    
    def get_all_definitions(self) -> List[ToolDefinition]:
        """Alias for get_definitions - get all tool definitions."""
        return self.get_definitions()
    
    def get_definitions_dict(self) -> List[Dict]:
        """Get definitions as dictionaries for LLM prompt."""
        return [tool.definition.to_dict() for tool in self._tools.values()]
    
    def clear(self) -> None:
        """Remove all registered tools."""
        self._tools.clear()
        logger.info("Tool registry cleared")


# Global registry instance
tool_registry = ToolRegistry()


def register_tool(tool: Tool) -> None:
    """Register a tool in the global registry."""
    tool_registry.register(tool)


def get_tool(name: str) -> Tool:
    """Get a tool from the global registry."""
    return tool_registry.get(name)