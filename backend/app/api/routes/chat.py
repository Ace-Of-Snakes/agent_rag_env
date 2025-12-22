"""
Chat API routes with SSE streaming support.
"""

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import agent_orchestrator, StreamEvent
from app.api.dependencies import CommonDeps, get_db
from app.core.constants import APIConstants
from app.core.exceptions import ChatNotFoundError
from app.core.logging import get_logger
from app.models.domain import MessageRole
from app.models.schemas import (
    BranchCreate,
    BranchSwitch,
    ChatCreate,
    ChatDetailResponse,
    ChatListResponse,
    ChatResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.chat import chat_service

logger = get_logger(__name__)

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", response_model=ChatResponse, status_code=201)
async def create_chat(
    data: ChatCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat conversation."""
    chat = await chat_service.create_chat(
        title=data.title,
        initial_message=data.initial_message,
        session=db
    )
    return ChatResponse.model_validate(chat)


@router.get("", response_model=ChatListResponse)
async def list_chats(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all chats with pagination."""
    chats, total = await chat_service.list_chats(
        page=page,
        page_size=page_size,
        session=db
    )
    
    return ChatListResponse(
        chats=[ChatResponse.model_validate(c) for c in chats],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def get_chat(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a chat with its messages."""
    chat = await chat_service.get_chat(chat_id, session=db)
    
    # Get full message objects for the active branch
    messages = await chat_service.get_messages(
        chat_id=chat_id,
        session=db
    )
    
    return ChatDetailResponse(
        **ChatResponse.model_validate(chat).model_dump(),
        messages=[MessageResponse.model_validate(msg) for msg in messages]
    )


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat (soft delete)."""
    await chat_service.delete_chat(chat_id, session=db)


@router.post("/{chat_id}/messages", response_model=MessageResponse)
async def send_message(
    chat_id: uuid.UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message and get a response (non-streaming).
    
    For streaming responses, use the /stream endpoint.
    """
    # Add user message
    user_message = await chat_service.add_message(
        chat_id=chat_id,
        content=data.content,
        role=MessageRole.USER,
        parent_id=data.parent_id,
        session=db
    )
    
    # Get conversation history
    history = await chat_service.get_conversation_history(
        chat_id=chat_id,
        message_id=user_message.id,
        session=db
    )
    
    # Process with agent
    response = await agent_orchestrator.process_message(
        user_message=data.content,
        conversation_history=history[:-1],  # Exclude the message we just added
        attached_files=data.attachments
    )
    
    # Add assistant response
    assistant_message = await chat_service.add_message(
        chat_id=chat_id,
        content=response.response,
        role=MessageRole.ASSISTANT,
        parent_id=user_message.id,
        sources={"sources": response.sources} if response.sources else None,
        session=db
    )
    
    return MessageResponse.model_validate(assistant_message)


@router.post("/{chat_id}/messages/stream")
async def send_message_stream(
    chat_id: uuid.UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message and stream the response via SSE.
    
    Events:
    - message: Token chunks from the LLM
    - tool_start: Tool execution started
    - tool_end: Tool execution completed
    - done: Response complete
    - error: An error occurred
    """
    # Add user message
    user_message = await chat_service.add_message(
        chat_id=chat_id,
        content=data.content,
        role=MessageRole.USER,
        parent_id=data.parent_id,
        session=db
    )
    
    # Get conversation history
    history = await chat_service.get_conversation_history(
        chat_id=chat_id,
        message_id=user_message.id,
        session=db
    )
    
    async def event_stream():
        """Generate SSE events."""
        full_response = ""
        sources = []
        
        try:
            async for event in agent_orchestrator.process_message_stream(
                user_message=data.content,
                conversation_history=history[:-1],
                attached_files=data.attachments
            ):
                # Format as SSE
                event_data = json.dumps(event.data)
                yield f"event: {event.event}\ndata: {event_data}\n\n"
                
                # Collect response for saving
                if event.event == APIConstants.SSE_EVENT_MESSAGE:
                    full_response += event.data.get("token", "")
                elif event.event == APIConstants.SSE_EVENT_DONE:
                    full_response = event.data.get("response", full_response)
                    sources = event.data.get("sources", [])
            
            # Save assistant message after streaming completes
            await chat_service.add_message(
                chat_id=chat_id,
                content=full_response,
                role=MessageRole.ASSISTANT,
                parent_id=user_message.id,
                sources={"sources": sources} if sources else None
                # Don't pass session - let it create its own
            )
                
        except Exception as e:
            logger.error("Stream error", error=str(e))
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post("/{chat_id}/branches", response_model=ChatResponse)
async def create_branch(
    chat_id: uuid.UUID,
    data: BranchCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation branch."""
    chat = await chat_service.create_branch(
        chat_id=chat_id,
        branch_name=data.branch_name,
        from_message_id=data.from_message_id,
        session=db
    )
    return ChatResponse.model_validate(chat)


@router.post("/{chat_id}/branches/switch", response_model=ChatResponse)
async def switch_branch(
    chat_id: uuid.UUID,
    data: BranchSwitch,
    db: AsyncSession = Depends(get_db)
):
    """Switch to a different branch."""
    chat = await chat_service.switch_branch(
        chat_id=chat_id,
        branch_name=data.branch_name,
        session=db
    )
    return ChatResponse.model_validate(chat)


@router.get("/{chat_id}/history")
async def get_history(
    chat_id: uuid.UUID,
    branch: Optional[str] = None,
    message_id: Optional[uuid.UUID] = None,
    max_messages: Optional[int] = Query(None, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history for a chat."""
    history = await chat_service.get_conversation_history(
        chat_id=chat_id,
        branch=branch,
        message_id=message_id,
        max_messages=max_messages,
        session=db
    )
    return {"messages": history, "count": len(history)}
