"""Progress tracking for long-running operations.

This module provides a session-based event tracking system for
monitoring progress of asynchronous operations like auto-reply,
deep research, etc.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class ProgressStatus(str, Enum):
    """Progress status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressEvent:
    """A single progress event."""

    timestamp: datetime
    event_type: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    sequence: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "message": self.message,
            "data": self.data,
            "sequence": self.sequence,
        }


@dataclass
class ProgressSession:
    """A progress tracking session."""

    session_id: str
    created_at: datetime
    status: ProgressStatus = ProgressStatus.PENDING
    events: list[ProgressEvent] = field(default_factory=list)
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "event_count": len(self.events),
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


class ProgressTracker:
    """Session-based progress tracking system.

    This class provides a way to track progress of long-running
    operations with event streaming support.

    Example:
        ```python
        tracker = ProgressTracker()

        # Create a session
        session_id = tracker.create_session(metadata={"task": "auto_reply"})

        # Add events
        tracker.add_event(session_id, "started", "Starting operation")
        tracker.add_event(session_id, "progress", "Processing item 1/10", {"current": 1, "total": 10})
        tracker.add_event(session_id, "completed", "Operation finished")

        # Get events with cursor-based pagination
        events = tracker.get_events(session_id, cursor=0)
        ```
    """

    def __init__(self, max_sessions: int = 1000, max_events_per_session: int = 10000):
        """Initialize tracker.

        Args:
            max_sessions: Maximum number of sessions to keep
            max_events_per_session: Maximum events per session
        """
        self.max_sessions = max_sessions
        self.max_events_per_session = max_events_per_session
        self._sessions: dict[str, ProgressSession] = {}
        self._lock = asyncio.Lock()

    def create_session(
        self, session_id: str | None = None, metadata: dict[str, Any] | None = None
    ) -> str:
        """Create a new progress session.

        Args:
            session_id: Optional session ID. Generated if not provided.
            metadata: Optional metadata to attach to session.

        Returns:
            Session ID
        """
        if session_id is None:
            session_id = str(uuid4())

        session = ProgressSession(
            session_id=session_id,
            created_at=datetime.utcnow(),
            status=ProgressStatus.PENDING,
            metadata=metadata or {},
        )

        self._sessions[session_id] = session

        # Cleanup old sessions if limit exceeded
        self._cleanup_old_sessions()

        return session_id

    def add_event(
        self,
        session_id: str,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Add an event to a session.

        Args:
            session_id: Session ID
            event_type: Type of event (e.g., "started", "progress", "completed")
            message: Human-readable message
            data: Optional event data
        """
        session = self._sessions.get(session_id)
        if not session:
            return

        # Enforce event limit
        if len(session.events) >= self.max_events_per_session:
            return

        event = ProgressEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            message=message,
            data=data or {},
            sequence=len(session.events),
        )
        session.events.append(event)

        # Update status based on event type
        if event_type == "started":
            session.status = ProgressStatus.RUNNING
        elif event_type == "completed":
            session.status = ProgressStatus.COMPLETED
        elif event_type == "failed":
            session.status = ProgressStatus.FAILED
        elif event_type == "cancelled":
            session.status = ProgressStatus.CANCELLED

    def set_status(self, session_id: str, status: ProgressStatus) -> None:
        """Set session status.

        Args:
            session_id: Session ID
            status: New status
        """
        session = self._sessions.get(session_id)
        if session:
            session.status = status

    def set_result(self, session_id: str, result: Any) -> None:
        """Set session result.

        Args:
            session_id: Session ID
            result: Result data
        """
        session = self._sessions.get(session_id)
        if session:
            session.result = result

    def set_error(self, session_id: str, error: str) -> None:
        """Set session error.

        Args:
            session_id: Session ID
            error: Error message
        """
        session = self._sessions.get(session_id)
        if session:
            session.error = error
            session.status = ProgressStatus.FAILED

    def get_session(self, session_id: str) -> ProgressSession | None:
        """Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session or None if not found
        """
        return self._sessions.get(session_id)

    def get_events(
        self, session_id: str, cursor: int = 0, limit: int = 100
    ) -> dict[str, Any]:
        """Get events from a session with cursor-based pagination.

        Args:
            session_id: Session ID
            cursor: Starting event sequence number
            limit: Maximum events to return

        Returns:
            Dictionary with session info, events, and next cursor
        """
        session = self._sessions.get(session_id)
        if not session:
            return {
                "session_id": session_id,
                "status": "not_found",
                "events": [],
                "next_cursor": cursor,
            }

        # Get events starting from cursor
        events = [
            e.to_dict()
            for e in session.events[cursor : cursor + limit]
        ]

        next_cursor = cursor + len(events)

        return {
            "session_id": session_id,
            "status": session.status.value,
            "events": events,
            "next_cursor": next_cursor,
            "total_events": len(session.events),
            "has_more": next_cursor < len(session.events),
        }

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if session was deleted
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(
        self, status: ProgressStatus | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """List sessions.

        Args:
            status: Filter by status
            limit: Maximum sessions to return

        Returns:
            List of session summaries
        """
        sessions = list(self._sessions.values())

        if status:
            sessions = [s for s in sessions if s.status == status]

        # Sort by creation time (newest first)
        sessions.sort(key=lambda s: s.created_at, reverse=True)

        return [s.to_dict() for s in sessions[:limit]]

    def _cleanup_old_sessions(self) -> None:
        """Remove old sessions if limit exceeded."""
        if len(self._sessions) <= self.max_sessions:
            return

        # Sort sessions by creation time
        sorted_sessions = sorted(
            self._sessions.items(),
            key=lambda x: x[1].created_at,
        )

        # Remove oldest sessions
        to_remove = len(self._sessions) - self.max_sessions
        for session_id, _ in sorted_sessions[:to_remove]:
            del self._sessions[session_id]


# Global progress tracker instance
progress_tracker = ProgressTracker()


# -------------------------------------------------------------------------
# Task manager for background operations
# -------------------------------------------------------------------------


class TaskManager:
    """Manager for background asyncio tasks.

    This class helps track and manage long-running async tasks
    with cancellation support.
    """

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start_task(
        self,
        task_id: str,
        coro,
        on_complete: Any = None,
    ) -> str:
        """Start a background task.

        Args:
            task_id: Unique task ID
            coro: Coroutine to run
            on_complete: Optional callback when task completes

        Returns:
            Task ID
        """
        async with self._lock:
            # Cancel existing task with same ID
            if task_id in self._tasks:
                self._tasks[task_id].cancel()

            async def wrapped():
                try:
                    result = await coro
                    if on_complete:
                        on_complete(result)
                    return result
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    if on_complete:
                        on_complete(None, error=str(e))
                    raise
                finally:
                    async with self._lock:
                        self._tasks.pop(task_id, None)

            task = asyncio.create_task(wrapped())
            self._tasks[task_id] = task

            return task_id

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task.

        Args:
            task_id: Task ID

        Returns:
            True if task was cancelled
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if task and not task.done():
                task.cancel()
                return True
            return False

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Get task status.

        Args:
            task_id: Task ID

        Returns:
            Task status information
        """
        task = self._tasks.get(task_id)
        if not task:
            return {"task_id": task_id, "status": "not_found"}

        if task.done():
            if task.cancelled():
                return {"task_id": task_id, "status": "cancelled"}
            try:
                task.result()
                return {"task_id": task_id, "status": "completed"}
            except Exception as e:
                return {"task_id": task_id, "status": "failed", "error": str(e)}
        else:
            return {"task_id": task_id, "status": "running"}

    async def list_tasks(self) -> list[dict[str, Any]]:
        """List all tasks.

        Returns:
            List of task statuses
        """
        return [await self.get_task_status(tid) for tid in self._tasks]

    async def cancel_all(self) -> int:
        """Cancel all running tasks.

        Returns:
            Number of tasks cancelled
        """
        count = 0
        async with self._lock:
            for task in self._tasks.values():
                if not task.done():
                    task.cancel()
                    count += 1
        return count


# Global task manager instance
task_manager = TaskManager()
