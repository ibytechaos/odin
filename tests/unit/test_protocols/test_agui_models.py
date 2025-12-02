"""Tests for AG-UI protocol models."""

import pytest

from odin.protocols.agui.models import (
    MessageRole,
    ToolCall,
    Message,
    Tool,
    RunAgentInput,
    EventType,
    AGUIEvent,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageChunkEvent,
    ToolCallChunkEvent,
    StateUpdateEvent,
)


class TestMessageRole:
    """Test MessageRole enum."""

    def test_all_roles(self):
        """Test all role values."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.TOOL.value == "tool"


class TestToolCall:
    """Test ToolCall model."""

    def test_tool_call_creation(self):
        """Test creating a tool call."""
        call = ToolCall(
            function={"name": "search", "arguments": '{"query": "test"}'},
        )
        assert call.type == "function"
        assert call.function["name"] == "search"
        assert call.id is not None

    def test_tool_call_with_custom_id(self):
        """Test tool call with custom ID."""
        call = ToolCall(
            id="call-123",
            function={"name": "greet", "arguments": '{"name": "World"}'},
        )
        assert call.id == "call-123"


class TestMessage:
    """Test Message model."""

    def test_user_message(self):
        """Test user message."""
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.tool_calls is None

    def test_assistant_message(self):
        """Test assistant message."""
        msg = Message(role=MessageRole.ASSISTANT, content="Hi there!")
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Hi there!"

    def test_assistant_message_with_tool_calls(self):
        """Test assistant message with tool calls."""
        calls = [
            ToolCall(
                id="call-1",
                function={"name": "search", "arguments": '{"q": "test"}'},
            )
        ]
        msg = Message(
            role=MessageRole.ASSISTANT,
            content=None,
            tool_calls=calls,
        )
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1

    def test_tool_message(self):
        """Test tool result message."""
        msg = Message(
            role=MessageRole.TOOL,
            content='{"result": "success"}',
            tool_call_id="call-1",
        )
        assert msg.role == MessageRole.TOOL
        assert msg.tool_call_id == "call-1"

    def test_system_message(self):
        """Test system message."""
        msg = Message(role=MessageRole.SYSTEM, content="You are a helpful assistant.")
        assert msg.role == MessageRole.SYSTEM


class TestTool:
    """Test Tool model."""

    def test_tool_creation(self):
        """Test creating a tool."""
        tool = Tool(
            name="search",
            description="Search for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        )
        assert tool.name == "search"
        assert tool.description == "Search for information"
        assert "properties" in tool.parameters


class TestRunAgentInput:
    """Test RunAgentInput model."""

    def test_run_agent_input_creation(self):
        """Test creating run agent input."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]
        input_data = RunAgentInput(
            thread_id="thread-123",
            run_id="run-456",
            messages=messages,
        )
        assert input_data.thread_id == "thread-123"
        assert input_data.run_id == "run-456"
        assert len(input_data.messages) == 1
        assert input_data.tools is None

    def test_run_agent_input_with_tools(self):
        """Test run agent input with tools."""
        tools = [
            Tool(
                name="greet",
                description="Greet someone",
                parameters={"type": "object", "properties": {}},
            )
        ]
        input_data = RunAgentInput(
            thread_id="thread-123",
            run_id="run-456",
            messages=[],
            tools=tools,
        )
        assert input_data.tools is not None
        assert len(input_data.tools) == 1


class TestEventType:
    """Test EventType enum."""

    def test_all_event_types(self):
        """Test all event type values."""
        assert EventType.RUN_STARTED.value == "RUN_STARTED"
        assert EventType.RUN_FINISHED.value == "RUN_FINISHED"
        assert EventType.RUN_ERROR.value == "RUN_ERROR"
        assert EventType.TEXT_MESSAGE_CHUNK.value == "TEXT_MESSAGE_CHUNK"
        assert EventType.TOOL_CALL_CHUNK.value == "TOOL_CALL_CHUNK"
        assert EventType.STATE_UPDATE.value == "STATE_UPDATE"


class TestRunEvents:
    """Test run lifecycle events."""

    def test_run_started_event(self):
        """Test RunStartedEvent model."""
        event = RunStartedEvent(thread_id="thread-123", run_id="run-456")
        assert event.event == EventType.RUN_STARTED
        assert event.thread_id == "thread-123"
        assert event.run_id == "run-456"

    def test_run_finished_event(self):
        """Test RunFinishedEvent model."""
        event = RunFinishedEvent(thread_id="thread-123", run_id="run-456")
        assert event.event == EventType.RUN_FINISHED
        assert event.thread_id == "thread-123"
        assert event.run_id == "run-456"

    def test_run_error_event(self):
        """Test RunErrorEvent model."""
        event = RunErrorEvent(
            thread_id="thread-123",
            run_id="run-456",
            message="Something went wrong",
            error="ValueError: Invalid input",
        )
        assert event.event == EventType.RUN_ERROR
        assert event.message == "Something went wrong"
        assert event.error == "ValueError: Invalid input"

    def test_run_error_event_without_error_detail(self):
        """Test RunErrorEvent without detailed error."""
        event = RunErrorEvent(
            thread_id="thread-123",
            run_id="run-456",
            message="Error occurred",
        )
        assert event.error is None


class TestTextMessageChunkEvent:
    """Test TextMessageChunkEvent model."""

    def test_text_chunk_event(self):
        """Test creating a text chunk event."""
        event = TextMessageChunkEvent(
            message_id="msg-123",
            delta="Hello, ",
            thread_id="thread-123",
            run_id="run-456",
        )
        assert event.event == EventType.TEXT_MESSAGE_CHUNK
        assert event.message_id == "msg-123"
        assert event.delta == "Hello, "
        assert event.thread_id == "thread-123"
        assert event.run_id == "run-456"


class TestToolCallChunkEvent:
    """Test ToolCallChunkEvent model."""

    def test_tool_call_chunk_event(self):
        """Test creating a tool call chunk event."""
        event = ToolCallChunkEvent(
            tool_call_id="call-123",
            tool_call_name="search",
            parent_message_id="msg-456",
            delta='{"query": "test"}',
            thread_id="thread-123",
            run_id="run-456",
        )
        assert event.event == EventType.TOOL_CALL_CHUNK
        assert event.tool_call_id == "call-123"
        assert event.tool_call_name == "search"
        assert event.parent_message_id == "msg-456"
        assert event.delta == '{"query": "test"}'


class TestStateUpdateEvent:
    """Test StateUpdateEvent model."""

    def test_state_update_event(self):
        """Test creating a state update event."""
        event = StateUpdateEvent(
            thread_id="thread-123",
            run_id="run-456",
            state={"key": "value", "count": 42},
        )
        assert event.event == EventType.STATE_UPDATE
        assert event.thread_id == "thread-123"
        assert event.run_id == "run-456"
        assert event.state == {"key": "value", "count": 42}

    def test_state_update_event_empty_state(self):
        """Test state update with empty state."""
        event = StateUpdateEvent(
            thread_id="thread-123",
            run_id="run-456",
            state={},
        )
        assert event.state == {}
