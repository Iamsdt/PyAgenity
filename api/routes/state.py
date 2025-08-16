from fastapi import APIRouter, Depends, HTTPException

from api.auth import User, get_current_user_optional
from api.models import APIResponse, StateResponse, StateUpdate
from api.shared import get_checkpointer

router = APIRouter()


@router.get("/threads/{thread_id}/state", response_model=StateResponse)
async def get_state(
    thread_id: str,
    user: User | None = Depends(get_current_user_optional),
) -> StateResponse:
    """Get the current state for a thread."""
    checkpointer = get_checkpointer()

    try:
        config = {"thread_id": thread_id}

        # Get state from checkpointer
        state = checkpointer.get_state(config)

        if state is None:
            raise HTTPException(status_code=404, detail="Thread state not found")

        return StateResponse.from_agent_state(state, thread_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get state: {e!s}") from e


@router.patch("/threads/{thread_id}/state", response_model=StateResponse)
async def update_state(
    thread_id: str,
    state_update: StateUpdate,
    user: User | None = Depends(get_current_user_optional),
) -> StateResponse:
    """Update the state for a thread."""
    checkpointer = get_checkpointer()

    try:
        config = {"thread_id": thread_id}

        # Get existing state
        existing_state = checkpointer.get_state(config)
        if existing_state is None:
            raise HTTPException(status_code=404, detail="Thread state not found")

        # Update context summary if provided
        if state_update.context_summary is not None:
            existing_state.context_summary = state_update.context_summary

        # Update any additional metadata
        for key, value in state_update.metadata.items():
            setattr(existing_state, key, value)

        # Save updated state
        checkpointer.put_state(config, existing_state)

        return StateResponse.from_agent_state(existing_state, thread_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update state: {e!s}") from e


@router.delete("/threads/{thread_id}/state", response_model=APIResponse)
async def clear_state(
    thread_id: str,
    user: User | None = Depends(get_current_user_optional),
) -> APIResponse:
    """Clear the state for a thread."""
    checkpointer = get_checkpointer()

    try:
        config = {"thread_id": thread_id}

        # Clear state
        checkpointer.clear_state(config)

        return APIResponse(
            success=True,
            message=f"State for thread {thread_id} cleared successfully",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear state: {e!s}") from e
