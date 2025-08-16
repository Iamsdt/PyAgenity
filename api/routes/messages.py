from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import User, get_current_user_optional
from api.models import APIResponse, MessageListResponse, MessageResponse
from api.shared import get_checkpointer

router = APIRouter()


@router.get("/threads/{thread_id}/messages", response_model=MessageListResponse)
async def list_messages(
    thread_id: str,
    search: str | None = Query(None, description="Search term for messages"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    user: User | None = Depends(get_current_user_optional),
) -> MessageListResponse:
    """List all messages in a thread with pagination and search."""
    checkpointer = get_checkpointer()

    try:
        config = {"thread_id": thread_id}

        # Get messages from checkpointer
        messages = checkpointer.list_messages(config, search=search, offset=offset, limit=limit)

        # Convert to response format
        message_responses = []
        for message in messages:
            message_responses.append(MessageResponse.from_message(message, thread_id))

        return MessageListResponse(
            messages=message_responses,
            total=len(messages),  # In real implementation, would get actual total
            offset=offset,
            limit=limit,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list messages: {e!s}") from e


@router.get("/threads/{thread_id}/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    thread_id: str,
    message_id: str,
    user: User | None = Depends(get_current_user_optional),
) -> MessageResponse:
    """Get a specific message by ID."""
    checkpointer = get_checkpointer()

    try:
        config = {"thread_id": thread_id}

        # Get all messages and find the specific one
        messages = checkpointer.list_messages(config)

        # Find message by ID (simple implementation)
        for message in messages:
            if str(id(message)) == message_id:
                return MessageResponse.from_message(message, thread_id)

        raise HTTPException(status_code=404, detail="Message not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get message: {e!s}") from e


@router.delete("/threads/{thread_id}/messages/{message_id}", response_model=APIResponse)
async def delete_message(
    thread_id: str,
    message_id: str,
    user: User | None = Depends(get_current_user_optional),
) -> APIResponse:
    """Delete a specific message."""
    checkpointer = get_checkpointer()

    try:
        config = {"thread_id": thread_id}

        # Get all messages
        messages = checkpointer.list_messages(config)

        # Find and remove message by ID
        updated_messages = []
        found = False
        for message in messages:
            if str(id(message)) == message_id:
                found = True
                continue  # Skip this message (delete it)
            updated_messages.append(message)

        if not found:
            raise HTTPException(status_code=404, detail="Message not found")

        # Save updated messages
        checkpointer.put_messages(config, updated_messages)

        return APIResponse(
            success=True,
            message=f"Message {message_id} deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete message: {e!s}") from e


@router.delete("/threads/{thread_id}/messages", response_model=APIResponse)
async def delete_all_messages(
    thread_id: str,
    user: User | None = Depends(get_current_user_optional),
) -> APIResponse:
    """Delete all messages in a thread."""
    checkpointer = get_checkpointer()

    try:
        config = {"thread_id": thread_id}

        # Delete all messages
        checkpointer.delete_message(config)

        return APIResponse(
            success=True,
            message=f"All messages in thread {thread_id} deleted successfully",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete messages: {e!s}") from e
