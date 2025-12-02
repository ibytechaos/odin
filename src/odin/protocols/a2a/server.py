"""A2A Server implementation for Odin framework."""
from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException
from sse_starlette import EventSourceResponse

from odin.logging import get_logger
from odin.protocols.a2a.agent_card import AgentCardGenerator, create_default_agent_card
from odin.protocols.a2a.models import (
    A2AError,
    AgentCard,
    GetTaskResponse,
    ListTasksResponse,
    Message,
    SendMessageRequest,
    SendMessageResponse,
    TaskArtifact,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
)
from odin.protocols.a2a.task_manager import TaskManager

if TYPE_CHECKING:
    from odin.core.odin import Odin

logger = get_logger(__name__)


class A2AServer:
    """A2A (Agent-to-Agent) Protocol Server.

    Exposes Odin agent capabilities via the A2A protocol over HTTP/REST
    with Server-Sent Events for streaming updates.

    Example:
        ```python
        from odin import Odin
        from odin.protocols.a2a import A2AServer

        app = Odin()
        await app.initialize()

        # Register plugins...

        # Start A2A server
        a2a_server = A2AServer(app, name="my-agent")
        await a2a_server.run(host="0.0.0.0", port=8000)
        ```
    """

    def __init__(
        self,
        odin_app: Odin,
        name: str | None = None,
        description: str | None = None,
        agent_card_generator: AgentCardGenerator | None = None,
    ):
        """Initialize A2A server.

        Args:
            odin_app: Odin framework instance
            name: Agent name
            description: Agent description
            agent_card_generator: Optional custom agent card generator
        """
        self.odin_app = odin_app
        self.task_manager = TaskManager()

        # Setup agent card generator
        if agent_card_generator:
            self.agent_card_generator = agent_card_generator
        else:
            self.agent_card_generator = create_default_agent_card(
                odin_app, name, description
            )

        # Create FastAPI app
        self.app = FastAPI(
            title=name or "Odin A2A Server",
            description=description or "Agent-to-Agent protocol server",
            version="1.0.0",
        )

        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes for A2A protocol."""

        @self.app.get("/.well-known/agent-card")
        async def get_agent_card() -> AgentCard:
            """Get agent card (self-describing capabilities)."""
            logger.info("A2A: Agent card requested")
            card = await self.agent_card_generator.generate()
            return card

        @self.app.post("/message/send")
        async def send_message(request: SendMessageRequest) -> SendMessageResponse:
            """Send a message to the agent.

            Creates a task and processes the message.
            """
            logger.info(
                "A2A: Message received",
                message_id=request.message.messageId,
                role=request.message.role,
                parts=len(request.message.parts),
            )

            try:
                # Create task
                context_id = request.contextId or request.message.contextId or "default"
                task = await self.task_manager.create_task(
                    context_id=context_id,
                    initial_message=request.message,
                )

                # Process message asynchronously
                _task = asyncio.create_task(self._process_message(task.id, request.message))
                _ = _task  # Store reference to avoid garbage collection

                return SendMessageResponse(task=task)

            except Exception as e:
                logger.error("A2A: Failed to send message", error=str(e))
                raise HTTPException(
                    status_code=500,
                    detail=A2AError(
                        code="INTERNAL_ERROR",
                        message=f"Failed to process message: {e!s}",
                    ).model_dump(),
                ) from e

        @self.app.post("/message/send/streaming")
        async def send_streaming_message(request: SendMessageRequest):
            """Send a message with streaming response.

            Returns Server-Sent Events with task updates.
            """
            logger.info(
                "A2A: Streaming message received",
                message_id=request.message.messageId,
            )

            try:
                # Create task
                context_id = request.contextId or request.message.contextId or "default"
                task = await self.task_manager.create_task(
                    context_id=context_id,
                    initial_message=request.message,
                )

                # Subscribe to task updates
                queue = await self.task_manager.subscribe_to_task(task.id)

                async def event_generator():
                    """Generate SSE events for task updates."""
                    try:
                        # Send initial task
                        yield {
                            "event": "taskCreated",
                            "data": task.model_dump_json(),
                        }

                        # Process message in background
                        _bg_task = asyncio.create_task(
                            self._process_message(task.id, request.message)
                        )
                        _ = _bg_task  # Store reference to avoid garbage collection

                        # Stream updates
                        while True:
                            updated_task = await asyncio.wait_for(
                                queue.get(), timeout=60.0
                            )

                            # Send status update
                            event = TaskStatusUpdateEvent(
                                taskId=updated_task.id,
                                status=updated_task.status,
                            )
                            yield {
                                "event": "taskStatus",
                                "data": event.model_dump_json(),
                            }

                            # Send artifact updates
                            if updated_task.artifacts:
                                for artifact in updated_task.artifacts:
                                    event = TaskArtifactUpdateEvent(
                                        taskId=updated_task.id,
                                        artifact=artifact,
                                    )
                                    yield {
                                        "event": "taskArtifact",
                                        "data": event.model_dump_json(),
                                    }

                            # End stream on terminal states
                            if updated_task.status.state in [
                                TaskState.COMPLETED,
                                TaskState.FAILED,
                                TaskState.CANCELLED,
                                TaskState.REJECTED,
                            ]:
                                break

                    except TimeoutError:
                        logger.warning("A2A: Streaming timeout", task_id=task.id)
                    except Exception as e:
                        logger.error("A2A: Streaming error", error=str(e))
                    finally:
                        await self.task_manager.unsubscribe_from_task(task.id, queue)

                return EventSourceResponse(event_generator())

            except Exception as e:
                logger.error("A2A: Failed to send streaming message", error=str(e))
                raise HTTPException(
                    status_code=500,
                    detail=A2AError(
                        code="INTERNAL_ERROR",
                        message=f"Failed to process message: {e!s}",
                    ).model_dump(),
                ) from e

        @self.app.get("/tasks/{task_id}")
        async def get_task(task_id: str, include_history: bool = False) -> GetTaskResponse:
            """Get task by ID."""
            logger.info("A2A: Get task", task_id=task_id)

            task = await self.task_manager.get_task(task_id, include_history)
            if not task:
                raise HTTPException(
                    status_code=404,
                    detail=A2AError(
                        code="TASK_NOT_FOUND",
                        message=f"Task {task_id} not found",
                    ).model_dump(),
                )

            return GetTaskResponse(task=task)

        @self.app.get("/tasks")
        async def list_tasks(
            context_id: str | None = None,
            status: TaskState | None = None,
            limit: int = 100,
            offset: int = 0,
        ) -> ListTasksResponse:
            """List tasks with optional filtering."""
            logger.info(
                "A2A: List tasks",
                context_id=context_id,
                status=status,
                limit=limit,
                offset=offset,
            )

            tasks, total, has_more = await self.task_manager.list_tasks(
                context_id=context_id,
                status=status,
                limit=limit,
                offset=offset,
            )

            return ListTasksResponse(
                tasks=tasks,
                total=total,
                hasMore=has_more,
            )

        @self.app.get("/tasks/{task_id}/subscribe")
        async def subscribe_to_task(task_id: str):
            """Subscribe to task updates via SSE."""
            logger.info("A2A: Subscribe to task", task_id=task_id)

            # Check task exists
            task = await self.task_manager.get_task(task_id)
            if not task:
                raise HTTPException(
                    status_code=404,
                    detail=A2AError(
                        code="TASK_NOT_FOUND",
                        message=f"Task {task_id} not found",
                    ).model_dump(),
                )

            # Subscribe to updates
            queue = await self.task_manager.subscribe_to_task(task_id)

            async def event_generator():
                """Generate SSE events for task updates."""
                try:
                    while True:
                        updated_task = await asyncio.wait_for(queue.get(), timeout=300.0)

                        # Send status update
                        event = TaskStatusUpdateEvent(
                            taskId=updated_task.id,
                            status=updated_task.status,
                        )
                        yield {
                            "event": "taskStatus",
                            "data": event.model_dump_json(),
                        }

                        # End stream on terminal states
                        if updated_task.status.state in [
                            TaskState.COMPLETED,
                            TaskState.FAILED,
                            TaskState.CANCELLED,
                            TaskState.REJECTED,
                        ]:
                            break

                except TimeoutError:
                    logger.warning("A2A: Subscription timeout", task_id=task_id)
                except Exception as e:
                    logger.error("A2A: Subscription error", error=str(e))
                finally:
                    await self.task_manager.unsubscribe_from_task(task_id, queue)

            return EventSourceResponse(event_generator())

    async def _process_message(self, task_id: str, message: Message):
        """Process a message and update task.

        Args:
            task_id: Task ID
            message: Message to process
        """
        try:
            # Update task to WORKING state
            await self.task_manager.update_task_status(
                task_id, TaskState.WORKING, "Processing message"
            )

            # Extract text from message parts
            text_parts = [
                part.text for part in message.parts if isinstance(part, TextPart)
            ]
            combined_text = " ".join(text_parts)

            logger.info(
                "A2A: Processing message",
                task_id=task_id,
                text_preview=combined_text[:100],
            )

            # Try to route message to appropriate tool
            result = await self._route_message_to_tool(combined_text)

            # Create response artifact
            artifact = TaskArtifact(
                parts=[TextPart(text=json.dumps(result, indent=2))],
                metadata={"source": "odin_tool"},
            )

            await self.task_manager.add_task_artifact(task_id, artifact)

            # Mark as completed
            await self.task_manager.complete_task(task_id)

        except Exception as e:
            logger.error("A2A: Message processing failed", task_id=task_id, error=str(e))
            await self.task_manager.fail_task(task_id, str(e))

    async def _route_message_to_tool(self, text: str) -> dict[str, Any]:
        """Route message to appropriate tool (simple routing logic).

        Args:
            text: Message text

        Returns:
            Tool execution result
        """
        # Simple routing: try to match tool names in text
        tools = self.odin_app.list_tools()

        for tool in tools:
            if tool["name"].lower() in text.lower():
                logger.info("A2A: Routing to tool", tool=tool["name"])

                # Extract parameters (simplified - in production use LLM)
                kwargs = {}

                try:
                    result = await self.odin_app.execute_tool(tool["name"], **kwargs)
                    return {
                        "tool": tool["name"],
                        "result": result,
                        "success": True,
                    }
                except Exception as e:
                    return {
                        "tool": tool["name"],
                        "error": str(e),
                        "success": False,
                    }

        # No tool matched - return echo response
        return {
            "message": "Message received but no matching tool found",
            "text": text,
            "available_tools": [t["name"] for t in tools],
        }

    async def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run A2A server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        import uvicorn

        logger.info("Starting A2A server", host=host, port=port)

        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        try:
            await server.serve()
        except Exception as e:
            logger.error("A2A server error", error=str(e))
            raise
