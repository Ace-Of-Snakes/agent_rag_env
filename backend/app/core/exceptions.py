"""
Custom exception hierarchy for RAGent.
All application-specific exceptions inherit from RAGentError.
"""

from typing import Any, Dict, Optional

from app.core.constants import HTTPStatus


class RAGentError(Exception):
    """Base exception for all RAGent errors."""
    
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    default_message: str = "An unexpected error occurred"
    
    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


# =============================================================================
# Document Processing Errors
# =============================================================================

class DocumentError(RAGentError):
    """Base exception for document-related errors."""
    
    status_code = HTTPStatus.BAD_REQUEST
    default_message = "Document processing error"


class DocumentNotFoundError(DocumentError):
    """Raised when a document is not found."""
    
    status_code = HTTPStatus.NOT_FOUND
    default_message = "Document not found"
    
    def __init__(self, document_id: str):
        super().__init__(
            message=f"Document with ID '{document_id}' not found",
            details={"document_id": document_id}
        )


class UnsupportedFileTypeError(DocumentError):
    """Raised when an unsupported file type is uploaded."""
    
    default_message = "Unsupported file type"
    
    def __init__(self, file_type: str, supported_types: list[str]):
        super().__init__(
            message=f"File type '{file_type}' is not supported",
            details={
                "provided_type": file_type,
                "supported_types": supported_types
            }
        )


class FileTooLargeError(DocumentError):
    """Raised when an uploaded file exceeds size limits."""
    
    default_message = "File size exceeds limit"
    
    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            message=f"File size ({file_size} bytes) exceeds maximum ({max_size} bytes)",
            details={
                "file_size_bytes": file_size,
                "max_size_bytes": max_size
            }
        )


class DocumentProcessingError(DocumentError):
    """Raised when document processing fails."""
    
    default_message = "Failed to process document"
    
    def __init__(self, document_id: str, reason: str):
        super().__init__(
            message=f"Failed to process document '{document_id}': {reason}",
            details={"document_id": document_id, "reason": reason}
        )


# =============================================================================
# LLM Errors
# =============================================================================

class LLMError(RAGentError):
    """Base exception for LLM-related errors."""
    
    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    default_message = "LLM service error"


class OllamaConnectionError(LLMError):
    """Raised when unable to connect to Ollama."""
    
    default_message = "Unable to connect to Ollama service"
    
    def __init__(self, url: str, reason: Optional[str] = None):
        message = f"Unable to connect to Ollama at '{url}'"
        if reason:
            message += f": {reason}"
        super().__init__(
            message=message,
            details={"ollama_url": url, "reason": reason}
        )


class ModelNotFoundError(LLMError):
    """Raised when a requested model is not available."""
    
    status_code = HTTPStatus.NOT_FOUND
    default_message = "Model not found"
    
    def __init__(self, model_name: str):
        super().__init__(
            message=f"Model '{model_name}' is not available in Ollama",
            details={"model_name": model_name}
        )


class GenerationError(LLMError):
    """Raised when LLM generation fails."""
    
    default_message = "Text generation failed"


class EmbeddingError(LLMError):
    """Raised when embedding generation fails."""
    
    default_message = "Embedding generation failed"


# =============================================================================
# Search Errors
# =============================================================================

class SearchError(RAGentError):
    """Base exception for search-related errors."""
    
    default_message = "Search error"


class VectorSearchError(SearchError):
    """Raised when vector search fails."""
    
    default_message = "Vector search failed"


class WebSearchError(SearchError):
    """Raised when web search fails."""
    
    default_message = "Web search failed"
    
    def __init__(self, query: str, reason: str):
        super().__init__(
            message=f"Web search failed for query '{query}': {reason}",
            details={"query": query, "reason": reason}
        )


# =============================================================================
# Chat Errors
# =============================================================================

class ChatError(RAGentError):
    """Base exception for chat-related errors."""
    
    default_message = "Chat error"


class ChatNotFoundError(ChatError):
    """Raised when a chat session is not found."""
    
    status_code = HTTPStatus.NOT_FOUND
    default_message = "Chat session not found"
    
    def __init__(self, chat_id: str):
        super().__init__(
            message=f"Chat session '{chat_id}' not found",
            details={"chat_id": chat_id}
        )


class MessageNotFoundError(ChatError):
    """Raised when a message is not found."""
    
    status_code = HTTPStatus.NOT_FOUND
    default_message = "Message not found"
    
    def __init__(self, message_id: str):
        super().__init__(
            message=f"Message '{message_id}' not found",
            details={"message_id": message_id}
        )


class InvalidBranchError(ChatError):
    """Raised when attempting to branch from an invalid point."""
    
    default_message = "Invalid branch operation"


# =============================================================================
# Agent Errors
# =============================================================================

class AgentError(RAGentError):
    """Base exception for agent-related errors."""
    
    default_message = "Agent error"


class ToolNotFoundError(AgentError):
    """Raised when a requested tool is not registered."""
    
    default_message = "Tool not found"
    
    def __init__(self, tool_name: str, available_tools: list[str]):
        super().__init__(
            message=f"Tool '{tool_name}' is not registered",
            details={
                "requested_tool": tool_name,
                "available_tools": available_tools
            }
        )


class ToolExecutionError(AgentError):
    """Raised when tool execution fails."""
    
    default_message = "Tool execution failed"
    
    def __init__(self, tool_name: str, reason: str):
        super().__init__(
            message=f"Tool '{tool_name}' execution failed: {reason}",
            details={"tool_name": tool_name, "reason": reason}
        )


class MaxIterationsExceededError(AgentError):
    """Raised when agent exceeds maximum tool iterations."""
    
    default_message = "Maximum iterations exceeded"
    
    def __init__(self, max_iterations: int):
        super().__init__(
            message=f"Agent exceeded maximum iterations ({max_iterations})",
            details={"max_iterations": max_iterations}
        )


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(RAGentError):
    """Base exception for validation errors."""
    
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    default_message = "Validation error"


# =============================================================================
# Database Errors
# =============================================================================

class DatabaseError(RAGentError):
    """Base exception for database errors."""
    
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    default_message = "Database error"


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""
    
    default_message = "Database connection failed"