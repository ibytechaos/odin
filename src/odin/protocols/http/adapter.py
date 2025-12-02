"""HTTP/REST Protocol Adapter for Odin framework.

This adapter implements the IProtocolAdapter interface for HTTP/REST protocol,
enabling protocol-agnostic development.
"""


from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from odin.logging import get_logger
from odin.protocols.base_adapter import IProtocolAdapter

if TYPE_CHECKING:
    from odin.core.agent_interface import IAgent

logger = get_logger(__name__)


class ToolExecutionRequest(BaseModel):
    """Request model for tool execution."""

    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )


class ToolExecutionResponse(BaseModel):
    """Response model for tool execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    result: Any = Field(None, description="Tool execution result")
    error: str | None = Field(None, description="Error message if failed")


class AgentExecuteRequest(BaseModel):
    """Request model for agent execution."""

    input: str = Field(..., description="User input text")
    thread_id: str = Field(default="default", description="Thread ID for persistence")


class AgentExecuteResponse(BaseModel):
    """Response model for agent execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    events: list[dict] = Field(default_factory=list, description="Agent events")
    error: str | None = Field(None, description="Error message if failed")


class ToolInfo(BaseModel):
    """Model for tool information."""

    name: str
    description: str
    parameters: list[dict[str, Any]]


