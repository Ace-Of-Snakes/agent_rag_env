"""
Pydantic schemas for agent and tool-related functionality.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Tool Schemas
# =============================================================================

class ToolParameter(BaseModel):
    """Schema for a tool parameter definition."""
    
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = False
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """Schema for defining a tool available to the agent."""
    
    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)


class ToolCall(BaseModel):
    """Schema for a tool call request from the LLM."""
    
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None  # Why the agent chose this tool


class ToolResult(BaseModel):
    """Schema for tool execution result."""
    
    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0


# =============================================================================
# RAG Tool Schemas
# =============================================================================

class RAGSearchParams(BaseModel):
    """Parameters for RAG search tool."""
    
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.3, ge=0, le=1)
    document_ids: Optional[List[str]] = None  # Filter to specific documents


class RAGSearchResult(BaseModel):
    """Result from RAG search."""
    
    content: str
    document_filename: str
    page_number: Optional[int] = None
    similarity_score: float
    chunk_id: str


class RAGSearchResponse(BaseModel):
    """Response from RAG search tool."""
    
    results: List[RAGSearchResult]
    query: str
    total_results: int


# =============================================================================
# Web Search Schemas
# =============================================================================

class WebSearchParams(BaseModel):
    """Parameters for web search tool."""
    
    query: str
    max_results: int = Field(default=5, ge=1, le=10)


class WebSearchResult(BaseModel):
    """Single result from web search."""
    
    title: str
    url: str
    snippet: str


class WebSearchResponse(BaseModel):
    """Response from web search tool."""
    
    results: List[WebSearchResult]
    query: str


# =============================================================================
# File Reader Schemas
# =============================================================================

class FileReaderParams(BaseModel):
    """Parameters for file reader tool."""
    
    file_path: str
    extract_text: bool = True
    extract_images: bool = False


class FileReaderResponse(BaseModel):
    """Response from file reader tool."""
    
    content: str
    file_type: str
    page_count: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Agent Schemas
# =============================================================================

class AgentThought(BaseModel):
    """Schema for agent's reasoning step."""
    
    thought: str
    action: Optional[str] = None  # Tool to use or "respond"
    action_input: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Schema for complete agent response."""
    
    response: str
    thoughts: List[AgentThought] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    total_tokens_used: int = 0


# =============================================================================
# Context Schemas
# =============================================================================

class AgentContext(BaseModel):
    """Context provided to the agent for each request."""
    
    chat_id: str
    user_message: str
    conversation_history: List[Dict[str, str]]
    available_tools: List[ToolDefinition]
    attached_files: List[Dict[str, Any]] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)
