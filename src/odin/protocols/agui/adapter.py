"""AG-UI Protocol Adapter for Odin framework.

This adapter implements the IProtocolAdapter interface for AG-UI
(Agent-User Interaction Protocol), enabling protocol-agnostic development.
"""

import asyncio
import json
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from odin.core.agent_interface import IAgent
from odin.logging import get_logger
from odin.protocols.agui.encoder import EventEncoder
from odin.protocols.agui.models import (
    MessageRole,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageChunkEvent,
    Tool,
    ToolCallChunkEvent,
)
from odin.protocols.base_adapter import IProtocolAdapter

logger = get_logger(__name__)


class AGUIAdapter(IProtocolAdapter):
    """AG-UI (Agent-User Interaction Protocol) Adapter.

    Implements IProtocolAdapter interface for AG-UI protocol.
    Exposes Odin agent capabilities via the AG-UI protocol for generative UI
    and real-time agent interactions.

    Example:
        ```python
        from odin.core.agent_factory import AgentFactory
        from odin.protocols.agui import AGUIAdapter

        # Create agent
        agent = AgentFactory.create_agent()

        # Create AG-UI adapter
        adapter = AGUIAdapter(agent)

        # Run AG-UI server
        await adapter.run(host="0.0.0.0", port=8000)
        ```
    """

    def __init__(self, agent: IAgent, path: str = "/"):
        """Initialize AG-UI adapter.

        Args:
            agent: Unified agent instance
            path: Endpoint path (default: "/")
        """
        super().__init__(agent)
        self.path = path

        # Create FastAPI app
        self.app = FastAPI(
            title=f"Odin AG-UI Server - {agent.name}",
            description=agent.description,
            version="1.0.0",
        )

        self._setup_routes()

    def convert_tools(self) -> list[Tool]:
        """Convert Odin tools to AG-UI Tool format.

        Returns:
            List of AG-UI Tool objects
        """
        metadata = self.agent.get_metadata()
        tool_names = metadata.get("tools", [])

        agui_tools = []
        for tool_name in tool_names:
            # Basic conversion - agent should provide more details
            parameters = {
                "type": "object",
                "properties": {},
                "required": [],
            }

            agui_tool = Tool(
                name=tool_name,
                description=f"Tool: {tool_name}",
                parameters=parameters,
            )
            agui_tools.append(agui_tool)

        return agui_tools

    async def handle_request(self, request: Any) -> Any:
        """Handle AG-UI request.

        For AG-UI, requests are handled through the FastAPI routes.
        This method is primarily for ProtocolDispatcher integration.

        Args:
            request: AG-UI request

        Returns:
            AG-UI response
        """
        # AG-UI uses FastAPI routes for request handling
        return None

    def get_app(self) -> FastAPI:
        """Get FastAPI application.

        Use this when mounting the AG-UI adapter standalone.

        Returns:
            FastAPI application instance
        """
        return self.app

    def _setup_routes(self):
        """Setup FastAPI routes for AG-UI protocol."""

        @self.app.post(self.path)
        async def agentic_chat_endpoint(
            input_data: RunAgentInput,
            request: Request,
        ):
            """Main AG-UI agentic chat endpoint.

            Accepts RunAgentInput and returns Server-Sent Events stream.
            """
            logger.info(
                "AG-UI: Chat request received",
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
                message_count=len(input_data.messages),
            )

            # Create encoder based on Accept header
            accept_header = request.headers.get("accept", "text/event-stream")
            encoder = EventEncoder(accept=accept_header)

            async def event_generator():
                """Generate AG-UI events."""
                try:
                    # Emit RUN_STARTED event
                    yield encoder.encode(
                        RunStartedEvent(
                            thread_id=input_data.thread_id,
                            run_id=input_data.run_id,
                        )
                    )

                    # Process through unified agent
                    async for event in self._process_run(input_data):
                        yield encoder.encode(event)

                    # Emit RUN_FINISHED event
                    yield encoder.encode(
                        RunFinishedEvent(
                            thread_id=input_data.thread_id,
                            run_id=input_data.run_id,
                        )
                    )

                except Exception as e:
                    logger.error(
                        "AG-UI: Run failed",
                        thread_id=input_data.thread_id,
                        run_id=input_data.run_id,
                        error=str(e),
                    )

                    # Emit RUN_ERROR event
                    yield encoder.encode(
                        RunErrorEvent(
                            thread_id=input_data.thread_id,
                            run_id=input_data.run_id,
                            message=str(e),
                            error=e.__class__.__name__,
                        )
                    )

            return StreamingResponse(
                event_generator(),
                media_type=encoder.get_content_type(),
            )

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            metadata = self.agent.get_metadata()
            return {
                "status": "healthy",
                "version": "1.0.0",
                "agent": metadata.get("name"),
            }

        @self.app.get("/tools")
        async def list_tools():
            """List available tools in AG-UI format."""
            tools = self.convert_tools()
            return [tool.model_dump() for tool in tools]

    async def _process_run(self, input_data: RunAgentInput):
        """Process a chat run using unified agent and yield AG-UI events.

        Args:
            input_data: Run input data

        Yields:
            AG-UI events
        """
        # Extract last user message
        user_messages = [msg for msg in input_data.messages if msg.role == MessageRole.USER]
        if not user_messages:
            logger.warning("AG-UI: No user messages found")
            return

        last_message = user_messages[-1]
        if not last_message.content:
            logger.warning("AG-UI: Empty message content")
            return

        user_text = last_message.content
        logger.info("AG-UI: Processing message via agent", text_preview=user_text[:100] if len(user_text) > 100 else user_text)

        message_id = str(uuid.uuid4())

        try:
            # Execute through unified agent
            async for event in self.agent.execute(
                input=user_text,
                thread_id=input_data.thread_id,
            ):
                event_type = event.get("type")

                if event_type == "tool_call":
                    # Convert to AG-UI ToolCallChunkEvent
                    tool_call_id = str(uuid.uuid4())
                    yield ToolCallChunkEvent(
                        tool_call_id=tool_call_id,
                        tool_call_name=event.get("tool", "unknown"),
                        parent_message_id=message_id,
                        delta=json.dumps(event.get("args", {})),
                        thread_id=input_data.thread_id,
                        run_id=input_data.run_id,
                    )

                elif event_type == "message":
                    # Convert to AG-UI TextMessageChunkEvent
                    content = event.get("content", "")
                    if isinstance(content, str):
                        # Stream in chunks for better UX
                        chunk_size = 30
                        for i in range(0, len(content), chunk_size):
                            chunk = content[i:i + chunk_size]
                            yield TextMessageChunkEvent(
                                message_id=message_id,
                                delta=chunk,
                                thread_id=input_data.thread_id,
                                run_id=input_data.run_id,
                            )
                            await asyncio.sleep(0.02)
                    else:
                        # Handle non-string content
                        content_str = json.dumps(content, ensure_ascii=False)
                        yield TextMessageChunkEvent(
                            message_id=message_id,
                            delta=content_str,
                            thread_id=input_data.thread_id,
                            run_id=input_data.run_id,
                        )

                elif event_type == "ui_component":
                    # Handle generative UI components
                    component = event.get("component", {})
                    yield TextMessageChunkEvent(
                        message_id=message_id,
                        delta=f"\n[UI Component: {component.get('type', 'unknown')}]\n",
                        thread_id=input_data.thread_id,
                        run_id=input_data.run_id,
                    )

                elif event_type == "error":
                    # Handle errors
                    error_msg = event.get("error", "Unknown error")
                    yield TextMessageChunkEvent(
                        message_id=message_id,
                        delta=f"\n\nError: {error_msg}",
                        thread_id=input_data.thread_id,
                        run_id=input_data.run_id,
                    )

        except Exception as e:
            logger.error("AG-UI: Agent execution failed", error=str(e))
            yield TextMessageChunkEvent(
                message_id=message_id,
                delta=f"\n\nError: {str(e)}",
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            )

    async def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run AG-UI server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        import uvicorn

        logger.info("Starting AG-UI server", host=host, port=port, path=self.path)

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
            logger.error("AG-UI server error", error=str(e))
            raise
