"""A2A Protocol Adapter for Odin framework.

This adapter implements the IProtocolAdapter interface for A2A (Agent-to-Agent) protocol,
enabling protocol-agnostic development.
"""

import asyncio
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException
from sse_starlette import EventSourceResponse

from odin.logging import get_logger
from odin.protocols.a2a.models import (
    A2AError,
    AgentCard,
    AgentSkill,
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
from odin.protocols.base_adapter import IProtocolAdapter

if TYPE_CHECKING:
    from odin.core.agent_interface import IAgent

logger = get_logger(__name__)


class A2AAdapter(IProtocolAdapter):
    """A2A (Agent-to-Agent) Protocol Adapter.

    Implements IProtocolAdapter interface for A2A protocol.
    Exposes Odin agent capabilities via the A2A protocol over HTTP/REST
    with Server-Sent Events for streaming updates.

    Example:
        ```python
        from odin.core.agent_factory import AgentFactory
        from odin.protocols.a2a import A2AAdapter

        # Create agent
        agent = AgentFactory.create_agent()

        # Create A2A adapter
        adapter = A2AAdapter(agent)

        # Run A2A server
        await adapter.run(host="0.0.0.0", port=8000)
        ```
    """

    def __init__(
        self,
        agent: IAgent,
        url: str = "http://localhost:8000",
    ):
        """Initialize A2A adapter.

        Args:
            agent: Unified agent instance
            url: Agent URL for agent card
        """
        super().__init__(agent)
        self._url = url
        self.task_manager = TaskManager()

        # Create FastAPI app
        self.app = FastAPI(
            title=f"Odin A2A Server - {agent.name}",
            description=agent.description,
            version="1.0.0",
        )

        self._setup_routes()

    def convert_tools(self) -> list[AgentSkill]:
        """Convert Odin tools to A2A skills format.

        Returns:
            List of AgentSkill objects
        """
        metadata = self.agent.get_metadata()
        tool_names = metadata.get("tools", [])

        skills = []
        for tool_name in tool_names:
            skill = AgentSkill(
                name=tool_name,
                description=f"Tool: {tool_name}",
            )
            skills.append(skill)

        return skills

    async def handle_request(self, request: Any) -> Any:
        """Handle A2A request.

        For A2A, requests are handled through the FastAPI routes.
        This method is primarily for ProtocolDispatcher integration.

        Args:
            request: A2A request

        Returns:
            A2A response
        """
        # A2A uses FastAPI routes for request handling
        # This is mainly for interface compatibility
        return None

    def _generate_agent_card(self) -> AgentCard:
        """Generate agent card from agent metadata.

        Returns:
            AgentCard for self-description
        """
        metadata = self.agent.get_metadata()
        skills = self.convert_tools()

        return AgentCard(
            name=metadata.get("name", "Odin Agent"),
            description=metadata.get("description", "AI Agent powered by Odin"),
            url=self._url,
            skills=skills,
            supportedContentTypes=["text/plain", "application/json"],
            version="1.0.0",
        )

    def get_app(self) -> FastAPI:
        """Get FastAPI application.

        Use this when mounting the A2A adapter standalone.

        Returns:
            FastAPI application instance
        """
        return self.app

    def _setup_routes(self):
        """Setup FastAPI routes for A2A protocol."""

        @self.app.get("/.well-known/agent-card")
        async def get_agent_card() -> AgentCard:
            """Get agent card (self-describing capabilities)."""
            logger.info("A2A: Agent card requested")
            return self._generate_agent_card()

        @self.app.post("/message/send")
        async def send_message(request: SendMessageRequest) -> SendMessageResponse:
            """Send a message to the agent."""
            logger.info(
                "A2A: Message received",
                message_id=request.message.messageId,
                role=request.message.role,
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
            """Send a message with streaming response."""
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

                            event = TaskStatusUpdateEvent(
                                taskId=updated_task.id,
                                status=updated_task.status,
                            )
                            yield {
                                "event": "taskStatus",
                                "data": event.model_dump_json(),
                            }

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

            task = await self.task_manager.get_task(task_id)
            if not task:
                raise HTTPException(
                    status_code=404,
                    detail=A2AError(
                        code="TASK_NOT_FOUND",
                        message=f"Task {task_id} not found",
                    ).model_dump(),
                )

            queue = await self.task_manager.subscribe_to_task(task_id)

            async def event_generator():
                """Generate SSE events for task updates."""
                try:
                    while True:
                        updated_task = await asyncio.wait_for(queue.get(), timeout=300.0)

                        event = TaskStatusUpdateEvent(
                            taskId=updated_task.id,
                            status=updated_task.status,
                        )
                        yield {
                            "event": "taskStatus",
                            "data": event.model_dump_json(),
                        }

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
        """Process a message using the unified agent.

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
                "A2A: Processing message via agent",
                task_id=task_id,
                text_preview=combined_text[:100] if len(combined_text) > 100 else combined_text,
            )

            # Execute through unified agent
            events = []
            async for event in self.agent.execute(
                input=combined_text,
                thread_id=task_id,
            ):
                events.append(event)

            # Extract result from agent events
            result = None
            for event in events:
                if event.get("type") == "message":
                    result = event.get("content")
                    break

            result_text = result if result else "Message processed successfully"

            # Create response artifact
            artifact = TaskArtifact(
                parts=[TextPart(text=result_text)],
                metadata={"source": "odin_agent"},
            )

            await self.task_manager.add_task_artifact(task_id, artifact)

            # Mark as completed
            await self.task_manager.complete_task(task_id)

        except Exception as e:
            logger.error("A2A: Message processing failed", task_id=task_id, error=str(e))
            await self.task_manager.fail_task(task_id, str(e))

    async def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run A2A server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        import uvicorn

        # Update URL for agent card
        self._url = f"http://{host}:{port}"

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
