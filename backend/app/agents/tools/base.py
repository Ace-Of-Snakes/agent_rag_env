"""
Base tool interface and types for agent tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = False
    default: Optional[Any] = None


@dataclass
class ToolDefinition:
    """Complete tool definition for LLM."""
    
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM prompt."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default
                }
                for p in self.parameters
            ]
        }


@dataclass
class ToolResult:
    """Result from tool execution."""
    
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success_result(cls, result: Any, **metadata) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, result=result, metadata=metadata)
    
    @classmethod
    def error_result(cls, error: str, **metadata) -> "ToolResult":
        """Create an error result."""
        return cls(success=False, error=error, metadata=metadata)


@runtime_checkable
class Tool(Protocol):
    """Protocol defining the tool interface."""
    
    @property
    def name(self) -> str:
        """Tool name for identification."""
        ...
    
    @property
    def definition(self) -> ToolDefinition:
        """Tool definition for LLM."""
        ...
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute the tool with given parameters."""
        ...


class BaseTool(ABC):
    """
    Abstract base class for tools.
    
    Provides common functionality and enforces the tool interface.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for identification."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM."""
        pass
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters. Override to define parameters."""
        return []
    
    @property
    def definition(self) -> ToolDefinition:
        """Get complete tool definition."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters
        )
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            params: Dictionary of parameter values
            
        Returns:
            ToolResult with success/failure and result/error
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """
        Validate parameters against definition.
        
        Args:
            params: Parameters to validate
            
        Returns:
            Error message if validation fails, None if valid
        """
        for param in self.parameters:
            if param.required and param.name not in params:
                return f"Missing required parameter: {param.name}"
        
        return None
