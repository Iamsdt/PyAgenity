from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import User, get_current_user_optional
from ..models import (
    APIResponse,
    ThreadCreate,
    ThreadListResponse,
    ThreadResponse,
    ThreadUpdate,
)
from ..shared import get_checkpointer

router = APIRouter()


def generate_thread_id() -> str:
    """Generate a unique thread ID."""
    return str(uuid4())


@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(
    search: str | None = Query(None, description="Search term for threads"),
    offset: int = Query(0, ge=0, description="Number of threads to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of threads to return"),
    user: User | None = Depends(get_current_user_optional),
) -> ThreadListResponse:
    """List all threads with pagination and search."""
    checkpointer = get_checkpointer()

    try:
        # Get threads from checkpointer
        threads = checkpointer.list_threads(search=search, offset=offset, limit=limit)

        # Convert to response format
        thread_responses = []
        for thread in threads:
            thread_responses.append(
                ThreadResponse(
                    thread_id=thread.get("thread_id", "unknown"),
                    metadata=thread.get("metadata", {}),
                    created_at=thread.get("created_at", datetime.now()),
                    updated_at=thread.get("updated_at"),
                )
            )

        return ThreadListResponse(
            threads=thread_responses,
            total=len(threads),  # In real implementation, would get actual total
            offset=offset,
            limit=limit,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list threads: {str(e)}") from e


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    user: User | None = Depends(get_current_user_optional),
) -> ThreadResponse:
    """Get a specific thread by ID."""
    checkpointer = get_checkpointer()

    try:
        config = {"thread_id": thread_id}
        thread = checkpointer.get_thread(config)

        if thread is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        return ThreadResponse(
            thread_id=thread_id,
            metadata=thread.get("metadata", {}),
            created_at=thread.get("created_at", datetime.now()),
            updated_at=thread.get("updated_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get thread: {str(e)}") from e


@router.post("/threads", response_model=ThreadResponse, status_code=201)
async def create_thread(
    thread_data: ThreadCreate,
    user: User | None = Depends(get_current_user_optional),
) -> ThreadResponse:
    """Create a new thread."""
    checkpointer = get_checkpointer()

    try:
        thread_id = generate_thread_id()
        config = {"thread_id": thread_id}

        thread_info = {
            "thread_id": thread_id,
            "metadata": thread_data.metadata,
            "created_at": datetime.now(),
            "created_by": user.username if user else "anonymous",
        }

        checkpointer.put_thread(config, thread_info)

        return ThreadResponse(
            thread_id=thread_id,
            metadata=thread_data.metadata,
            created_at=thread_info["created_at"],
            updated_at=None,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create thread: {str(e)}") from e


@router.patch("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: str,
    thread_update: ThreadUpdate,
    user: User | None = Depends(get_current_user_optional),
) -> ThreadResponse:
    """Update a thread's metadata."""
    checkpointer = get_checkpointer()

    try:
        config = {"thread_id": thread_id}

        # Get existing thread
        existing_thread = checkpointer.get_thread(config)
        if existing_thread is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Update metadata if provided
        if thread_update.metadata is not None:
            existing_thread["metadata"].update(thread_update.metadata)

        existing_thread["updated_at"] = datetime.now()
        existing_thread["updated_by"] = user.username if user else "anonymous"

        # Save updated thread
        checkpointer.put_thread(config, existing_thread)

        return ThreadResponse(
            thread_id=thread_id,
            metadata=existing_thread["metadata"],
            created_at=existing_thread["created_at"],
            updated_at=existing_thread["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update thread: {str(e)}") from e


@router.delete("/threads/{thread_id}", response_model=APIResponse)
async def delete_thread(
    thread_id: str,
    user: User | None = Depends(get_current_user_optional),
) -> APIResponse:
    """Delete a thread and all its associated data."""
    checkpointer = get_checkpointer()

    try:
        config = {"thread_id": thread_id}

        # Check if thread exists
        existing_thread = checkpointer.get_thread(config)
        if existing_thread is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Cleanup all thread data
        checkpointer.cleanup(config)

        return APIResponse(
            success=True,
            message=f"Thread {thread_id} deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete thread: {str(e)}") from e
