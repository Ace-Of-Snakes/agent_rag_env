"""
Message domain model with linked-list structure for branching.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ChatConstants
from app.models.domain.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.domain.chat import Chat


class MessageRole(str, Enum):
    """Message role in conversation."""
    
    USER = ChatConstants.ROLE_USER
    ASSISTANT = ChatConstants.ROLE_ASSISTANT
    SYSTEM = ChatConstants.ROLE_SYSTEM
    TOOL = ChatConstants.ROLE_TOOL


class MessageType(str, Enum):
    """Type of message content."""
    
    TEXT = ChatConstants.TYPE_TEXT
    FILE = ChatConstants.TYPE_FILE
    TOOL_CALL = ChatConstants.TYPE_TOOL_CALL
    TOOL_RESULT = ChatConstants.TYPE_TOOL_RESULT


class Message(Base, UUIDMixin, TimestampMixin):
    """
    Represents a message in a chat conversation.
    
    Uses linked-list structure for branching support:
    - parent_id links to the previous message in the conversation
    - branch identifies which conversation branch this message belongs to
    - Multiple messages can have the same parent (creating branches)
    """
    
    __tablename__ = "messages"
    
    # Foreign key to parent chat
    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Linked-list pointer to parent message (None for first message)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Branch this message belongs to
    branch: Mapped[str] = mapped_column(
        String(100),
        default=ChatConstants.DEFAULT_BRANCH_NAME,
        nullable=False,
        index=True
    )
    
    # Message role (user, assistant, system, tool)
    role: Mapped[MessageRole] = mapped_column(
        String(20),
        nullable=False
    )
    
    # Message type (text, file, tool_call, tool_result)
    message_type: Mapped[MessageType] = mapped_column(
        String(20),
        default=MessageType.TEXT,
        nullable=False
    )
    
    # Message content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Token count for context management
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # For tool calls: tool name and parameters
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tool_params: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # For tool results: link to the tool call message
    tool_call_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # File attachments metadata
    attachments: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Sources used for this response (RAG citations)
    sources: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Additional metadata
    message_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    chat: Mapped["Chat"] = relationship(
        "Chat",
        back_populates="messages"
    )
    
    parent: Mapped[Optional["Message"]] = relationship(
        "Message",
        remote_side="Message.id",
        foreign_keys=[parent_id],
        backref="children"
    )
    
    def __repr__(self) -> str:
        return (
            f"<Message(id={self.id}, role={self.role}, "
            f"branch={self.branch})>"
        )
    
    def soft_delete(self) -> None:
        """Soft delete the message."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def to_llm_format(self) -> dict:
        """
        Convert message to format expected by LLM.
        
        Returns:
            Dictionary with role and content
        """
        return {
            "role": self.role.value if isinstance(self.role, MessageRole) else self.role,
            "content": self.content
        }
    
    @classmethod
    def create_user_message(
        cls,
        chat_id: uuid.UUID,
        content: str,
        parent_id: Optional[uuid.UUID] = None,
        branch: str = ChatConstants.DEFAULT_BRANCH_NAME,
        attachments: Optional[dict] = None
    ) -> "Message":
        """Factory method to create a user message."""
        return cls(
            chat_id=chat_id,
            parent_id=parent_id,
            branch=branch,
            role=MessageRole.USER,
            message_type=MessageType.TEXT,
            content=content,
            attachments=attachments
        )
    
    @classmethod
    def create_assistant_message(
        cls,
        chat_id: uuid.UUID,
        content: str,
        parent_id: uuid.UUID,
        branch: str = ChatConstants.DEFAULT_BRANCH_NAME,
        sources: Optional[dict] = None
    ) -> "Message":
        """Factory method to create an assistant message."""
        return cls(
            chat_id=chat_id,
            parent_id=parent_id,
            branch=branch,
            role=MessageRole.ASSISTANT,
            message_type=MessageType.TEXT,
            content=content,
            sources=sources
        )
    
    @classmethod
    def create_tool_call(
        cls,
        chat_id: uuid.UUID,
        tool_name: str,
        tool_params: dict,
        parent_id: uuid.UUID,
        branch: str = ChatConstants.DEFAULT_BRANCH_NAME
    ) -> "Message":
        """Factory method to create a tool call message."""
        return cls(
            chat_id=chat_id,
            parent_id=parent_id,
            branch=branch,
            role=MessageRole.ASSISTANT,
            message_type=MessageType.TOOL_CALL,
            content=f"Calling tool: {tool_name}",
            tool_name=tool_name,
            tool_params=tool_params
        )
    
    @classmethod
    def create_tool_result(
        cls,
        chat_id: uuid.UUID,
        content: str,
        tool_call_id: uuid.UUID,
        parent_id: uuid.UUID,
        branch: str = ChatConstants.DEFAULT_BRANCH_NAME
    ) -> "Message":
        """Factory method to create a tool result message."""
        return cls(
            chat_id=chat_id,
            parent_id=parent_id,
            branch=branch,
            role=MessageRole.TOOL,
            message_type=MessageType.TOOL_RESULT,
            content=content,
            tool_call_id=tool_call_id
        )
