"""Complete End-to-End Agent Example.

This example demonstrates a production-ready agent that:
1. Exposes tools via multiple protocols (MCP, A2A, AG-UI)
2. Includes comprehensive observability (logs, traces, metrics)
3. Uses proper structured logging (no print statements)
4. Demonstrates real business logic (weather + calendar management)
5. Can be integrated with generative UI systems like AG-UI

To run:
```bash
# Run AG-UI server (default)
PYTHONPATH=src uv run python examples/end_to_end_agent.py --protocol agui

# Run A2A server
PYTHONPATH=src uv run python examples/end_to_end_agent.py --protocol a2a

# Run MCP server (for Claude Desktop)
PYTHONPATH=src uv run python examples/end_to_end_agent.py --protocol mcp
```

To test AG-UI endpoint:
```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "thread_id": "thread-123",
    "run_id": "run-456",
    "messages": [
      {
        "role": "user",
        "content": "Check the weather in San Francisco"
      }
    ]
  }'
```
"""

import argparse
import asyncio
from datetime import datetime, timedelta
from typing import Literal

from odin import Odin, tool
from odin.logging import get_logger
from odin.plugins import AgentPlugin

logger = get_logger(__name__)


class WeatherPlugin(AgentPlugin):
    """Weather information and forecasting plugin.

    Provides tools for checking current weather and forecasts.
    """

    @property
    def name(self) -> str:
        return "weather"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Weather information and forecasting services"

    @tool(name="get_current_weather", description="Get current weather for a location")
    async def get_current_weather(
        self,
        location: str,
        units: Literal["celsius", "fahrenheit"] = "celsius",
    ) -> dict:
        """Get current weather conditions.

        Args:
            location: City name or coordinates (e.g., "San Francisco" or "37.7749,-122.4194")
            units: Temperature units (celsius or fahrenheit)

        Returns:
            Current weather data including temperature, conditions, and humidity
        """
        logger.info("Fetching current weather", location=location, units=units)

        # Simulated weather data (in production, call actual API)
        weather_data = {
            "location": location,
            "temperature": 22 if units == "celsius" else 72,
            "units": units,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind_speed": 15,
            "wind_direction": "NW",
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            "Weather fetched successfully",
            location=location,
            temp=weather_data["temperature"],
            condition=weather_data["condition"],
        )

        return weather_data

    @tool(name="get_forecast", description="Get weather forecast for upcoming days")
    async def get_forecast(
        self,
        location: str,
        days: int = 3,
        units: Literal["celsius", "fahrenheit"] = "celsius",
    ) -> dict:
        """Get weather forecast for the next N days.

        Args:
            location: City name or coordinates
            days: Number of days to forecast (1-7)
            units: Temperature units

        Returns:
            Forecast data for the requested number of days
        """
        logger.info("Fetching weather forecast", location=location, days=days)

        if days < 1 or days > 7:
            logger.warning("Invalid forecast days", days=days)
            days = min(max(days, 1), 7)

        # Generate forecast
        forecast = []
        base_date = datetime.utcnow().date()

        for i in range(days):
            date = base_date + timedelta(days=i)
            forecast.append(
                {
                    "date": date.isoformat(),
                    "high": 25 if units == "celsius" else 77,
                    "low": 15 if units == "celsius" else 59,
                    "condition": ["Sunny", "Cloudy", "Rainy"][i % 3],
                    "precipitation": [10, 30, 70][i % 3],
                }
            )

        logger.info("Forecast generated", location=location, days=len(forecast))

        return {
            "location": location,
            "units": units,
            "forecast": forecast,
        }

    async def get_tools(self):
        """Auto-discover tools from decorated methods."""
        from odin.decorators.tool import get_tool_from_function, is_tool

        tools = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def:
                    tools.append(tool_def)
        return tools

    async def execute_tool(self, tool_name: str, **kwargs):
        """Execute a tool by name."""
        from odin.decorators.tool import get_tool_from_function, is_tool

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def and tool_def.name == tool_name:
                    return await attr(**kwargs)

        raise ValueError(f"Tool '{tool_name}' not found")


