"""Unified Odin Server - Single port, multiple protocols.

This module provides a unified server that exposes all protocols on a single port
with path-based routing:

    /a2a/*          → A2A protocol (agent-card, message/send, tasks)
    /mcp/*          → MCP Streamable HTTP protocol
    /agui/*         → AG-UI protocol (SSE streaming)
    /copilotkit/*   → CopilotKit protocol
    /api/*          → REST API (tools CRUD)
    /health         → Health check

Example:
    ```python
    from odin import Odin
    from odin.server import UnifiedServer

    odin = Odin()
    await odin.initialize()

    server = UnifiedServer(odin)
    await server.run(host="0.0.0.0", port=8000)
    ```

Docker usage:
    ```bash
    docker run -p 8000:8000 odin-server
    ```
"""

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from odin.logging import get_logger

if TYPE_CHECKING:
    from odin.core.odin import Odin

logger = get_logger(__name__)


class ToolCallRequest(BaseModel):
    """Request model for tool execution."""

    params: dict[str, Any] = {}


class ToolCallResponse(BaseModel):
    """Response model for tool execution."""

    result: dict | list | str | None
    error: str | None = None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    version: str
    protocols: list[str]
    tools_count: int


class UnifiedServer:
    """Unified server exposing all protocols on a single port.

    This server mounts all protocol adapters under different path prefixes,
    allowing a single deployment to serve multiple protocols simultaneously.

    Protocols:
        - A2A: Google's Agent-to-Agent protocol at /a2a
        - MCP: Model Context Protocol (Streamable HTTP) at /mcp
        - AG-UI: Agent-User Interaction protocol at /agui
        - CopilotKit: CopilotKit integration at /copilotkit
        - REST API: Simple HTTP API at /api
    """

    def __init__(
        self,
        odin: Odin,
        *,
        name: str = "Odin Server",
        version: str = "0.1.0",
        cors_origins: list[str] | None = None,
    ):
        """Initialize unified server.

        Args:
            odin: Odin framework instance
            name: Server name
            version: Server version
            cors_origins: CORS allowed origins (default: ["*"])
        """
        self.odin = odin
        self.name = name
        self.version = version
        self.cors_origins = cors_origins or ["*"]
        self.app: FastAPI | None = None
        self._adapters: dict[str, Any] = {}

    def create_app(self) -> FastAPI:
        """Create FastAPI application with all protocols mounted.

        Returns:
            Configured FastAPI application
        """

        @asynccontextmanager
        async def lifespan(app: FastAPI):  # noqa: ARG001
            logger.info("Starting unified server", name=self.name)
            yield
            logger.info("Shutting down unified server")
            await self.odin.shutdown()

        self.app = FastAPI(
            title=self.name,
            description="Unified AI Agent Server - MCP, A2A, AG-UI, CopilotKit",
            version=self.version,
            lifespan=lifespan,
        )

        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Setup all endpoints
        self._setup_health()
        self._setup_rest_api()
        self._setup_a2a()
        self._setup_mcp()
        self._setup_agui()
        self._setup_copilotkit()

        return self.app

    def _setup_health(self) -> None:
        """Setup health check endpoint."""

        @self.app.get("/health", response_model=HealthResponse, tags=["System"])
        async def health() -> dict:
            """Health check endpoint."""
            return {
                "status": "healthy",
                "version": self.version,
                "protocols": list(self._adapters.keys()),
                "tools_count": len(self.odin.list_tools()),
            }

        @self.app.get("/", tags=["System"])
        async def root() -> dict:
            """Root endpoint with server info."""
            return {
                "name": self.name,
                "version": self.version,
                "protocols": {
                    "a2a": "/a2a",
                    "mcp": "/mcp",
                    "agui": "/agui",
                    "copilotkit": "/copilotkit",
                    "rest": "/api",
                },
                "docs": "/docs",
                "health": "/health",
            }

    def _setup_rest_api(self) -> None:
        """Setup REST API endpoints at /api."""

        @self.app.get("/api/tools", tags=["REST API"])
        async def list_tools() -> list[dict]:
            """List all available tools."""
            return self.odin.list_tools()

        @self.app.get("/api/tools/{tool_name}", tags=["REST API"])
        async def get_tool(tool_name: str) -> dict:
            """Get information about a specific tool."""
            tools = self.odin.list_tools()
            for tool in tools:
                if tool["name"] == tool_name:
                    return tool
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

        @self.app.post(
            "/api/tools/{tool_name}",
            response_model=ToolCallResponse,
            tags=["REST API"],
        )
        async def execute_tool(tool_name: str, request: ToolCallRequest) -> dict:
            """Execute a tool by name."""
            try:
                result = await self.odin.execute_tool(tool_name, **request.params)
                return {"result": result, "error": None}
            except Exception as e:
                logger.error("Tool execution failed", tool=tool_name, error=str(e))
                return {"result": None, "error": str(e)}

        self._adapters["rest"] = "mounted"
        logger.info("REST API mounted at /api")

    def _setup_a2a(self) -> None:
        """Setup A2A protocol at /a2a."""
        try:
            from odin.protocols.a2a import A2AServer

            a2a = A2AServer(
                self.odin,
                name=self.name,
                description="A2A protocol endpoint",
            )
            self.app.mount("/a2a", a2a.app)
            self._adapters["a2a"] = a2a
            logger.info("A2A protocol mounted at /a2a")

        except Exception as e:
            logger.warning("Failed to setup A2A protocol", error=str(e))

    def _setup_mcp(self) -> None:
        """Setup MCP Streamable HTTP protocol at /mcp."""
        try:
            from odin.protocols.mcp.streamable_http import MCPStreamableHTTP

            mcp = MCPStreamableHTTP(self.odin, name=self.name)
            self.app.mount("/mcp", mcp.get_app())
            self._adapters["mcp"] = mcp
            logger.info("MCP Streamable HTTP mounted at /mcp")

        except Exception as e:
            logger.warning("Failed to setup MCP protocol", error=str(e))

    def _setup_agui(self) -> None:
        """Setup AG-UI protocol at /agui."""
        try:
            from odin.protocols.agui import AGUIServer

            agui = AGUIServer(self.odin, path="/")
            self.app.mount("/agui", agui.app)
            self._adapters["agui"] = agui
            logger.info("AG-UI protocol mounted at /agui")

        except Exception as e:
            logger.warning("Failed to setup AG-UI protocol", error=str(e))

    def _setup_copilotkit(self) -> None:
        """Setup CopilotKit protocol at /copilotkit."""
        try:
            from odin.protocols.copilotkit import CopilotKitAdapter

            adapter = CopilotKitAdapter(self.odin)
            adapter.mount(self.app, "/copilotkit")
            self._adapters["copilotkit"] = adapter
            logger.info("CopilotKit protocol mounted at /copilotkit")

        except Exception as e:
            logger.warning("Failed to setup CopilotKit protocol", error=str(e))

    async def run(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """Run the unified server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        import uvicorn

        if self.app is None:
            self.create_app()

        logger.info(
            "Starting unified server",
            host=host,
            port=port,
            protocols=list(self._adapters.keys()),
        )

        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()


def create_unified_app(
    plugin_dirs: list[str] | None = None,
    builtin_plugins: list[str] | None = None,
) -> FastAPI:
    """Create a unified FastAPI application.

    This is the entry point for uvicorn/gunicorn:
    ```bash
    uvicorn odin.server:create_unified_app --factory
    ```

    Args:
        plugin_dirs: Plugin directories to load
        builtin_plugins: Builtin plugins to enable

    Returns:
        FastAPI application
    """
    import asyncio

    from odin import Odin
    from odin.config import Settings
    from odin.plugins.builtin import BUILTIN_PLUGINS

    # Default to all builtin plugins
    if builtin_plugins is None:
        builtin_plugins = list(BUILTIN_PLUGINS.keys())

    settings = Settings(
        plugin_dirs=plugin_dirs or [],
        builtin_plugins=builtin_plugins,
    )

    odin = Odin(settings=settings)

    # Initialize synchronously for factory pattern
    asyncio.get_event_loop().run_until_complete(odin.initialize())

    server = UnifiedServer(odin)
    return server.create_app()
