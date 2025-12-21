"""
Chat service for conversation management.
"""

import uuid
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import ChatConstants
from app.core.exceptions import ChatNotFoundError, MessageNotFoundError
from app.core.logging import get_logger
from app.db.postgres import get_db_session
from app.db.redis import redis_helper
from app.models.domain import Chat, Message, MessageRole, MessageType
from app.services.llm.text import text_service

logger = get_logger(__name__)


class ChatService:
    """Service for managing chat conversations."""
    
    def __init__(self):
        self._settings = get_settings()
    
    async def create_chat(
        self,
        title: Optional[str] = None,
        initial_message: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ) -> Chat:
        """
        Create a new chat conversation.
        
        Args:
            title: Optional title (auto-generated if not provided)
            initial_message: Optional first user message
            session: Database session
            
        Returns:
            Created Chat object
        """
        async def execute(session: AsyncSession) -> Chat:
            chat = Chat(
                title=title,
                active_branch=ChatConstants.DEFAULT_BRANCH_NAME,
                branches={
                    ChatConstants.DEFAULT_BRANCH_NAME: {
                        "created_at": str(uuid.uuid4())
                    }
                }
            )
            session.add(chat)
            await session.flush()
            
            # Add initial message if provided
            if initial_message:
                message = Message.create_user_message(
                    chat_id=chat.id,
                    content=initial_message,
                    branch=ChatConstants.DEFAULT_BRANCH_NAME
                )
                session.add(message)
                chat.update_message_count()
                
                # Generate title from first message if not provided
                if not title:
                    chat.title = await text_service.generate_title(initial_message)
            
            await session.commit()
            await session.refresh(chat)
            
            logger.info("Chat created", chat_id=str(chat.id))
            return chat
        
        if session:
            return await execute(session)
        else:
            async with get_db_session() as session:
                return await execute(session)
    
    async def get_chat(
        self,
        chat_id: uuid.UUID,
        session: Optional[AsyncSession] = None
    ) -> Chat:
        """
        Get a chat by ID.
        
        Args:
            chat_id: Chat identifier
            session: Database session
            
        Returns:
            Chat object
            
        Raises:
            ChatNotFoundError: If chat doesn't exist
        """
        async def execute(session: AsyncSession) -> Chat:
            result = await session.execute(
                select(Chat).where(
                    Chat.id == chat_id,
                    Chat.is_deleted == False
                )
            )
            chat = result.scalar_one_or_none()
            
            if not chat:
                raise ChatNotFoundError(str(chat_id))
            
            return chat
        
        if session:
            return await execute(session)
        else:
            async with get_db_session() as session:
                return await execute(session)
    
    async def list_chats(
        self,
        page: int = 1,
        page_size: int = 20,
        session: Optional[AsyncSession] = None
    ) -> tuple[List[Chat], int]:
        """
        List chats with pagination.
        
        Returns:
            Tuple of (chats list, total count)
        """
        async def execute(session: AsyncSession) -> tuple[List[Chat], int]:
            # Count total
            count_result = await session.execute(
                select(Chat).where(Chat.is_deleted == False)
            )
            total = len(count_result.scalars().all())
            
            # Get page
            offset = (page - 1) * page_size
            result = await session.execute(
                select(Chat)
                .where(Chat.is_deleted == False)
                .order_by(Chat.updated_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            chats = list(result.scalars().all())
            
            return chats, total
        
        if session:
            return await execute(session)
        else:
            async with get_db_session() as session:
                return await execute(session)
    
    async def add_message(
        self,
        chat_id: uuid.UUID,
        content: str,
        role: MessageRole,
        parent_id: Optional[uuid.UUID] = None,
        message_type: MessageType = MessageType.TEXT,
        sources: Optional[dict] = None,
        session: Optional[AsyncSession] = None
    ) -> Message:
        """
        Add a message to a chat.
        
        Args:
            chat_id: Chat identifier
            content: Message content
            role: Message role (user, assistant, etc.)
            parent_id: Parent message ID for branching
            message_type: Type of message
            sources: RAG sources for citations
            session: Database session
            
        Returns:
            Created Message object
        """
        async def execute(session: AsyncSession) -> Message:
            # Handle parent_id logic
            nonlocal parent_id
            
            # Get the chat
            chat = await self.get_chat(chat_id, session)
            
            # If no parent specified, find the last message in the branch
            if parent_id is None:
                result = await session.execute(
                    select(Message)
                    .where(
                        Message.chat_id == chat_id,
                        Message.branch == chat.active_branch,
                        Message.is_deleted == False
                    )
                    .order_by(Message.created_at.desc())
                    .limit(1)
                )
                last_message = result.scalar_one_or_none()
                parent_id = last_message.id if last_message else None
            
            # Create message
            message = Message(
                chat_id=chat_id,
                parent_id=parent_id,
                branch=chat.active_branch,
                role=role,
                message_type=message_type,
                content=content,
                sources=sources
            )
            session.add(message)
            
            # Update chat
            chat.update_message_count()
            
            await session.commit()
            await session.refresh(message)
            
            # Invalidate cache
            await redis_helper.invalidate_chat_history(str(chat_id))
            
            return message
        
        if session:
            return await execute(session)
        else:
            async with get_db_session() as session:
                return await execute(session)
    
    async def get_conversation_history(
        self,
        chat_id: uuid.UUID,
        branch: Optional[str] = None,
        message_id: Optional[uuid.UUID] = None,
        max_messages: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> List[Dict[str, str]]:
        """
        Get conversation history for LLM context.
        
        Args:
            chat_id: Chat identifier
            branch: Branch name (defaults to active branch)
            message_id: Get history up to this message
            max_messages: Maximum messages to return
            session: Database session
            
        Returns:
            List of message dicts with 'role' and 'content'
        """
        # Check cache first
        cache_key = f"{chat_id}:{branch or 'active'}"
        cached = await redis_helper.get_chat_history(cache_key)
        if cached and not message_id:
            return cached[:max_messages] if max_messages else cached
        
        async def execute(session: AsyncSession) -> List[Dict[str, str]]:
            chat = await self.get_chat(chat_id, session)
            branch_name = branch or chat.active_branch
            
            if message_id:
                # Walk backwards from message_id
                messages = await self._get_history_to_message(
                    session, chat_id, message_id
                )
            else:
                # Get all messages in branch
                result = await session.execute(
                    select(Message)
                    .where(
                        Message.chat_id == chat_id,
                        Message.branch == branch_name,
                        Message.is_deleted == False
                    )
                    .order_by(Message.created_at)
                )
                messages = list(result.scalars().all())
            
            # Convert to LLM format
            history = [msg.to_llm_format() for msg in messages]
            
            # Apply limit
            if max_messages:
                history = history[-max_messages:]
            
            # Cache the full history
            if not message_id:
                await redis_helper.set_chat_history(cache_key, history)
            
            return history
        
        if session:
            return await execute(session)
        else:
            async with get_db_session() as session:
                return await execute(session)
    
    async def _get_history_to_message(
        self,
        session: AsyncSession,
        chat_id: uuid.UUID,
        message_id: uuid.UUID
    ) -> List[Message]:
        """Walk the linked list backwards to build history."""
        messages = []
        current_id = message_id
        
        while current_id:
            result = await session.execute(
                select(Message).where(Message.id == current_id)
            )
            message = result.scalar_one_or_none()
            
            if not message:
                break
            
            messages.append(message)
            current_id = message.parent_id
        
        # Reverse to get chronological order
        return list(reversed(messages))
    
    async def create_branch(
        self,
        chat_id: uuid.UUID,
        branch_name: str,
        from_message_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Chat:
        """
        Create a new conversation branch.
        
        Args:
            chat_id: Chat identifier
            branch_name: Name for the new branch
            from_message_id: Message to branch from
            session: Database session
            
        Returns:
            Updated Chat object
        """
        async def execute(session: AsyncSession) -> Chat:
            chat = await self.get_chat(chat_id, session)
            chat.create_branch(branch_name, from_message_id)
            chat.switch_branch(branch_name)
            
            await session.commit()
            await session.refresh(chat)
            
            # Invalidate cache
            await redis_helper.invalidate_chat_history(str(chat_id))
            
            logger.info(
                "Branch created",
                chat_id=str(chat_id),
                branch=branch_name,
                from_message=str(from_message_id) if from_message_id else None
            )
            
            return chat
        
        if session:
            return await execute(session)
        else:
            async with get_db_session() as session:
                return await execute(session)
    
    async def switch_branch(
        self,
        chat_id: uuid.UUID,
        branch_name: str,
        session: Optional[AsyncSession] = None
    ) -> Chat:
        """Switch to a different branch."""
        async def execute(session: AsyncSession) -> Chat:
            chat = await self.get_chat(chat_id, session)
            chat.switch_branch(branch_name)
            
            await session.commit()
            await session.refresh(chat)
            
            return chat
        
        if session:
            return await execute(session)
        else:
            async with get_db_session() as session:
                return await execute(session)
    
    async def delete_chat(
        self,
        chat_id: uuid.UUID,
        session: Optional[AsyncSession] = None
    ) -> None:
        """Soft delete a chat."""
        async def execute(session: AsyncSession) -> None:
            chat = await self.get_chat(chat_id, session)
            chat.soft_delete()
            
            await session.commit()
            
            # Clean up cache
            await redis_helper.invalidate_chat_history(str(chat_id))
            
            logger.info("Chat deleted", chat_id=str(chat_id))
        
        if session:
            await execute(session)
        else:
            async with get_db_session() as session:
                await execute(session)


# Singleton instance
chat_service = ChatService()
