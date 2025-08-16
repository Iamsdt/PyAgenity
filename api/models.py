from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from pyagenity.graph.state.agent_state import AgentState
from pyagenity.graph.utils import Message


# Base API Response Models
class APIResponse(BaseModel):
    """Base response model for all API endpoints."""

    success: bool = True
    message: str | None = None


class ErrorResponse(BaseModel):
    """Error response model."""

    success: bool = False
    error: str
    detail: str | None = None


# Thread Models
class ThreadCreate(BaseModel):
    """Model for creating a new thread."""

    metadata: dict[str, Any] = Field(default_factory=dict)


class ThreadUpdate(BaseModel):
    """Model for updating a thread."""

    metadata: dict[str, Any] | None = None


class ThreadResponse(BaseModel):
    """Response model for thread data."""

    thread_id: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None = None


class ThreadListResponse(BaseModel):
    """Response model for list of threads."""

    threads: list[ThreadResponse]
    total: int
    offset: int
    limit: int


# Message Models
class MessageResponse(BaseModel):
    """Response model for message data."""

    message_id: str
    thread_id: str
    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @classmethod
    def from_message(cls, message: Message, thread_id: str) -> "MessageResponse":
        """Convert a Message object to MessageResponse."""
        metadata = getattr(message, "metadata", {}) or {}
        return cls(
            message_id=str(id(message)),  # Simple ID generation
            thread_id=thread_id,
            role=message.role,
            content=message.content,
            tool_calls=getattr(message, "tools_calls", None),
            tool_call_id=getattr(message, "tool_call_id", None),
            metadata=metadata,
            created_at=datetime.now(),
        )


class MessageListResponse(BaseModel):
    """Response model for list of messages."""

    messages: list[MessageResponse]
    total: int
    offset: int
    limit: int


# State Models
class StateResponse(BaseModel):
    """Response model for agent state data."""

    thread_id: str
    state: dict[str, Any]
    execution_meta: dict[str, Any]
    context_summary: str | None = None
    current_node: str
    step: int
    updated_at: datetime

    @classmethod
    def from_agent_state(cls, state: AgentState, thread_id: str) -> "StateResponse":
        """Convert an AgentState object to StateResponse."""
        return cls(
            thread_id=thread_id,
            state=state.to_dict(include_internal=False),
            execution_meta=state.execution_meta.to_dict(),
            context_summary=state.context_summary,
            current_node=state.execution_meta.current_node,
            step=state.execution_meta.step,
            updated_at=datetime.now(),
        )


class StateUpdate(BaseModel):
    """Model for updating agent state."""

    context_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# Execution Models
class ExecutionRequest(BaseModel):
    """Model for executing agent workflows."""

    input_data: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False


class ExecutionResponse(BaseModel):
    """Response model for agent execution."""

    thread_id: str
    result: dict[str, Any]
    execution_id: str | None = None
    status: str
    created_at: datetime


# Streaming Models
class StreamChunkResponse(BaseModel):
    """Response model for streaming chunks."""

    chunk_id: str
    thread_id: str
    content: str
    is_final: bool
    node_name: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


# Health Check Models
class HealthCheckResponse(BaseModel):
    """Response model for health check."""

    status: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
