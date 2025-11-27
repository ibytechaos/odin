"""Task management for A2A protocol."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any

from odin.logging import get_logger
from odin.protocols.a2a.models import (
    Message,
    MessageRole,
    Task,
    TaskArtifact,
    TaskState,
    TaskStatus,
)

logger = get_logger(__name__)


class TaskManager:
    """Manages task lifecycle and storage."""

    def __init__(self):
        """Initialize task manager."""
        self._tasks: dict[str, Task] = {}
        self._context_tasks: dict[str, list[str]] = defaultdict(list)
        self._task_locks: dict[str, asyncio.Lock] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def create_task(
        self,
        context_id: str,
        initial_message: Message,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Create a new task.

        Args:
            context_id: Context identifier
            initial_message: Initial message that created the task
            metadata: Optional task metadata

        Returns:
            Created task
        """
        task = Task(
            contextId=context_id,
            status=TaskStatus(state=TaskState.SUBMITTED),
            history=[initial_message],
            metadata=metadata or {},
        )

        async with self._lock:
            self._tasks[task.id] = task
            self._context_tasks[context_id].append(task.id)
            self._task_locks[task.id] = asyncio.Lock()

        logger.info("Task created", task_id=task.id, context_id=context_id)
        await self._notify_subscribers(task.id, task)

        return task

    async def get_task(self, task_id: str, include_history: bool = False) -> Task | None:
        """Get task by ID.

        Args:
            task_id: Task identifier
            include_history: Whether to include message history

        Returns:
            Task if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if task and not include_history:
            # Return copy without history
            task_dict = task.model_dump()
            task_dict["history"] = None
            return Task(**task_dict)
        return task

    async def update_task_status(
        self,
        task_id: str,
        state: TaskState,
        message: str | None = None,
    ) -> Task | None:
        """Update task status.

        Args:
            task_id: Task identifier
            state: New task state
            message: Optional status message

        Returns:
            Updated task if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        async with self._task_locks[task_id]:
            task.status = TaskStatus(state=state, message=message)
            task.updatedAt = datetime.utcnow()

        logger.info(
            "Task status updated",
            task_id=task_id,
            state=state,
            message=message,
        )
        await self._notify_subscribers(task_id, task)

        return task

    async def add_task_artifact(
        self,
        task_id: str,
        artifact: TaskArtifact,
    ) -> Task | None:
        """Add artifact to task.

        Args:
            task_id: Task identifier
            artifact: Task artifact to add

        Returns:
            Updated task if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        async with self._task_locks[task_id]:
            task.artifacts.append(artifact)
            task.updatedAt = datetime.utcnow()

        logger.info(
            "Task artifact added",
            task_id=task_id,
            artifact_id=artifact.artifactId,
        )
        await self._notify_subscribers(task_id, task)

        return task

    async def add_task_message(
        self,
        task_id: str,
        message: Message,
    ) -> Task | None:
        """Add message to task history.

        Args:
            task_id: Task identifier
            message: Message to add

        Returns:
            Updated task if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        async with self._task_locks[task_id]:
            if task.history is None:
                task.history = []
            task.history.append(message)
            task.updatedAt = datetime.utcnow()

        logger.info(
            "Message added to task",
            task_id=task_id,
            message_id=message.messageId,
            role=message.role,
        )

        return task

    async def list_tasks(
        self,
        context_id: str | None = None,
        status: TaskState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Task], int, bool]:
        """List tasks with optional filtering.

        Args:
            context_id: Filter by context ID
            status: Filter by task status
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip

        Returns:
            Tuple of (tasks, total_count, has_more)
        """
        # Get task IDs to query
        if context_id:
            task_ids = self._context_tasks.get(context_id, [])
        else:
            task_ids = list(self._tasks.keys())

        # Filter by status
        tasks = []
        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if task and (status is None or task.status.state == status):
                tasks.append(task)

        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.createdAt, reverse=True)

        # Apply pagination
        total = len(tasks)
        tasks = tasks[offset : offset + limit]
        has_more = (offset + limit) < total

        return tasks, total, has_more

    async def subscribe_to_task(self, task_id: str) -> asyncio.Queue:
        """Subscribe to task updates.

        Args:
            task_id: Task identifier

        Returns:
            Queue that will receive task updates
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[task_id].append(queue)

        logger.info("Subscribed to task updates", task_id=task_id)

        return queue

    async def unsubscribe_from_task(self, task_id: str, queue: asyncio.Queue):
        """Unsubscribe from task updates.

        Args:
            task_id: Task identifier
            queue: Queue to remove from subscribers
        """
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(queue)
                logger.info("Unsubscribed from task updates", task_id=task_id)
            except ValueError:
                pass

    async def _notify_subscribers(self, task_id: str, task: Task):
        """Notify all subscribers of task update.

        Args:
            task_id: Task identifier
            task: Updated task
        """
        if task_id not in self._subscribers:
            return

        # Send update to all subscribers
        for queue in self._subscribers[task_id]:
            try:
                await queue.put(task)
            except Exception as e:
                logger.error(
                    "Failed to notify subscriber",
                    task_id=task_id,
                    error=str(e),
                )

    async def cancel_task(self, task_id: str) -> Task | None:
        """Cancel a task.

        Args:
            task_id: Task identifier

        Returns:
            Updated task if found, None otherwise
        """
        return await self.update_task_status(
            task_id,
            TaskState.CANCELLED,
            "Task cancelled by request",
        )

    async def complete_task(
        self,
        task_id: str,
        message: str | None = None,
    ) -> Task | None:
        """Mark task as completed.

        Args:
            task_id: Task identifier
            message: Optional completion message

        Returns:
            Updated task if found, None otherwise
        """
        return await self.update_task_status(
            task_id,
            TaskState.COMPLETED,
            message or "Task completed successfully",
        )

    async def fail_task(
        self,
        task_id: str,
        error_message: str,
    ) -> Task | None:
        """Mark task as failed.

        Args:
            task_id: Task identifier
            error_message: Error description

        Returns:
            Updated task if found, None otherwise
        """
        return await self.update_task_status(
            task_id,
            TaskState.FAILED,
            error_message,
        )
