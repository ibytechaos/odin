"""Protocol-Agnostic Agent Example.

This example demonstrates how to create a protocol-agnostic agent
using the new Odin architecture. Business logic is written once and
automatically works with all supported protocols (MCP, A2A, AG-UI,
CopilotKit, HTTP).

Usage:
    # Set environment variables
    export ODIN_AGENT_BACKEND=crewai  # or langgraph
    export OPENAI_API_KEY=your-key

    # Run the example
    python examples/protocol_agnostic_agent.py
"""

import asyncio
import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


async def main():
    """Run protocol-agnostic agent server."""

    # Import Odin components
    from odin.config import get_settings
    from odin.core.agent_factory import AgentFactory
    from odin.plugins.base import Tool

    # Get settings
    settings = get_settings()
    print(f"Using agent backend: {settings.agent_backend}")
    print(f"Agent name: {settings.agent_name}")

    # Create agent using factory
    agent = AgentFactory.create_agent(settings=settings)
    print(f"Agent created: {agent.name}")

    # Define a simple tool
    def get_weather(location: str, unit: str = "celsius") -> dict:
        """Get weather for a location.

        Args:
            location: City name
            unit: Temperature unit (celsius or fahrenheit)

        Returns:
            Weather information
        """
        # Mock weather data
        return {
            "location": location,
            "temperature": 22 if unit == "celsius" else 72,
            "unit": unit,
            "condition": "sunny",
            "humidity": 45,
        }

    # Create tool from function
    weather_tool = Tool(
        name="get_weather",
        description="Get current weather for a location",
        func=get_weather,
        parameters=[
            {"name": "location", "type": "string", "description": "City name", "required": True},
            {"name": "unit", "type": "string", "description": "Temperature unit", "required": False},
        ]
    )

    # Add tool to agent
    agent.add_tool(weather_tool)
    print(f"Added tool: {weather_tool.name}")

    # Create FastAPI app
    app = FastAPI(
        title="Protocol-Agnostic Agent",
        description="Demonstrates protocol-agnostic agent development",
        version="1.0.0",
    )

    # Add CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "agent": agent.name,
            "backend": settings.agent_backend,
        }

    # Mount protocol adapters
    # Each adapter provides protocol-specific endpoints but uses the same agent

    # 1. HTTP/REST API
    from odin.protocols.http.adapter import HTTPAdapter
    http_adapter = HTTPAdapter(agent, name="Weather Agent API")
    app.mount("/api", http_adapter.get_app())
    print("HTTP adapter mounted at /api")

    # 2. AG-UI (Generative UI)
    from odin.protocols.agui.adapter import AGUIAdapter
    agui_adapter = AGUIAdapter(agent, path="/")
    app.mount("/agui", agui_adapter.get_app())
    print("AG-UI adapter mounted at /agui")

    # 3. A2A (Agent-to-Agent)
    from odin.protocols.a2a.adapter import A2AAdapter
    a2a_adapter = A2AAdapter(agent)
    app.mount("/a2a", a2a_adapter.get_app())
    print("A2A adapter mounted at /a2a")

    # 4. CopilotKit (if available)
    try:
        from odin.protocols.copilotkit.adapter_v2 import CopilotKitAdapter
        copilot_adapter = CopilotKitAdapter(agent)
        copilot_adapter.mount(app, "/copilotkit")
        print("CopilotKit adapter mounted at /copilotkit")
    except ImportError as e:
        print(f"CopilotKit not available: {e}")

    print("\n" + "=" * 50)
    print("Protocol-Agnostic Agent Server Starting...")
    print("=" * 50)
    print("\nAvailable endpoints:")
    print("  - Health:     GET  http://localhost:8000/health")
    print("  - HTTP API:   POST http://localhost:8000/api/agent/execute")
    print("  - HTTP Tools: GET  http://localhost:8000/api/tools")
    print("  - AG-UI:      POST http://localhost:8000/agui/")
    print("  - A2A Card:   GET  http://localhost:8000/a2a/.well-known/agent-card")
    print("  - A2A Msg:    POST http://localhost:8000/a2a/message/send")
    print("  - CopilotKit: POST http://localhost:8000/copilotkit")
    print("\nAll endpoints use the same agent backend!")
    print("=" * 50 + "\n")

    # Run server
    import uvicorn
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
