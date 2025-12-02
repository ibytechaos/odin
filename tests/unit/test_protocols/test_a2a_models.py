"""Tests for A2A protocol models."""

import pytest
from datetime import datetime
import uuid

from odin.protocols.a2a.models import (
    MessageRole,
    TextPart,
    FilePart,
    DataPart,
    Message,
    TaskState,
    TaskStatus,
    TaskArtifact,
    Task,
    SecurityScheme,
    AgentSkill,
    AgentCapabilities,
    ProviderInfo,
    AgentCard,
    SendMessageRequest,
    SendMessageResponse,
    GetTaskRequest,
    GetTaskResponse,
    ListTasksRequest,
    ListTasksResponse,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    A2AError,
)


class TestMessageRole:
    """Test MessageRole enum."""

    def test_user_role(self):
        """Test USER role value."""
        assert MessageRole.USER.value == "USER"

    def test_agent_role(self):
        """Test AGENT role value."""
        assert MessageRole.AGENT.value == "AGENT"


class TestMessageParts:
    """Test message part models."""

    def test_text_part(self):
        """Test TextPart model."""
        part = TextPart(text="Hello, world!")
        assert part.type == "text"
        assert part.text == "Hello, world!"
        assert part.metadata is None

    def test_text_part_with_metadata(self):
        """Test TextPart with metadata."""
        part = TextPart(text="Test", metadata={"key": "value"})
        assert part.metadata == {"key": "value"}

    def test_file_part_with_uri(self):
        """Test FilePart with URI."""
        part = FilePart(uri="https://example.com/file.pdf", mimeType="application/pdf")
        assert part.type == "file"
        assert part.uri == "https://example.com/file.pdf"
        assert part.mimeType == "application/pdf"
        assert part.bytes is None

    def test_file_part_with_bytes(self):
        """Test FilePart with base64 bytes."""
        part = FilePart(bytes="SGVsbG8gV29ybGQ=", mimeType="text/plain", name="test.txt")
        assert part.bytes == "SGVsbG8gV29ybGQ="
        assert part.name == "test.txt"

    def test_data_part(self):
        """Test DataPart model."""
        part = DataPart(data={"key": "value", "count": 42})
        assert part.type == "data"
        assert part.data == {"key": "value", "count": 42}


