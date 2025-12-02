"""Tests for progress tracking utilities."""

import pytest
import asyncio
from datetime import datetime

from odin.utils.progress import (
    ProgressStatus,
    ProgressEvent,
    ProgressSession,
    ProgressTracker,
    TaskManager,
)


class TestProgressStatus:
    """Test ProgressStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert ProgressStatus.PENDING.value == "pending"
        assert ProgressStatus.RUNNING.value == "running"
        assert ProgressStatus.COMPLETED.value == "completed"
        assert ProgressStatus.FAILED.value == "failed"
        assert ProgressStatus.CANCELLED.value == "cancelled"


class TestProgressEvent:
    """Test ProgressEvent dataclass."""

    def test_event_creation(self):
        """Test creating a progress event."""
        now = datetime.utcnow()
        event = ProgressEvent(
            timestamp=now,
            event_type="progress",
            message="Processing",
            data={"count": 5},
            sequence=0,
        )

        assert event.timestamp == now
        assert event.event_type == "progress"
        assert event.message == "Processing"
        assert event.data == {"count": 5}
        assert event.sequence == 0

    def test_event_to_dict(self):
        """Test event serialization."""
        now = datetime.utcnow()
        event = ProgressEvent(
            timestamp=now,
            event_type="started",
            message="Starting",
            data={},
            sequence=1,
        )

        result = event.to_dict()

        assert result["timestamp"] == now.isoformat()
        assert result["event_type"] == "started"
        assert result["message"] == "Starting"
        assert result["data"] == {}
        assert result["sequence"] == 1

    def test_event_default_data(self):
        """Test event with default data."""
        now = datetime.utcnow()
        event = ProgressEvent(
            timestamp=now,
            event_type="info",
            message="Info",
        )

        assert event.data == {}


class TestProgressSession:
    """Test ProgressSession dataclass."""

    def test_session_creation(self):
        """Test creating a progress session."""
        now = datetime.utcnow()
        session = ProgressSession(
            session_id="test-123",
            created_at=now,
        )

        assert session.session_id == "test-123"
        assert session.created_at == now
        assert session.status == ProgressStatus.PENDING
        assert session.events == []
        assert session.result is None
        assert session.error is None
        assert session.metadata == {}

    def test_session_to_dict(self):
        """Test session serialization."""
        now = datetime.utcnow()
        session = ProgressSession(
            session_id="test-456",
            created_at=now,
            status=ProgressStatus.COMPLETED,
            result={"data": "test"},
            metadata={"task": "test_task"},
        )

        result = session.to_dict()

        assert result["session_id"] == "test-456"
        assert result["created_at"] == now.isoformat()
        assert result["status"] == "completed"
        assert result["event_count"] == 0
        assert result["result"] == {"data": "test"}
        assert result["error"] is None
        assert result["metadata"] == {"task": "test_task"}


class TestProgressTracker:
    """Test ProgressTracker class."""

    def test_init(self):
        """Test tracker initialization."""
        tracker = ProgressTracker()
        assert tracker.max_sessions == 1000
        assert tracker.max_events_per_session == 10000

    def test_custom_init(self):
        """Test tracker with custom limits."""
        tracker = ProgressTracker(max_sessions=10, max_events_per_session=100)
        assert tracker.max_sessions == 10
        assert tracker.max_events_per_session == 100

    def test_create_session(self):
        """Test creating a session."""
        tracker = ProgressTracker()
        session_id = tracker.create_session()

        assert session_id is not None
        assert len(session_id) > 0

        session = tracker.get_session(session_id)
        assert session is not None
        assert session.status == ProgressStatus.PENDING

    def test_create_session_with_id(self):
        """Test creating a session with custom ID."""
        tracker = ProgressTracker()
        session_id = tracker.create_session(session_id="my-session")

        assert session_id == "my-session"

    def test_create_session_with_metadata(self):
        """Test creating a session with metadata."""
        tracker = ProgressTracker()
        session_id = tracker.create_session(metadata={"task": "test"})

        session = tracker.get_session(session_id)
        assert session.metadata == {"task": "test"}

    def test_add_event(self):
        """Test adding events to a session."""
        tracker = ProgressTracker()
        session_id = tracker.create_session()

        tracker.add_event(session_id, "started", "Starting operation")
        tracker.add_event(session_id, "progress", "Working", {"step": 1})

        session = tracker.get_session(session_id)
        assert len(session.events) == 2
        assert session.events[0].event_type == "started"
        assert session.events[0].sequence == 0
        assert session.events[1].event_type == "progress"
        assert session.events[1].sequence == 1

    def test_add_event_nonexistent_session(self):
        """Test adding event to nonexistent session."""
        tracker = ProgressTracker()
        # Should not raise
        tracker.add_event("nonexistent", "test", "Test")

    def test_add_event_updates_status(self):
        """Test that certain events update session status."""
        tracker = ProgressTracker()
        session_id = tracker.create_session()

        tracker.add_event(session_id, "started", "Starting")
        assert tracker.get_session(session_id).status == ProgressStatus.RUNNING

        tracker.add_event(session_id, "completed", "Done")
        assert tracker.get_session(session_id).status == ProgressStatus.COMPLETED

    def test_add_event_failed_status(self):
        """Test failed event updates status."""
        tracker = ProgressTracker()
        session_id = tracker.create_session()

        tracker.add_event(session_id, "failed", "Error occurred")
        assert tracker.get_session(session_id).status == ProgressStatus.FAILED

    def test_add_event_cancelled_status(self):
        """Test cancelled event updates status."""
        tracker = ProgressTracker()
        session_id = tracker.create_session()

        tracker.add_event(session_id, "cancelled", "Cancelled by user")
        assert tracker.get_session(session_id).status == ProgressStatus.CANCELLED

    def test_add_event_limit(self):
        """Test event limit per session."""
        tracker = ProgressTracker(max_events_per_session=3)
        session_id = tracker.create_session()

        for i in range(5):
            tracker.add_event(session_id, "progress", f"Step {i}")

        session = tracker.get_session(session_id)
        assert len(session.events) == 3

    def test_set_status(self):
        """Test setting session status."""
        tracker = ProgressTracker()
        session_id = tracker.create_session()

        tracker.set_status(session_id, ProgressStatus.RUNNING)
        assert tracker.get_session(session_id).status == ProgressStatus.RUNNING

    def test_set_status_nonexistent(self):
        """Test setting status on nonexistent session."""
        tracker = ProgressTracker()
        # Should not raise
        tracker.set_status("nonexistent", ProgressStatus.COMPLETED)

    def test_set_result(self):
        """Test setting session result."""
        tracker = ProgressTracker()
        session_id = tracker.create_session()

        tracker.set_result(session_id, {"data": "test"})
        assert tracker.get_session(session_id).result == {"data": "test"}

    def test_set_error(self):
        """Test setting session error."""
        tracker = ProgressTracker()
        session_id = tracker.create_session()

        tracker.set_error(session_id, "Something went wrong")

        session = tracker.get_session(session_id)
        assert session.error == "Something went wrong"
        assert session.status == ProgressStatus.FAILED

    def test_get_events(self):
        """Test getting events with pagination."""
        tracker = ProgressTracker()
        session_id = tracker.create_session()

        for i in range(5):
            tracker.add_event(session_id, "progress", f"Step {i}")

        result = tracker.get_events(session_id, cursor=0, limit=3)

        assert result["session_id"] == session_id
        assert result["status"] == "pending"
        assert len(result["events"]) == 3
        assert result["next_cursor"] == 3
        assert result["total_events"] == 5
        assert result["has_more"] is True

    def test_get_events_second_page(self):
        """Test getting second page of events."""
        tracker = ProgressTracker()
        session_id = tracker.create_session()

        for i in range(5):
            tracker.add_event(session_id, "progress", f"Step {i}")

        result = tracker.get_events(session_id, cursor=3, limit=3)

        assert len(result["events"]) == 2
        assert result["next_cursor"] == 5
        assert result["has_more"] is False

    def test_get_events_nonexistent(self):
        """Test getting events from nonexistent session."""
        tracker = ProgressTracker()

        result = tracker.get_events("nonexistent")

        assert result["status"] == "not_found"
        assert result["events"] == []

    def test_delete_session(self):
        """Test deleting a session."""
        tracker = ProgressTracker()
        session_id = tracker.create_session()

        assert tracker.delete_session(session_id) is True
        assert tracker.get_session(session_id) is None

    def test_delete_nonexistent_session(self):
        """Test deleting nonexistent session."""
        tracker = ProgressTracker()

        assert tracker.delete_session("nonexistent") is False

    def test_list_sessions(self):
        """Test listing sessions."""
        tracker = ProgressTracker()
        tracker.create_session(session_id="session1")
        tracker.create_session(session_id="session2")

        sessions = tracker.list_sessions()

        assert len(sessions) == 2
        session_ids = [s["session_id"] for s in sessions]
        assert "session1" in session_ids
        assert "session2" in session_ids

    def test_list_sessions_filter_by_status(self):
        """Test filtering sessions by status."""
        tracker = ProgressTracker()
        s1 = tracker.create_session()
        s2 = tracker.create_session()

        tracker.set_status(s1, ProgressStatus.COMPLETED)

        completed = tracker.list_sessions(status=ProgressStatus.COMPLETED)
        pending = tracker.list_sessions(status=ProgressStatus.PENDING)

        assert len(completed) == 1
        assert len(pending) == 1

    def test_list_sessions_limit(self):
        """Test session listing with limit."""
        tracker = ProgressTracker()
        for i in range(5):
            tracker.create_session(session_id=f"session{i}")

        sessions = tracker.list_sessions(limit=3)
        assert len(sessions) == 3

    def test_cleanup_old_sessions(self):
        """Test automatic cleanup of old sessions."""
        tracker = ProgressTracker(max_sessions=3)

        # Create more sessions than the limit
        for i in range(5):
            tracker.create_session(session_id=f"session{i}")

        # Should have only max_sessions
        sessions = tracker.list_sessions()
        assert len(sessions) == 3


class TestTaskManager:
    """Test TaskManager class."""

    @pytest.mark.asyncio
    async def test_start_task(self):
        """Test starting a background task."""
        manager = TaskManager()

        async def test_coro():
            await asyncio.sleep(0.01)
            return "done"

        task_id = await manager.start_task("task1", test_coro())

        assert task_id == "task1"

        # Wait for task to complete
        await asyncio.sleep(0.1)

        status = await manager.get_task_status("task1")
        # Task should be removed after completion
        assert status["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test cancelling a task."""
        manager = TaskManager()

        async def long_running():
            await asyncio.sleep(10)
            return "done"

        await manager.start_task("task1", long_running())

        # Give task time to start
        await asyncio.sleep(0.01)

        result = await manager.cancel_task("task1")
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self):
        """Test cancelling nonexistent task."""
        manager = TaskManager()

        result = await manager.cancel_task("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_task_status_running(self):
        """Test getting status of running task."""
        manager = TaskManager()

        async def long_running():
            await asyncio.sleep(10)
            return "done"

        await manager.start_task("task1", long_running())

        # Give task time to start
        await asyncio.sleep(0.01)

        status = await manager.get_task_status("task1")
        assert status["status"] == "running"

        # Cleanup
        await manager.cancel_task("task1")

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self):
        """Test getting status of nonexistent task."""
        manager = TaskManager()

        status = await manager.get_task_status("nonexistent")
        assert status["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        """Test listing tasks."""
        manager = TaskManager()

        async def long_running():
            await asyncio.sleep(10)

        await manager.start_task("task1", long_running())
        await manager.start_task("task2", long_running())

        tasks = await manager.list_tasks()
        assert len(tasks) == 2

        # Cleanup
        await manager.cancel_all()

    @pytest.mark.asyncio
    async def test_cancel_all(self):
        """Test cancelling all tasks."""
        manager = TaskManager()

        async def long_running():
            await asyncio.sleep(10)

        await manager.start_task("task1", long_running())
        await manager.start_task("task2", long_running())

        # Give tasks time to start
        await asyncio.sleep(0.01)

        count = await manager.cancel_all()
        assert count == 2

    @pytest.mark.asyncio
    async def test_start_task_replaces_existing(self):
        """Test that starting task with same ID replaces existing."""
        manager = TaskManager()

        async def task1():
            await asyncio.sleep(10)
            return "task1"

        async def task2():
            await asyncio.sleep(0.01)
            return "task2"

        await manager.start_task("task", task1())
        await asyncio.sleep(0.01)  # Let task1 start

        # Starting task with same ID should cancel task1
        await manager.start_task("task", task2())

        # Wait for task2 to complete
        await asyncio.sleep(0.1)

        # Task should be gone after completion
        status = await manager.get_task_status("task")
        assert status["status"] == "not_found"
