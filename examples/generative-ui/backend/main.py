#!/usr/bin/env python
"""Generative UI Example - Odin Agent with AG-UI Protocol.

This example demonstrates how to build an agent that generates
interactive UI components using CopilotKit's Agentic Generative UI.

Key concepts:
1. Agent state contains `ui_components` list
2. Tools add UI component definitions to state
3. Frontend uses `useCoAgent` to render components dynamically

Usage:
    python main.py
"""

import asyncio
import os
import sys
from typing import Any

# Add odin src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

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
    logger.info("Generative UI Server starting")
    yield
    logger.info("Server stopping")


async def create_app(odin_app: Odin) -> FastAPI:
    """Create FastAPI application with CopilotKit."""
    app = FastAPI(
        title="Generative UI Demo",
        description="Demonstrates Agentic Generative UI with Odin",
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
        tools = odin_app.list_tools()
        return {
            "status": "healthy",
            "tools": len(tools),
            "tool_names": [t["name"] for t in tools],
        }

    # List tools endpoint (for debugging)
    @app.get("/tools")
    async def list_tools():
        return odin_app.list_tools()

    return app


async def main():
    # Initialize Odin with auto-discovery of plugins
    odin_app = Odin()
    await odin_app.initialize()

    # Manually import and register plugins from ./plugins directory
    from plugins.ui_tools import UIToolsPlugin
    from plugins.data_tools import DataToolsPlugin

    await odin_app.register_plugin(UIToolsPlugin())
    await odin_app.register_plugin(DataToolsPlugin())

    logger.info(
        "Odin initialized with generative UI tools",
        tools=[t["name"] for t in odin_app.list_tools()],
    )

    # Create and run app
    app = await create_app(odin_app)

    print("\n" + "=" * 60)
    print("  Generative UI Demo Server")
    print("=" * 60)
    print("\nBackend running at: http://localhost:8000")
    print("CopilotKit endpoint: http://localhost:8000/copilotkit")
    print("\nAvailable tools:")
    for tool in odin_app.list_tools():
        print(f"  - {tool['name']}: {tool['description'][:50]}...")
    print("\nStart the frontend:")
    print("  cd frontend && npm install && npm run dev")
    print("=" * 60 + "\n")

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
