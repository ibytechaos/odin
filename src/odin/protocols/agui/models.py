"""AG-UI Protocol data models.

Implements data structures for the AG-UI protocol.
"""

import uuid
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ============================================================================
# Message Types
# ============================================================================


class MessageRole(str, Enum):
    """Message role."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolCall(BaseModel):
    """Tool call in a message."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["function"] = "function"
    function: dict[str, Any]  # {name: str, arguments: str}


class Message(BaseModel):
    """AG-UI message format."""

    role: MessageRole
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class Tool(BaseModel):
    """Tool definition in AG-UI format."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


class RunAgentInput(BaseModel):
    """Input for running an agent via AG-UI."""

    thread_id: str
    run_id: str
    messages: list[Message]
    tools: list[Tool] | None = None


# ============================================================================
# Event Types
# ============================================================================


class EventType(str, Enum):
    """AG-UI event types."""

    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"
    TEXT_MESSAGE_CHUNK = "TEXT_MESSAGE_CHUNK"
    TOOL_CALL_CHUNK = "TOOL_CALL_CHUNK"
    STATE_UPDATE = "STATE_UPDATE"


class AGUIEvent(BaseModel):
    """Base AG-UI event."""

    event: EventType


class RunStartedEvent(AGUIEvent):
    """Event emitted when a run starts."""

    event: Literal[EventType.RUN_STARTED] = EventType.RUN_STARTED
    thread_id: str
    run_id: str


class RunFinishedEvent(AGUIEvent):
    """Event emitted when a run completes successfully."""

    event: Literal[EventType.RUN_FINISHED] = EventType.RUN_FINISHED
    thread_id: str
    run_id: str


class RunErrorEvent(AGUIEvent):
    """Event emitted when a run encounters an error."""

    event: Literal[EventType.RUN_ERROR] = EventType.RUN_ERROR
    thread_id: str
    run_id: str
    message: str
    error: str | None = None


class TextMessageChunkEvent(AGUIEvent):
    """Event for streaming text content."""

    event: Literal[EventType.TEXT_MESSAGE_CHUNK] = EventType.TEXT_MESSAGE_CHUNK
    message_id: str
    delta: str  # Text chunk
    thread_id: str
    run_id: str


class ToolCallChunkEvent(AGUIEvent):
    """Event for tool call execution."""

    event: Literal[EventType.TOOL_CALL_CHUNK] = EventType.TOOL_CALL_CHUNK
    tool_call_id: str
    tool_call_name: str
    parent_message_id: str
    delta: str  # Arguments chunk (JSON string)
    thread_id: str
    run_id: str


class StateUpdateEvent(AGUIEvent):
    """Event for shared state updates."""

    event: Literal[EventType.STATE_UPDATE] = EventType.STATE_UPDATE
    thread_id: str
    run_id: str
    state: dict[str, Any]


# Union type for all events
AGUIEventUnion = (
    RunStartedEvent
    | RunFinishedEvent
    | RunErrorEvent
    | TextMessageChunkEvent
    | ToolCallChunkEvent
    | StateUpdateEvent
)