class HTTPAdapter(IProtocolAdapter):
    """HTTP/REST Protocol Adapter.

    Implements IProtocolAdapter interface for HTTP/REST protocol.
    Provides RESTful endpoints for:
    - Agent execution
    - Tool listing and execution
    - Health checks

    Example:
        ```python
        from odin.core.agent_factory import AgentFactory
        from odin.protocols.http import HTTPAdapter

        # Create agent
        agent = AgentFactory.create_agent()

        # Create HTTP adapter
        adapter = HTTPAdapter(agent)

        # Get FastAPI app
        app = adapter.get_app()

        # Run with uvicorn
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
        ```
    """

    def __init__(self, agent: IAgent, name: str = "Odin HTTP API"):
        """Initialize HTTP adapter.

        Args:
            agent: Unified agent instance
            name: API name
        """
        super().__init__(agent)
        self._name = name

        # Create FastAPI app
        self.app = FastAPI(
            title=name,
            description="HTTP/REST API for Odin agent",
            version="1.0.0",
        )

        self._setup_routes()

    def convert_tools(self) -> list[dict]:
        """Convert Odin tools to HTTP-friendly format.

        Returns:
            List of tool definitions as dictionaries
        """
        metadata = self.agent.get_metadata()
        tools = metadata.get("tools", [])

        # Return tool info in JSON-serializable format
        result = []
        for tool_name in tools:
            result.append({
                "name": tool_name,
                "description": "",  # TODO: Get from agent
                "parameters": [],
            })
        return result

    async def handle_request(self, request: Request) -> Response:
        """Handle HTTP request.

        This method is used when the adapter is integrated with ProtocolDispatcher.
        For standalone usage, use get_app() and mount it directly.

        Args:
            request: FastAPI Request object

        Returns:
            FastAPI Response object
        """
        # Delegate to FastAPI app
        # This is primarily for ProtocolDispatcher integration
        from starlette.routing import Match

        for route in self.app.routes:
            match, _scope = route.matches({"type": "http", "path": request.url.path, "method": request.method})
            if match == Match.FULL:
                # Found matching route, let FastAPI handle it
                response = await route.handle(request.scope, request.receive, request._send)
                return response

        raise HTTPException(status_code=404, detail="Not found")

    def get_app(self) -> FastAPI:
        """Get FastAPI application.

        Use this when mounting the HTTP adapter standalone.

        Returns:
            FastAPI application instance
        """
        return self.app

    def _setup_routes(self):
        """Setup FastAPI routes for HTTP/REST API."""

        @self.app.get("/")
        async def root():
            """Root endpoint with API information."""
            metadata = self.agent.get_metadata()
            return {
                "name": self._name,
                "version": "1.0.0",
                "agent": {
                    "name": metadata.get("name"),
                    "description": metadata.get("description"),
                    "type": metadata.get("type"),
                },
                "endpoints": {
                    "agent": "/agent/execute",
                    "tools": "/tools",
                    "execute": "/execute",
                    "health": "/health",
                },
            }

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            metadata = self.agent.get_metadata()
            return {
                "status": "healthy",
                "agent": metadata.get("name"),
                "type": metadata.get("type"),
                "tools": len(metadata.get("tools", [])),
            }

        @self.app.get("/tools", response_model=list[ToolInfo])
        async def list_tools():
            """List all available tools."""
            logger.info("HTTP: Listing tools")
            return self.convert_tools()

        @self.app.get("/tools/{tool_name}", response_model=ToolInfo)
        async def get_tool(tool_name: str):
            """Get information about a specific tool."""
            logger.info("HTTP: Getting tool info", tool=tool_name)

            tools = self.convert_tools()
            tool = next((t for t in tools if t["name"] == tool_name), None)

            if not tool:
                raise HTTPException(
                    status_code=404, detail=f"Tool '{tool_name}' not found"
                )

            return ToolInfo(
                name=tool["name"],
                description=tool.get("description", ""),
                parameters=tool.get("parameters", []),
            )

        @self.app.post("/agent/execute", response_model=AgentExecuteResponse)
        async def execute_agent(request: AgentExecuteRequest):
            """Execute agent with user input.

            This is the primary endpoint for interacting with the agent.
            It executes the agent and returns all events.

            Request body:
            ```json
            {
                "input": "What is the weather in Beijing?",
                "thread_id": "session-123"
            }
            ```

            Response:
            ```json
            {
                "success": true,
                "events": [
                    {"type": "tool_call", "tool": "get_weather", "args": {"location": "Beijing"}},
                    {"type": "message", "content": "The weather in Beijing is sunny, 22°C."}
                ],
                "error": null
            }
            ```
            """
            logger.info(
                "HTTP: Executing agent",
                input=request.input[:50] + "..." if len(request.input) > 50 else request.input,
                thread_id=request.thread_id,
            )

            try:
                events = []
                async for event in self.agent.execute(
                    input=request.input,
                    thread_id=request.thread_id,
                ):
                    events.append(dict(event))

                logger.info("HTTP: Agent executed successfully", event_count=len(events))
                return AgentExecuteResponse(success=True, events=events, error=None)

            except Exception as e:
                logger.error("HTTP: Agent execution failed", error=str(e))
                return AgentExecuteResponse(success=False, events=[], error=str(e))

        @self.app.post("/execute", response_model=ToolExecutionResponse)
        async def execute_tool(request: ToolExecutionRequest):
            """Execute a tool directly by name.

            This bypasses the agent and executes tools directly.
            Useful for testing and simple tool invocations.

            Request body:
            ```json
            {
                "tool_name": "get_weather",
                "parameters": {
                    "location": "Beijing",
                    "unit": "celsius"
                }
            }
            ```

            Response:
            ```json
            {
                "success": true,
                "result": {"temperature": 22, "condition": "sunny"},
                "error": null
            }
            ```
            """
            logger.info(
                "HTTP: Executing tool",
                tool=request.tool_name,
                params=list(request.parameters.keys()),
            )

            # Check if tool exists
            tools = self.convert_tools()
            if not any(t["name"] == request.tool_name for t in tools):
                logger.warning("HTTP: Tool not found", tool=request.tool_name)
                raise HTTPException(
                    status_code=404, detail=f"Tool '{request.tool_name}' not found"
                )

            # Execute through agent (which will use its tool execution)
            try:
                # For direct tool execution, we send a tool call request to the agent
                events = []
                async for event in self.agent.execute(
                    input=f"Execute tool {request.tool_name} with parameters: {request.parameters}",
                    thread_id="direct-tool-execution",
                ):
                    events.append(dict(event))

                # Extract result from events
                result = None
                for event in events:
                    if event.get("type") == "message":
                        result = event.get("content")
                        break

                logger.info("HTTP: Tool executed successfully", tool=request.tool_name)
                return ToolExecutionResponse(success=True, result=result, error=None)

            except Exception as e:
                logger.error(
                    "HTTP: Tool execution failed",
                    tool=request.tool_name,
                    error=str(e),
                )
                return ToolExecutionResponse(success=False, result=None, error=str(e))

        @self.app.post("/execute/{tool_name}", response_model=ToolExecutionResponse)
        async def execute_tool_by_path(tool_name: str, parameters: dict[str, Any] | None = None):
            """Execute a tool by path parameter.

            Alternative endpoint that takes tool name in URL path.
            """
            if parameters is None:
                parameters = {}
            request = ToolExecutionRequest(tool_name=tool_name, parameters=parameters)
            return await execute_tool(request)

        @self.app.get("/agent/state/{thread_id}")
        async def get_agent_state(thread_id: str):
            """Get agent state for a thread.

            Returns the current state of the agent for the specified thread.
            """
            logger.info("HTTP: Getting agent state", thread_id=thread_id)

            state = await self.agent.get_state(thread_id)
            if state is None:
                return {"thread_id": thread_id, "state": None}

            return {"thread_id": thread_id, "state": dict(state)}

    async def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run HTTP server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        import uvicorn

        logger.info("Starting HTTP server", host=host, port=port)

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
            logger.error("HTTP server error", error=str(e))
            raise
