"""AG-UI Server implementation for Odin framework."""

import asyncio
import json
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from odin.core.odin import Odin
from odin.logging import get_logger
from odin.protocols.agui.encoder import EventEncoder
from odin.protocols.agui.models import (
    Message,
    MessageRole,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageChunkEvent,
    Tool,
    ToolCallChunkEvent,
)

logger = get_logger(__name__)


class AGUIServer:
    """AG-UI (Agent-User Interaction Protocol) Server.

    Exposes Odin agent capabilities via the AG-UI protocol for generative UI
    and real-time agent interactions.

    Example:
        ```python
        from odin import Odin
        from odin.protocols.agui import AGUIServer

        app = Odin()
        await app.initialize()

        # Register plugins...

        # Start AG-UI server
        agui_server = AGUIServer(app)
        await agui_server.run(host="0.0.0.0", port=8000)
        ```
    """

    def __init__(self, odin_app: Odin, path: str = "/"):
        """Initialize AG-UI server.

        Args:
            odin_app: Odin framework instance
            path: Endpoint path (default: "/")
        """
        self.odin_app = odin_app
        self.path = path

        # Create FastAPI app
        self.app = FastAPI(
            title="Odin AG-UI Server",
            description="Agent-User Interaction Protocol server",
            version="1.0.0",
        )

        self._setup_routes()

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

                    # Process messages
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
            return {"status": "healthy", "version": "1.0.0"}

    async def _process_run(self, input_data: RunAgentInput):
        """Process a chat run and yield AG-UI events.

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
        logger.info("AG-UI: Processing message", text_preview=user_text[:100])

        # Try to route to appropriate tool
        tools = self.odin_app.list_tools()

        # Simple routing: look for tool names in text
        matched_tool = None
        for tool in tools:
            if tool["name"].lower() in user_text.lower():
                matched_tool = tool
                break

        if matched_tool:
            # Generate tool call event
            tool_call_id = str(uuid.uuid4())
            message_id = str(uuid.uuid4())

            logger.info("AG-UI: Matched tool", tool=matched_tool["name"])

            # Emit tool call chunk with tool name
            yield ToolCallChunkEvent(
                tool_call_id=tool_call_id,
                tool_call_name=matched_tool["name"],
                parent_message_id=message_id,
                delta=json.dumps({"status": "executing"}),
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            )

            # Execute tool (with empty params for demo)
            try:
                result = await self.odin_app.execute_tool(matched_tool["name"])

                # Emit result as text message chunks
                result_text = json.dumps(result, indent=2, ensure_ascii=False)

                # Split into chunks for streaming effect
                chunk_size = 50
                for i in range(0, len(result_text), chunk_size):
                    chunk = result_text[i : i + chunk_size]
                    yield TextMessageChunkEvent(
                        message_id=message_id,
                        delta=chunk,
                        thread_id=input_data.thread_id,
                        run_id=input_data.run_id,
                    )
                    # Small delay for streaming effect
                    await asyncio.sleep(0.05)

            except Exception as e:
                logger.error("AG-UI: Tool execution failed", tool=matched_tool["name"], error=str(e))
                yield TextMessageChunkEvent(
                    message_id=message_id,
                    delta=f"\n\nError executing tool: {str(e)}",
                    thread_id=input_data.thread_id,
                    run_id=input_data.run_id,
                )

        else:
            # No tool matched - return conversational response
            message_id = str(uuid.uuid4())

            response_text = self._generate_conversational_response(user_text, tools)

            # Stream response in chunks
            chunk_size = 30
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i : i + chunk_size]
                yield TextMessageChunkEvent(
                    message_id=message_id,
                    delta=chunk,
                    thread_id=input_data.thread_id,
                    run_id=input_data.run_id,
                )
                await asyncio.sleep(0.05)

    def _generate_conversational_response(self, user_text: str, tools: list[dict]) -> str:
        """Generate a conversational response when no tool matches.

        Args:
            user_text: User's message
            tools: Available tools

        Returns:
            Response text
        """
        tool_names = [t["name"] for t in tools]
        return (
            f"I understand you said: '{user_text[:100]}...'\n\n"
            f"I have access to these tools:\n"
            + "\n".join(f"- {name}" for name in tool_names)
            + "\n\nPlease mention a specific tool name in your message to use it."
        )

    def _convert_odin_tools_to_agui(self) -> list[Tool]:
        """Convert Odin tools to AG-UI Tool format.

        Returns:
            List of AG-UI tools
        """
        agui_tools = []

        for tool in self.odin_app.list_tools():
            # Convert parameters to JSON Schema
            properties = {}
            required = []

            for param in tool.get("parameters", []):
                properties[param["name"]] = {
                    "type": param["type"],
                    "description": param["description"],
                }
                if param.get("required", False):
                    required.append(param["name"])

            parameters = {
                "type": "object",
                "properties": properties,
                "required": required,
            }

            agui_tool = Tool(
                name=tool["name"],
                description=tool["description"],
                parameters=parameters,
            )
            agui_tools.append(agui_tool)

        return agui_tools

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