class CalendarPlugin(AgentPlugin):
    """Calendar and scheduling plugin.

    Provides tools for managing events and checking availability.
    """

    def __init__(self):
        super().__init__()
        # In-memory event storage (in production, use database)
        self._events: list[dict] = []

    @property
    def name(self) -> str:
        return "calendar"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Calendar and scheduling management"

    @tool(name="create_event", description="Create a new calendar event")
    async def create_event(
        self,
        title: str,
        start_time: str,
        duration_minutes: int = 60,
        description: str = "",
    ) -> dict:
        """Create a calendar event.

        Args:
            title: Event title
            start_time: Start time in ISO format (e.g., "2025-01-27T14:00:00")
            duration_minutes: Event duration in minutes
            description: Optional event description

        Returns:
            Created event details
        """
        logger.info(
            "Creating calendar event",
            title=title,
            start_time=start_time,
            duration=duration_minutes,
        )

        event = {
            "id": len(self._events) + 1,
            "title": title,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
        }

        self._events.append(event)

        logger.info("Event created successfully", event_id=event["id"], title=title)

        return event

    @tool(name="list_events", description="List upcoming calendar events")
    async def list_events(self, limit: int = 10) -> dict:
        """List upcoming calendar events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of upcoming events
        """
        logger.info("Listing calendar events", limit=limit)

        events = self._events[-limit:]

        logger.info("Events retrieved", count=len(events))

        return {
            "count": len(events),
            "events": events,
        }

    async def get_tools(self):
        """Auto-discover tools from decorated methods."""
        from odin.decorators.tool import get_tool_from_function, is_tool

        tools = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def:
                    tools.append(tool_def)
        return tools

    async def execute_tool(self, tool_name: str, **kwargs):
        """Execute a tool by name."""
        from odin.decorators.tool import get_tool_from_function, is_tool

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def and tool_def.name == tool_name:
                    return await attr(**kwargs)

        raise ValueError(f"Tool '{tool_name}' not found")


async def main():
    """Run the end-to-end agent."""
    parser = argparse.ArgumentParser(description="End-to-End Agent Demo")
    parser.add_argument(
        "--protocol",
        choices=["mcp", "a2a", "agui"],
        default="agui",
        help="Protocol to use (default: agui)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Starting End-to-End Agent Demo")
    logger.info("=" * 70)
    logger.info("Protocol selected", protocol=args.protocol)

    # Initialize Odin
    logger.info("Initializing Odin framework")
    app = Odin()
    await app.initialize()

    # Register plugins
    logger.info("Registering plugins")
    weather_plugin = WeatherPlugin()
    calendar_plugin = CalendarPlugin()

    await app.register_plugin(weather_plugin)
    await app.register_plugin(calendar_plugin)

    logger.info(
        "Plugins registered",
        count=len(app.list_plugins()),
        tools=len(app.list_tools()),
    )

    # Log registered tools
    for tool in app.list_tools():
        logger.info(
            "Tool available",
            name=tool["name"],
            plugin=tool.get("plugin", "unknown"),
            description=tool["description"][:50] + "...",
        )

    # Start appropriate server
    if args.protocol == "mcp":
        logger.info("Starting MCP server (stdio)")
        from odin.protocols.mcp import MCPServer

        mcp_server = MCPServer(app, name="end-to-end-agent")
        logger.info(
            "MCP server ready for Claude Desktop",
            tools=len(app.list_tools()),
        )
        await mcp_server.run()

    elif args.protocol == "a2a":
        logger.info("Starting A2A server", host=args.host, port=args.port)
        from odin.protocols.a2a import A2AServer

        a2a_server = A2AServer(
            app,
            name="end-to-end-agent",
            description="Production-ready agent with weather and calendar capabilities",
        )

        logger.info(
            "A2A server starting",
            endpoint=f"http://{args.host}:{args.port}",
            agent_card=f"http://{args.host}:{args.port}/.well-known/agent-card",
        )

        await a2a_server.run(host=args.host, port=args.port)

    elif args.protocol == "agui":
        logger.info("Starting AG-UI server", host=args.host, port=args.port)
        from odin.protocols.agui import AGUIServer

        agui_server = AGUIServer(app, path="/")

        logger.info(
            "AG-UI server starting",
            endpoint=f"http://{args.host}:{args.port}/",
            health_check=f"http://{args.host}:{args.port}/health",
        )

        logger.info("AG-UI features enabled")
        logger.info("- Real-time streaming (SSE)")
        logger.info("- Tool execution")
        logger.info("- Generative UI compatible")

        await agui_server.run(host=args.host, port=args.port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        raise