class TestMessage:
    """Test Message model."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(
            role=MessageRole.USER,
            parts=[TextPart(text="Hello")],
        )
        assert msg.role == MessageRole.USER
        assert len(msg.parts) == 1
        assert msg.messageId is not None
        assert msg.timestamp is not None

    def test_message_with_custom_id(self):
        """Test message with custom ID."""
        msg = Message(
            messageId="custom-id",
            role=MessageRole.AGENT,
            parts=[TextPart(text="Response")],
        )
        assert msg.messageId == "custom-id"

    def test_message_with_context(self):
        """Test message with context and task IDs."""
        msg = Message(
            role=MessageRole.USER,
            parts=[DataPart(data={"query": "test"})],
            contextId="ctx-123",
            taskId="task-456",
        )
        assert msg.contextId == "ctx-123"
        assert msg.taskId == "task-456"


class TestTaskState:
    """Test TaskState enum."""

    def test_all_states(self):
        """Test all task state values."""
        assert TaskState.SUBMITTED.value == "SUBMITTED"
        assert TaskState.WORKING.value == "WORKING"
        assert TaskState.INPUT_REQUIRED.value == "INPUT_REQUIRED"
        assert TaskState.COMPLETED.value == "COMPLETED"
        assert TaskState.FAILED.value == "FAILED"
        assert TaskState.CANCELLED.value == "CANCELLED"
        assert TaskState.REJECTED.value == "REJECTED"
        assert TaskState.AUTH_REQUIRED.value == "AUTH_REQUIRED"


class TestTaskStatus:
    """Test TaskStatus model."""

    def test_status_creation(self):
        """Test creating a task status."""
        status = TaskStatus(state=TaskState.WORKING)
        assert status.state == TaskState.WORKING
        assert status.message is None
        assert status.timestamp is not None

    def test_status_with_message(self):
        """Test status with message."""
        status = TaskStatus(state=TaskState.FAILED, message="Something went wrong")
        assert status.message == "Something went wrong"


class TestTaskArtifact:
    """Test TaskArtifact model."""

    def test_artifact_creation(self):
        """Test creating a task artifact."""
        artifact = TaskArtifact(parts=[TextPart(text="Result")])
        assert artifact.artifactId is not None
        assert len(artifact.parts) == 1
        assert artifact.timestamp is not None

    def test_artifact_with_metadata(self):
        """Test artifact with metadata."""
        artifact = TaskArtifact(
            parts=[DataPart(data={"result": "success"})],
            metadata={"format": "json"},
        )
        assert artifact.metadata == {"format": "json"}


class TestTask:
    """Test Task model."""

    def test_task_creation(self):
        """Test creating a task."""
        status = TaskStatus(state=TaskState.SUBMITTED)
        task = Task(contextId="ctx-123", status=status)

        assert task.id is not None
        assert task.contextId == "ctx-123"
        assert task.status.state == TaskState.SUBMITTED
        assert task.artifacts == []
        assert task.history is None
        assert task.createdAt is not None
        assert task.updatedAt is not None

    def test_task_with_artifacts(self):
        """Test task with artifacts."""
        artifact = TaskArtifact(parts=[TextPart(text="Done")])
        status = TaskStatus(state=TaskState.COMPLETED)
        task = Task(
            contextId="ctx-123",
            status=status,
            artifacts=[artifact],
        )
        assert len(task.artifacts) == 1


class TestAgentCard:
    """Test AgentCard model."""

    def test_agent_card_creation(self):
        """Test creating an agent card."""
        card = AgentCard(
            name="TestAgent",
            description="A test agent",
        )
        assert card.name == "TestAgent"
        assert card.description == "A test agent"
        assert card.protocolVersion == "1.0"
        assert card.capabilities.streaming is False
        assert card.capabilities.pushNotifications is False
        assert card.securitySchemes == []
        assert card.skills == []

    def test_agent_card_with_skills(self):
        """Test agent card with skills."""
        skill = AgentSkill(
            name="search",
            description="Search for information",
            examples=["Search for weather", "Find documents"],
        )
        card = AgentCard(
            name="SearchAgent",
            description="An agent that searches",
            skills=[skill],
        )
        assert len(card.skills) == 1
        assert card.skills[0].name == "search"

    def test_agent_card_with_capabilities(self):
        """Test agent card with capabilities."""
        caps = AgentCapabilities(streaming=True, pushNotifications=True)
        card = AgentCard(
            name="StreamAgent",
            description="Streaming agent",
            capabilities=caps,
        )
        assert card.capabilities.streaming is True
        assert card.capabilities.pushNotifications is True

    def test_agent_card_with_security(self):
        """Test agent card with security schemes."""
        security = SecurityScheme(
            type="apiKey",
            name="X-API-Key",
            in_="header",
        )
        card = AgentCard(
            name="SecureAgent",
            description="Secure agent",
            securitySchemes=[security],
        )
        assert len(card.securitySchemes) == 1
        assert card.securitySchemes[0].type == "apiKey"

    def test_agent_card_with_provider(self):
        """Test agent card with provider info."""
        provider = ProviderInfo(
            organization="Test Org",
            url="https://example.com",
            contact="support@example.com",
        )
        card = AgentCard(
            name="Agent",
            description="Description",
            provider=provider,
        )
        assert card.provider.organization == "Test Org"


class TestRequestResponse:
    """Test request/response models."""

    def test_send_message_request(self):
        """Test SendMessageRequest model."""
        msg = Message(role=MessageRole.USER, parts=[TextPart(text="Hello")])
        req = SendMessageRequest(message=msg, contextId="ctx-123")

        assert req.message == msg
        assert req.contextId == "ctx-123"

    def test_send_message_response(self):
        """Test SendMessageResponse model."""
        status = TaskStatus(state=TaskState.SUBMITTED)
        task = Task(contextId="ctx-123", status=status)
        resp = SendMessageResponse(task=task)

        assert resp.task == task
        assert resp.message is None

    def test_get_task_request(self):
        """Test GetTaskRequest model."""
        req = GetTaskRequest(taskId="task-123", includeHistory=True)
        assert req.taskId == "task-123"
        assert req.includeHistory is True

    def test_get_task_response(self):
        """Test GetTaskResponse model."""
        status = TaskStatus(state=TaskState.COMPLETED)
        task = Task(contextId="ctx-123", status=status)
        resp = GetTaskResponse(task=task)
        assert resp.task == task

    def test_list_tasks_request(self):
        """Test ListTasksRequest model."""
        req = ListTasksRequest(
            contextId="ctx-123",
            status=TaskState.COMPLETED,
            limit=50,
            offset=10,
        )
        assert req.contextId == "ctx-123"
        assert req.status == TaskState.COMPLETED
        assert req.limit == 50
        assert req.offset == 10

    def test_list_tasks_response(self):
        """Test ListTasksResponse model."""
        status = TaskStatus(state=TaskState.COMPLETED)
        tasks = [Task(contextId="ctx-123", status=status)]
        resp = ListTasksResponse(tasks=tasks, total=1, hasMore=False)

        assert len(resp.tasks) == 1
        assert resp.total == 1
        assert resp.hasMore is False


class TestStreamingEvents:
    """Test streaming event models."""

    def test_task_status_update_event(self):
        """Test TaskStatusUpdateEvent model."""
        status = TaskStatus(state=TaskState.WORKING, message="Processing")
        event = TaskStatusUpdateEvent(taskId="task-123", status=status)

        assert event.type == "taskStatus"
        assert event.taskId == "task-123"
        assert event.status.state == TaskState.WORKING

    def test_task_artifact_update_event(self):
        """Test TaskArtifactUpdateEvent model."""
        artifact = TaskArtifact(parts=[TextPart(text="Result")])
        event = TaskArtifactUpdateEvent(taskId="task-123", artifact=artifact)

        assert event.type == "taskArtifact"
        assert event.taskId == "task-123"
        assert len(event.artifact.parts) == 1


class TestA2AError:
    """Test A2AError model."""

    def test_error_creation(self):
        """Test creating an error."""
        error = A2AError(code="NOT_FOUND", message="Task not found")
        assert error.code == "NOT_FOUND"
        assert error.message == "Task not found"
        assert error.details is None
        assert error.timestamp is not None

    def test_error_with_details(self):
        """Test error with details."""
        error = A2AError(
            code="VALIDATION_ERROR",
            message="Invalid request",
            details={"field": "message", "reason": "required"},
        )
        assert error.details == {"field": "message", "reason": "required"}
