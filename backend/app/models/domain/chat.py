"""
Chat domain model with conversation branching support.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ChatConstants
from app.models.domain.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.domain.message import Message


class Chat(Base, UUIDMixin, TimestampMixin):
    """
    Represents a chat conversation.
    
    Chats contain messages and support branching for conversation alternatives.
    """
    
    __tablename__ = "chats"
    
    # Chat title (auto-generated or user-provided)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Summary of conversation (for context management)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Current active branch
    active_branch: Mapped[str] = mapped_column(
        String(100),
        default=ChatConstants.DEFAULT_BRANCH_NAME,
        nullable=False
    )
    
    # Available branches in this chat
    branches: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=lambda: {ChatConstants.DEFAULT_BRANCH_NAME: {"created_at": datetime.utcnow().isoformat()}},
        nullable=False
    )
    
    # Message count for quick reference
    message_count: Mapped[int] = mapped_column(default=0, nullable=False)
    
    # Last activity timestamp
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Chat settings/preferences
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Chat(id={self.id}, title={self.title})>"
    
    def create_branch(self, branch_name: str, from_message_id: Optional[uuid.UUID] = None) -> None:
        """
        Create a new conversation branch.
        
        Args:
            branch_name: Name for the new branch
            from_message_id: Message ID to branch from (None for root)
        """
        if self.branches is None:
            self.branches = {}
        
        self.branches[branch_name] = {
            "created_at": datetime.utcnow().isoformat(),
            "from_message_id": str(from_message_id) if from_message_id else None
        }
    
    def switch_branch(self, branch_name: str) -> None:
        """
        Switch to a different branch.
        
        Args:
            branch_name: Name of branch to switch to
            
        Raises:
            ValueError: If branch doesn't exist
        """
        if self.branches is None or branch_name not in self.branches:
            raise ValueError(f"Branch '{branch_name}' does not exist")
        self.active_branch = branch_name
    
    def get_branch_info(self, branch_name: Optional[str] = None) -> dict:
        """Get information about a branch."""
        name = branch_name or self.active_branch
        if self.branches is None or name not in self.branches:
            return {}
        return self.branches[name]
    
    def update_message_count(self, delta: int = 1) -> None:
        """Update the message count."""
        self.message_count += delta
        self.last_message_at = datetime.utcnow()
    
    def soft_delete(self) -> None:
        """Soft delete the chat."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
