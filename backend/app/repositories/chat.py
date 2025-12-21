"""
Chat repository for chat-related database operations.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Chat, Message, MessageRole
from app.repositories.base import BaseRepository


class ChatRepository(BaseRepository[Chat]):
    """Repository for Chat entities."""
    
    model = Chat
    
    async def get_by_id(
        self,
        id: uuid.UUID,
        include_deleted: bool = False
    ) -> Optional[Chat]:
        """
        Get chat by ID.
        
        Args:
            id: Chat UUID
            include_deleted: Whether to include soft-deleted chats
            
        Returns:
            Chat or None
        """
        query = select(Chat).where(Chat.id == id)
        
        if not include_deleted:
            query = query.where(Chat.is_deleted == False)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def list_chats(
        self,
        skip: int = 0,
        limit: int = 20,
        include_deleted: bool = False
    ) -> tuple[List[Chat], int]:
        """
        List chats with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            include_deleted: Include soft-deleted chats
            
        Returns:
            Tuple of (chats, total_count)
        """
        # Build base query
        query = select(Chat)
        count_query = select(func.count()).select_from(Chat)
        
        if not include_deleted:
            query = query.where(Chat.is_deleted == False)
            count_query = count_query.where(Chat.is_deleted == False)
        
        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0
        
        # Get paginated results, ordered by most recent activity
        query = query.order_by(Chat.updated_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        chats = list(result.scalars().all())
        
        return chats, total
    
    async def update_title(
        self,
        chat_id: uuid.UUID,
        title: str
    ) -> Optional[Chat]:
        """
        Update chat title.
        
        Args:
            chat_id: Chat UUID
            title: New title
            
        Returns:
            Updated chat or None
        """
        chat = await self.get_by_id(chat_id)
        if not chat:
            return None
        
        chat.title = title
        await self.session.flush()
        await self.session.refresh(chat)
        return chat
    
    async def update_summary(
        self,
        chat_id: uuid.UUID,
        summary: str
    ) -> Optional[Chat]:
        """
        Update chat summary (for context management).
        
        Args:
            chat_id: Chat UUID
            summary: Conversation summary
            
        Returns:
            Updated chat or None
        """
        chat = await self.get_by_id(chat_id)
        if not chat:
            return None
        
        chat.summary = summary
        await self.session.flush()
        await self.session.refresh(chat)
        return chat
    
    async def soft_delete(self, chat_id: uuid.UUID) -> bool:
        """
        Soft delete a chat.
        
        Args:
            chat_id: Chat UUID
            
        Returns:
            True if deleted, False if not found
        """
        chat = await self.get_by_id(chat_id)
        if not chat:
            return False
        
        chat.soft_delete()
        await self.session.flush()
        return True
    
    async def get_recent_chats(self, limit: int = 10) -> List[Chat]:
        """
        Get most recently active chats.
        
        Args:
            limit: Maximum chats to return
            
        Returns:
            List of recent chats
        """
        result = await self.session.execute(
            select(Chat).where(
                Chat.is_deleted == False
            ).order_by(
                Chat.last_message_at.desc().nullsfirst()
            ).limit(limit)
        )
        return list(result.scalars().all())


class MessageRepository(BaseRepository[Message]):
    """Repository for Message entities."""
    
    model = Message
    
    async def get_by_id(
        self,
        id: uuid.UUID,
        include_deleted: bool = False
    ) -> Optional[Message]:
        """
        Get message by ID.
        
        Args:
            id: Message UUID
            include_deleted: Whether to include soft-deleted messages
            
        Returns:
            Message or None
        """
        query = select(Message).where(Message.id == id)
        
        if not include_deleted:
            query = query.where(Message.is_deleted == False)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_chat_messages(
        self,
        chat_id: uuid.UUID,
        branch: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[Message]:
        """
        Get all messages for a chat.
        
        Args:
            chat_id: Chat UUID
            branch: Optional branch filter
            include_deleted: Include soft-deleted messages
            
        Returns:
            List of messages ordered by creation time
        """
        query = select(Message).where(Message.chat_id == chat_id)
        
        if branch:
            query = query.where(Message.branch == branch)
        
        if not include_deleted:
            query = query.where(Message.is_deleted == False)
        
        query = query.order_by(Message.created_at)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_branch_messages(
        self,
        chat_id: uuid.UUID,
        branch: str,
        from_message_id: Optional[uuid.UUID] = None
    ) -> List[Message]:
        """
        Get messages for a specific branch.
        
        If from_message_id is provided, returns only messages from that point.
        
        Args:
            chat_id: Chat UUID
            branch: Branch name
            from_message_id: Optional starting message ID
            
        Returns:
            List of messages
        """
        query = select(Message).where(
            Message.chat_id == chat_id,
            Message.branch == branch,
            Message.is_deleted == False
        )
        
        if from_message_id:
            # Get the timestamp of the starting message
            start_msg = await self.get_by_id(from_message_id)
            if start_msg:
                query = query.where(Message.created_at >= start_msg.created_at)
        
        query = query.order_by(Message.created_at)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_message_chain(
        self,
        message_id: uuid.UUID
    ) -> List[Message]:
        """
        Get the chain of messages leading to a specific message.
        
        Walks backwards through parent_id links.
        
        Args:
            message_id: Target message UUID
            
        Returns:
            List of messages from root to target
        """
        messages = []
        current_id = message_id
        
        while current_id:
            message = await self.get_by_id(current_id)
            if not message:
                break
            
            messages.append(message)
            current_id = message.parent_id
        
        # Reverse to get chronological order
        return list(reversed(messages))
    
    async def get_last_message(
        self,
        chat_id: uuid.UUID,
        branch: Optional[str] = None
    ) -> Optional[Message]:
        """
        Get the last message in a chat/branch.
        
        Args:
            chat_id: Chat UUID
            branch: Optional branch filter
            
        Returns:
            Last message or None
        """
        query = select(Message).where(
            Message.chat_id == chat_id,
            Message.is_deleted == False
        )
        
        if branch:
            query = query.where(Message.branch == branch)
        
        query = query.order_by(Message.created_at.desc()).limit(1)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def count_by_chat(
        self,
        chat_id: uuid.UUID,
        branch: Optional[str] = None
    ) -> int:
        """
        Count messages in a chat/branch.
        
        Args:
            chat_id: Chat UUID
            branch: Optional branch filter
            
        Returns:
            Message count
        """
        query = select(func.count()).select_from(Message).where(
            Message.chat_id == chat_id,
            Message.is_deleted == False
        )
        
        if branch:
            query = query.where(Message.branch == branch)
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def soft_delete(self, message_id: uuid.UUID) -> bool:
        """
        Soft delete a message.
        
        Args:
            message_id: Message UUID
            
        Returns:
            True if deleted, False if not found
        """
        message = await self.get_by_id(message_id)
        if not message:
            return False
        
        message.soft_delete()
        await self.session.flush()
        return True
    
    async def get_tool_calls(
        self,
        chat_id: uuid.UUID,
        limit: int = 10
    ) -> List[Message]:
        """
        Get recent tool call messages.
        
        Args:
            chat_id: Chat UUID
            limit: Maximum messages to return
            
        Returns:
            List of tool call messages
        """
        from app.models.domain import MessageType
        
        result = await self.session.execute(
            select(Message).where(
                Message.chat_id == chat_id,
                Message.message_type == MessageType.TOOL_CALL,
                Message.is_deleted == False
            ).order_by(Message.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())