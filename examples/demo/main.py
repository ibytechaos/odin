#!/usr/bin/env python
"""Odin Demo Agent - Complete example with multiple protocols.

This demo showcases:
- Weather, Calendar, and Data plugins
- Multiple protocol support (AG-UI, A2A, CopilotKit)
- Auto-discovery of plugins from ./plugins directory

Usage:
    python main.py                        # Default: CopilotKit on port 8000
    python main.py --protocol agui        # AG-UI protocol
    python main.py --protocol a2a         # A2A protocol
    python main.py --port 8001            # Custom port
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from odin import Odin
from odin.logging import get_logger

logger = get_logger(__name__)


async def run_agui_server(odin_app: Odin, host: str, port: int):
    """Run AG-UI protocol server."""
    from odin.protocols.agui import AGUIServer

    logger.info("Starting AG-UI server", host=host, port=port)
    server = AGUIServer(odin_app, path="/")
    await server.run(host=host, port=port)


async def run_a2a_server(odin_app: Odin, host: str, port: int):
    """Run A2A protocol server."""
    from odin.protocols.a2a import A2AServer

    logger.info("Starting A2A server", host=host, port=port)
    server = A2AServer(odin_app)
    await server.run(host=host, port=port)


async def run_copilotkit_server(odin_app: Odin, host: str, port: int):
    """Run CopilotKit (AG-UI compatible) server."""
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn

    from odin.protocols.copilotkit import CopilotKitAdapter

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("CopilotKit server starting")
        yield
        logger.info("CopilotKit server stopping")

    app = FastAPI(
        title="Odin Demo Agent",
        description="Weather, Calendar, and Data agent with CopilotKit integration",
        lifespan=lifespan,
    )

    # CORS for frontend
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
        return {"status": "healthy", "tools": len(odin_app.list_tools())}

    logger.info("Starting CopilotKit server", host=host, port=port)
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    parser = argparse.ArgumentParser(description="Odin Demo Agent")
    parser.add_argument(
        "--protocol",
        choices=["agui", "a2a", "copilotkit"],
        default="copilotkit",
        help="Protocol to use (default: copilotkit)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind (default: 8000)",
    )

    args = parser.parse_args()

    # Initialize Odin (plugins are auto-discovered from ./plugins directory)
    odin_app = Odin()
    await odin_app.initialize()

    logger.info(
        "Odin initialized",
        tools=len(odin_app.list_tools()),
        protocol=args.protocol,
    )

    # Print available tools
    for tool in odin_app.list_tools():
        logger.info("Tool registered", name=tool["name"], description=tool.get("description", ""))

    # Start server based on protocol
    if args.protocol == "agui":
        await run_agui_server(odin_app, args.host, args.port)
    elif args.protocol == "a2a":
        await run_a2a_server(odin_app, args.host, args.port)
    elif args.protocol == "copilotkit":
        await run_copilotkit_server(odin_app, args.host, args.port)


if __name__ == "__main__":
    asyncio.run(main())
