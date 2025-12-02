#!/usr/bin/env python
"""{{PROJECT_TITLE}} - Odin Agent

Usage:
    python main.py                        # Default: CopilotKit on port 8000
    python main.py --protocol agui        # AG-UI protocol
    python main.py --protocol a2a         # A2A protocol
    python main.py --port 8001            # Custom port

API Documentation:
    http://localhost:8000/docs            # Swagger UI
    http://localhost:8000/redoc           # ReDoc
"""

import argparse
import asyncio
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from odin import Odin
from odin.logging import get_logger
from odin.protocols.copilotkit import CopilotKitAdapter
from pydantic import BaseModel

logger = get_logger(__name__)


# Request/Response models for API docs
class ToolCallRequest(BaseModel):
    """Request body for tool execution."""

    name: str
    params: dict[str, Any] = {}


class ToolCallResponse(BaseModel):
    """Response from tool execution."""

    success: bool
    result: Any = None
    error: str | None = None


class ToolInfo(BaseModel):
    """Tool information."""

    name: str
    description: str
    parameters: dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    tools: int
    tool_names: list[str]


# Global Odin instance for API routes
_odin_app: Odin | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Server starting")
    yield
    logger.info("Server stopping")


async def create_app(odin_app: Odin) -> FastAPI:
    """Create FastAPI application with CopilotKit and REST API."""
    global _odin_app
    _odin_app = odin_app

    app = FastAPI(
        title="{{PROJECT_TITLE}}",
        description="""
## AI Agent powered by Odin Framework

This API provides access to the agent's tools and capabilities.

### Endpoints

- `/health` - Health check and tool list
- `/tools` - List all available tools with their schemas
- `/tools/{name}` - Execute a specific tool
- `/copilotkit` - CopilotKit AG-UI protocol endpoint

### Usage

1. Check available tools: `GET /tools`
2. Execute a tool: `POST /tools/{tool_name}` with JSON body `{"params": {...}}`
3. Use with CopilotKit frontend via `/copilotkit` endpoint
        """,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount CopilotKit endpoint
    adapter = CopilotKitAdapter(odin_app)
    adapter.mount(app, "/copilotkit")

    # Health check
    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health():
        """Health check endpoint.

        Returns the server status and list of available tools.
        """
        tools = odin_app.list_tools()
        return {
            "status": "healthy",
            "tools": len(tools),
            "tool_names": [t["name"] for t in tools],
        }

    # List tools
    @app.get("/tools", response_model=list[ToolInfo], tags=["Tools"])
    async def list_tools():
        """List all available tools.

        Returns detailed information about each tool including:
        - Name and description
        - Parameter schema (JSON Schema format)
        """
        return odin_app.list_tools()

    # Get tool info
    @app.get("/tools/{name}", response_model=ToolInfo, tags=["Tools"])
    async def get_tool(name: str):
        """Get information about a specific tool.

        Args:
            name: The tool name
        """
        tools = odin_app.list_tools()
        for tool in tools:
            if tool["name"] == name:
                return tool
        return {"error": f"Tool '{name}' not found"}

    # Execute tool
    @app.post("/tools/{name}", response_model=ToolCallResponse, tags=["Tools"])
    async def execute_tool(name: str, request: ToolCallRequest | None = None):
        """Execute a tool with the given parameters.

        Args:
            name: The tool name
            request: Optional request body with parameters

        Returns:
            Tool execution result or error message
        """
        params = request.params if request else {}
        try:
            result = await odin_app.execute_tool(name, **params)
            return {"success": True, "result": result}
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception(f"Tool execution error: {e}")
            return {"success": False, "error": str(e)}

    return app


async def main():
    parser = argparse.ArgumentParser(description="{{PROJECT_TITLE}}")
    parser.add_argument(
        "--protocol",
        choices=["agui", "a2a", "copilotkit"],
        default="copilotkit",
        help="Protocol to use (default: copilotkit)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")

    args = parser.parse_args()

    # Initialize Odin (tools are auto-discovered from ./tools directory)
    from pathlib import Path

    from odin.config import Settings

    settings = Settings(
        plugin_dirs=[Path("tools")],
        plugin_auto_discovery=True,
    )
    odin_app = Odin(settings=settings)
    await odin_app.initialize()

    logger.info(
        "Odin initialized",
        tools=len(odin_app.list_tools()),
        protocol=args.protocol,
    )

    # Log available tools
    for tool in odin_app.list_tools():
        logger.info("Tool registered", name=tool["name"])

    # Log API docs URL
    logger.info(f"API docs available at http://{args.host}:{args.port}/docs")

    # Start server
    if args.protocol == "copilotkit":
        app = await create_app(odin_app)
        config = uvicorn.Config(app, host=args.host, port=args.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    elif args.protocol == "agui":
        from odin.protocols.agui import AGUIServer

        server = AGUIServer(odin_app, path="/")
        await server.run(host=args.host, port=args.port)
    elif args.protocol == "a2a":
        from odin.protocols.a2a import A2AServer

        server = A2AServer(odin_app)
        await server.run(host=args.host, port=args.port)


if __name__ == "__main__":
    asyncio.run(main())
