"""
Pydantic schemas for chat-related API endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from app.core.constants import ChatConstants
from app.models.domain.message import MessageRole, MessageType


# =============================================================================
# Message Schemas
# =============================================================================

class MessageBase(BaseModel):
    """Base schema for message data."""
    
    content: str
    role: MessageRole = MessageRole.USER


class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    
    content: str
    attachments: Optional[List[Dict[str, Any]]] = None
    parent_id: Optional[uuid.UUID] = None  # For branching
    branch: str = ChatConstants.DEFAULT_BRANCH_NAME


class MessageResponse(BaseModel):
    """Response schema for a message."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    chat_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    branch: str
    role: str
    message_type: str
    content: str
    token_count: Optional[int] = None
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    attachments: Optional[Dict[str, Any]] = None
    sources: Optional[Dict[str, Any]] = None
    message_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


# =============================================================================
# Chat Schemas
# =============================================================================

class ChatCreate(BaseModel):
    """Schema for creating a new chat."""
    
    title: Optional[str] = None
    initial_message: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ChatUpdate(BaseModel):
    """Schema for updating chat properties."""
    
    title: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response schema for a chat."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    title: Optional[str] = None
    active_branch: str
    branches: Dict[str, Any] = Field(default_factory=dict)
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ChatDetailResponse(ChatResponse):
    """Detailed chat response including messages."""
    
    messages: List[MessageResponse] = Field(default_factory=list)


class ChatListResponse(BaseModel):
    """Response schema for listing chats."""
    
    chats: List[ChatResponse]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False


# =============================================================================
# Branch Schemas
# =============================================================================

class BranchCreate(BaseModel):
    """Schema for creating a new branch."""
    
    branch_name: str = Field(min_length=1, max_length=100)
    from_message_id: Optional[uuid.UUID] = None


class BranchSwitch(BaseModel):
    """Schema for switching branches."""
    
    branch_name: str


class BranchInfo(BaseModel):
    """Information about a branch."""
    
    name: str
    created_at: datetime
    from_message_id: Optional[uuid.UUID] = None
    message_count: int = 0


# =============================================================================
# Streaming Schemas
# =============================================================================

class StreamEvent(BaseModel):
    """Schema for SSE stream events."""
    
    event: str  # message, tool_start, tool_end, error, done
    data: Dict[str, Any]


class ChatStreamChunk(BaseModel):
    """Schema for streaming chat response chunks."""
    
    content: str
    is_complete: bool = False
    sources: Optional[List[Dict[str, Any]]] = None


class ToolCallEvent(BaseModel):
    """Schema for tool call events in stream."""
    
    tool_name: str
    tool_params: Dict[str, Any]
    status: str  # started, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# History Schemas
# =============================================================================

class ConversationHistory(BaseModel):
    """Schema for formatted conversation history."""
    
    messages: List[Dict[str, str]]  # List of {role, content}
    total_tokens: int
    truncated: bool = False
    summary_used: bool = False
