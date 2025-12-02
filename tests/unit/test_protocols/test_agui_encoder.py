"""Tests for AG-UI event encoder."""

import pytest
import json

from odin.protocols.agui.encoder import EventEncoder
from odin.protocols.agui.models import (
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageChunkEvent,
    ToolCallChunkEvent,
    StateUpdateEvent,
    EventType,
)


class TestEventEncoderInit:
    """Test EventEncoder initialization."""

    def test_default_init(self):
        """Test default initialization."""
        encoder = EventEncoder()
        assert encoder.accept == "text/event-stream"
        assert encoder._content_type == "text/event-stream"

    def test_custom_accept_header(self):
        """Test initialization with custom accept header."""
        encoder = EventEncoder(accept="application/json")
        assert encoder.accept == "application/json"

    def test_get_content_type(self):
        """Test get_content_type method."""
        encoder = EventEncoder()
        assert encoder.get_content_type() == "text/event-stream"


class TestEventEncoderEncode:
    """Test EventEncoder.encode method."""

    def test_encode_run_started_event(self):
        """Test encoding run started event."""
        encoder = EventEncoder()
        event = RunStartedEvent(thread_id="thread-123", run_id="run-456")

        result = encoder.encode(event)

        # Should be SSE format: data: {json}\n\n
        assert result.startswith("data: ")
        assert result.endswith("\n\n")

        # Extract JSON
        json_str = result[6:-2]  # Remove "data: " prefix and "\n\n" suffix
        data = json.loads(json_str)

        assert data["event"] == "RUN_STARTED"
        assert data["thread_id"] == "thread-123"
        assert data["run_id"] == "run-456"

    def test_encode_run_finished_event(self):
        """Test encoding run finished event."""
        encoder = EventEncoder()
        event = RunFinishedEvent(thread_id="thread-123", run_id="run-456")

        result = encoder.encode(event)
        json_str = result[6:-2]
        data = json.loads(json_str)

        assert data["event"] == "RUN_FINISHED"

    def test_encode_run_error_event(self):
        """Test encoding run error event."""
        encoder = EventEncoder()
        event = RunErrorEvent(
            thread_id="thread-123",
            run_id="run-456",
            message="Something went wrong",
            error="ValueError",
        )

        result = encoder.encode(event)
        json_str = result[6:-2]
        data = json.loads(json_str)

        assert data["event"] == "RUN_ERROR"
        assert data["message"] == "Something went wrong"
        assert data["error"] == "ValueError"

    def test_encode_run_error_event_excludes_none(self):
        """Test that None values are excluded from encoded event."""
        encoder = EventEncoder()
        event = RunErrorEvent(
            thread_id="thread-123",
            run_id="run-456",
            message="Error occurred",
            # error is None by default
        )

        result = encoder.encode(event)
        json_str = result[6:-2]
        data = json.loads(json_str)

        # error should not be in the output since it's None
        assert "error" not in data

    def test_encode_text_message_chunk_event(self):
        """Test encoding text message chunk event."""
        encoder = EventEncoder()
        event = TextMessageChunkEvent(
            message_id="msg-123",
            delta="Hello, ",
            thread_id="thread-123",
            run_id="run-456",
        )

        result = encoder.encode(event)
        json_str = result[6:-2]
        data = json.loads(json_str)

        assert data["event"] == "TEXT_MESSAGE_CHUNK"
        assert data["message_id"] == "msg-123"
        assert data["delta"] == "Hello, "

    def test_encode_tool_call_chunk_event(self):
        """Test encoding tool call chunk event."""
        encoder = EventEncoder()
        event = ToolCallChunkEvent(
            tool_call_id="call-123",
            tool_call_name="search",
            parent_message_id="msg-456",
            delta='{"query": "test"}',
            thread_id="thread-123",
            run_id="run-456",
        )

        result = encoder.encode(event)
        json_str = result[6:-2]
        data = json.loads(json_str)

        assert data["event"] == "TOOL_CALL_CHUNK"
        assert data["tool_call_id"] == "call-123"
        assert data["tool_call_name"] == "search"
        assert data["delta"] == '{"query": "test"}'

    def test_encode_state_update_event(self):
        """Test encoding state update event."""
        encoder = EventEncoder()
        event = StateUpdateEvent(
            thread_id="thread-123",
            run_id="run-456",
            state={"key": "value", "nested": {"a": 1}},
        )

        result = encoder.encode(event)
        json_str = result[6:-2]
        data = json.loads(json_str)

        assert data["event"] == "STATE_UPDATE"
        assert data["state"] == {"key": "value", "nested": {"a": 1}}

    def test_encode_unicode_content(self):
        """Test encoding event with unicode content."""
        encoder = EventEncoder()
        event = TextMessageChunkEvent(
            message_id="msg-123",
            delta="你好世界 🌍",
            thread_id="thread-123",
            run_id="run-456",
        )

        result = encoder.encode(event)

        # Should use ensure_ascii=False to preserve unicode
        assert "你好世界" in result
        assert "🌍" in result

    def test_encode_special_characters(self):
        """Test encoding event with special JSON characters."""
        encoder = EventEncoder()
        event = TextMessageChunkEvent(
            message_id="msg-123",
            delta='Quote: "hello" and backslash: \\',
            thread_id="thread-123",
            run_id="run-456",
        )

        result = encoder.encode(event)
        json_str = result[6:-2]

        # Should be valid JSON
        data = json.loads(json_str)
        assert 'Quote: "hello"' in data["delta"]

    def test_encode_empty_state(self):
        """Test encoding state update with empty state."""
        encoder = EventEncoder()
        event = StateUpdateEvent(
            thread_id="thread-123",
            run_id="run-456",
            state={},
        )

        result = encoder.encode(event)
        json_str = result[6:-2]
        data = json.loads(json_str)

        assert data["state"] == {}


class TestEventEncoderMultipleEvents:
    """Test encoding multiple events in sequence."""

    def test_encode_sequence_of_events(self):
        """Test encoding a sequence of events."""
        encoder = EventEncoder()

        events = [
            RunStartedEvent(thread_id="t1", run_id="r1"),
            TextMessageChunkEvent(
                message_id="m1", delta="Hello", thread_id="t1", run_id="r1"
            ),
            TextMessageChunkEvent(
                message_id="m1", delta=" World", thread_id="t1", run_id="r1"
            ),
            RunFinishedEvent(thread_id="t1", run_id="r1"),
        ]

        results = [encoder.encode(event) for event in events]

        # All should be valid SSE format
        for result in results:
            assert result.startswith("data: ")
            assert result.endswith("\n\n")

        # First should be RUN_STARTED
        data = json.loads(results[0][6:-2])
        assert data["event"] == "RUN_STARTED"

        # Last should be RUN_FINISHED
        data = json.loads(results[-1][6:-2])
        assert data["event"] == "RUN_FINISHED"
