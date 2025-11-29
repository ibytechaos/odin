#!/usr/bin/env python
"""{{PROJECT_TITLE}} - Odin Agent

Usage:
    python main.py                        # Default: CopilotKit on port 8000
    python main.py --protocol agui        # AG-UI protocol
    python main.py --protocol a2a         # A2A protocol
    python main.py --port 8001            # Custom port
"""

import argparse
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from odin import Odin
from odin.logging import get_logger
from odin.protocols.copilotkit import CopilotKitAdapter

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Server starting")
    yield
    logger.info("Server stopping")


async def create_app(odin_app: Odin) -> FastAPI:
    """Create FastAPI application with CopilotKit."""
    app = FastAPI(
        title="{{PROJECT_TITLE}}",
        description="AI Agent powered by Odin Framework",
        lifespan=lifespan,
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
    @app.get("/health")
    async def health():
        tools = odin_app.list_tools()
        return {
            "status": "healthy",
            "tools": len(tools),
            "tool_names": [t["name"] for t in tools],
        }

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
    odin_app = Odin(plugin_dirs=["tools"])
    await odin_app.initialize()

    logger.info(
        "Odin initialized",
        tools=len(odin_app.list_tools()),
        protocol=args.protocol,
    )

    # Log available tools
    for tool in odin_app.list_tools():
        logger.info("Tool registered", name=tool["name"])

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
