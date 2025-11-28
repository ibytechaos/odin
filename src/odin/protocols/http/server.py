"""HTTP/REST Server implementation for Odin framework."""

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from odin.core.odin import Odin
from odin.logging import get_logger

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


class ToolInfo(BaseModel):
    """Model for tool information."""

    name: str
    description: str
    parameters: list[dict[str, Any]]


class HTTPServer:
    """HTTP/REST Protocol Server.

    Provides simple REST endpoints for:
    - Listing available tools
    - Executing tools by name
    - Health checks

    Example:
        ```python
        from odin import Odin
        from odin.protocols.http import HTTPServer

        app = Odin()
        await app.initialize()

        # Create HTTP server
        http_server = HTTPServer(app)
        await http_server.run(host="0.0.0.0", port=8000)
        ```
    """

    def __init__(self, odin_app: Odin, name: str = "Odin HTTP API"):
        """Initialize HTTP server.

        Args:
            odin_app: Odin framework instance
            name: API name
        """
        self.odin_app = odin_app

        # Create FastAPI app
        self.app = FastAPI(
            title=name,
            description="HTTP/REST API for Odin agent tools",
            version="1.0.0",
        )

        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes for HTTP/REST API."""

        @self.app.get("/")
        async def root():
            """Root endpoint with API information."""
            return {
                "name": "Odin HTTP API",
                "version": "1.0.0",
                "endpoints": {
                    "tools": "/tools",
                    "execute": "/execute",
                    "health": "/health",
                },
            }

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            tool_count = len(self.odin_app.list_tools())
            plugin_count = len(self.odin_app.list_plugins())

            return {
                "status": "healthy",
                "tools": tool_count,
                "plugins": plugin_count,
            }

        @self.app.get("/tools", response_model=list[ToolInfo])
        async def list_tools():
            """List all available tools."""
            logger.info("HTTP: Listing tools")

            tools = self.odin_app.list_tools()
            return [
                ToolInfo(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=tool["parameters"],
                )
                for tool in tools
            ]

        @self.app.get("/tools/{tool_name}", response_model=ToolInfo)
        async def get_tool(tool_name: str):
            """Get information about a specific tool."""
            logger.info("HTTP: Getting tool info", tool=tool_name)

            tools = self.odin_app.list_tools()
            tool = next((t for t in tools if t["name"] == tool_name), None)

            if not tool:
                raise HTTPException(
                    status_code=404, detail=f"Tool '{tool_name}' not found"
                )

            return ToolInfo(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
            )

        @self.app.post("/execute", response_model=ToolExecutionResponse)
        async def execute_tool(request: ToolExecutionRequest):
            """Execute a tool by name.

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
            tools = self.odin_app.list_tools()
            if not any(t["name"] == request.tool_name for t in tools):
                logger.warning("HTTP: Tool not found", tool=request.tool_name)
                raise HTTPException(
                    status_code=404, detail=f"Tool '{request.tool_name}' not found"
                )

            # Execute tool
            try:
                result = await self.odin_app.execute_tool(
                    request.tool_name, **request.parameters
                )

                logger.info("HTTP: Tool executed successfully", tool=request.tool_name)
                return ToolExecutionResponse(success=True, result=result, error=None)

            except TypeError as e:
                # Parameter type error
                logger.error(
                    "HTTP: Invalid parameters",
                    tool=request.tool_name,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid parameters for tool '{request.tool_name}': {str(e)}",
                )

            except Exception as e:
                # Tool execution error
                logger.error(
                    "HTTP: Tool execution failed",
                    tool=request.tool_name,
                    error=str(e),
                )
                return ToolExecutionResponse(
                    success=False, result=None, error=str(e)
                )

        @self.app.post("/execute/{tool_name}", response_model=ToolExecutionResponse)
        async def execute_tool_by_path(tool_name: str, parameters: dict[str, Any] = {}):
            """Execute a tool by path parameter.

            Alternative endpoint that takes tool name in URL path.
            """
            request = ToolExecutionRequest(tool_name=tool_name, parameters=parameters)
            return await execute_tool(request)

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
