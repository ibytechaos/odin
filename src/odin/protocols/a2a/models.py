"""A2A Protocol data models.

Implements the core data structures from the A2A specification.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# ============================================================================
# Core Message Types
# ============================================================================


class MessageRole(str, Enum):
    """Role of message sender."""

    USER = "USER"
    AGENT = "AGENT"


class TextPart(BaseModel):
    """Text content part."""

    type: Literal["text"] = "text"
    text: str
    metadata: dict[str, Any] | None = None


class FilePart(BaseModel):
    """File content part (URI or base64)."""

    type: Literal["file"] = "file"
    uri: str | None = None
    bytes: str | None = None  # base64 encoded
    mimeType: str | None = None
    name: str | None = None
    metadata: dict[str, Any] | None = None


class DataPart(BaseModel):
    """Structured data part."""

    type: Literal["data"] = "data"
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None


# Union type for message parts
MessagePart = TextPart | FilePart | DataPart


class Message(BaseModel):
    """A2A Message object."""

    messageId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    parts: list[MessagePart]
    contextId: str | None = None
    taskId: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Task Management
# ============================================================================


class TaskState(str, Enum):
    """Task lifecycle states."""

    SUBMITTED = "SUBMITTED"
    WORKING = "WORKING"
    INPUT_REQUIRED = "INPUT_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    AUTH_REQUIRED = "AUTH_REQUIRED"


class TaskStatus(BaseModel):
    """Task status object."""

    state: TaskState
    message: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskArtifact(BaseModel):
    """Task output artifact."""

    artifactId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parts: list[MessagePart]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] | None = None


class Task(BaseModel):
    """A2A Task object."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contextId: str
    status: TaskStatus
    artifacts: list[TaskArtifact] = Field(default_factory=list)
    history: list[Message] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Agent Card
# ============================================================================


class SecurityScheme(BaseModel):
    """Authentication scheme definition."""

    type: Literal["apiKey", "oauth2", "http", "openIdConnect", "mutualTLS"]
    scheme: str | None = None  # For http type: "basic", "bearer"
    name: str | None = None  # For apiKey: header/query/cookie name
    in_: str | None = Field(None, alias="in")  # For apiKey: location
    flows: dict[str, Any] | None = None  # For oauth2
    openIdConnectUrl: str | None = None  # For openIdConnect


class AgentSkill(BaseModel):
    """Agent skill/capability description."""

    name: str
    description: str
    examples: list[str] | None = None
    metadata: dict[str, Any] | None = None


class AgentCapabilities(BaseModel):
    """Agent capabilities flags."""

    streaming: bool = False
    pushNotifications: bool = False


class ProviderInfo(BaseModel):
    """Agent provider information."""

    organization: str | None = None
    url: str | None = None
    contact: str | None = None


class AgentCard(BaseModel):
    """Agent Card - declares agent capabilities and metadata.

    This is the self-describing document that agents expose to declare
    their capabilities, authentication requirements, and skills.
    """

    name: str
    description: str
    protocolVersion: str = "1.0"
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    securitySchemes: list[SecurityScheme] = Field(default_factory=list)
    skills: list[AgentSkill] = Field(default_factory=list)
    provider: ProviderInfo | None = None
    supportsAuthenticatedExtendedCard: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Request/Response Models
# ============================================================================


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    message: Message
    contextId: str | None = None


class SendMessageResponse(BaseModel):
    """Response from sending a message."""

    task: Task | None = None
    message: Message | None = None


class GetTaskRequest(BaseModel):
    """Request to get task status."""

    taskId: str
    includeHistory: bool = False


class GetTaskResponse(BaseModel):
    """Response with task details."""

    task: Task


class ListTasksRequest(BaseModel):
    """Request to list tasks."""

    contextId: str | None = None
    status: TaskState | None = None
    limit: int = 100
    offset: int = 0


class ListTasksResponse(BaseModel):
    """Response with task list."""

    tasks: list[Task]
    total: int
    hasMore: bool


# ============================================================================
# Streaming Events
# ============================================================================


class TaskStatusUpdateEvent(BaseModel):
    """Server-Sent Event for task status update."""

    type: Literal["taskStatus"] = "taskStatus"
    taskId: str
    status: TaskStatus


class TaskArtifactUpdateEvent(BaseModel):
    """Server-Sent Event for new task artifact."""

    type: Literal["taskArtifact"] = "taskArtifact"
    taskId: str
    artifact: TaskArtifact


# Union type for events
A2AEvent = TaskStatusUpdateEvent | TaskArtifactUpdateEvent


# ============================================================================
# Error Models
# ============================================================================


class A2AError(BaseModel):
    """Standardized A2A error response."""

    code: str
    message: str
    details: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
