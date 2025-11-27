"""CopilotKit Backend Example.

This example demonstrates how to expose Odin tools to a CopilotKit frontend.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  import { CopilotKit } from "@copilotkit/react-core"        ││
│  │  import { CopilotChat } from "@copilotkit/react-ui"         ││
│  │                                                              ││
│  │  <CopilotKit runtimeUrl="http://localhost:8000/copilotkit"> ││
│  │    <CopilotChat />                                           ││
│  │  </CopilotKit>                                               ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP (SSE)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (This File)                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  FastAPI + CopilotKit SDK + Odin Framework                  ││
│  │                                                              ││
│  │  /copilotkit  ←  CopilotKit endpoint (actions)              ││
│  │  /health      ←  Health check                                ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Odin Plugins (Tools)                                        ││
│  │  - WeatherPlugin: get_weather, get_forecast                  ││
│  │  - CalendarPlugin: create_event, list_events                 ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Install dependencies

```bash
# Backend
pip install copilotkit fastapi uvicorn

# Or with uv
uv pip install copilotkit fastapi uvicorn
```

### 2. Run this backend

```bash
PYTHONPATH=src uv run python examples/copilotkit_backend.py
```

### 3. Create React frontend

```bash
npx create-next-app@latest copilotkit-frontend
cd copilotkit-frontend
npm install @copilotkit/react-core @copilotkit/react-ui
```

### 4. Add CopilotKit to your React app

```tsx
// app/page.tsx
"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function Home() {
  return (
    <CopilotKit runtimeUrl="http://localhost:8000/copilotkit">
      <div style={{ height: "100vh" }}>
        <CopilotChat
          labels={{
            title: "Odin Assistant",
            initial: "Hi! I can help you with weather and calendar. Try asking me about the weather or creating an event.",
          }}
        />
      </div>
    </CopilotKit>
  );
}
```

### 5. Run frontend

```bash
npm run dev
# Open http://localhost:3000
```

## What you can ask

- "What's the weather in San Francisco?"
- "Show me the forecast for the next 3 days"
- "Create a meeting for tomorrow at 2pm"
- "List my upcoming events"
"""

import asyncio
from datetime import datetime, timedelta
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from odin import Odin, tool
from odin.logging import get_logger
from odin.plugins import AgentPlugin

logger = get_logger(__name__)


# ============================================================================
# Plugins (Same as end_to_end_agent.py)
# ============================================================================


class WeatherPlugin(AgentPlugin):
    """Weather information plugin."""

    @property
    def name(self) -> str:
        return "weather"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Weather information and forecasting"

    @tool(name="get_weather", description="Get current weather for a location")
    async def get_weather(
        self,
        location: str,
        units: Literal["celsius", "fahrenheit"] = "celsius",
    ) -> dict:
        """Get current weather.

        Args:
            location: City name (e.g., "San Francisco", "Tokyo")
            units: Temperature units
        """
        logger.info("Getting weather", location=location, units=units)

        # Simulated data (replace with real API in production)
        return {
            "location": location,
            "temperature": 22 if units == "celsius" else 72,
            "units": units,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind_speed": 15,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @tool(name="get_forecast", description="Get weather forecast for upcoming days")
    async def get_forecast(
        self,
        location: str,
        days: int = 3,
    ) -> dict:
        """Get weather forecast.

        Args:
            location: City name
            days: Number of days (1-7)
        """
        logger.info("Getting forecast", location=location, days=days)

        days = min(max(days, 1), 7)
        forecast = []
        base_date = datetime.utcnow().date()

        for i in range(days):
            date = base_date + timedelta(days=i)
            forecast.append({
                "date": date.isoformat(),
                "high": 25,
                "low": 15,
                "condition": ["Sunny", "Cloudy", "Rainy"][i % 3],
            })

        return {"location": location, "forecast": forecast}

    async def get_tools(self):
        from odin.decorators.tool import get_tool_from_function, is_tool

        tools = []
        for name in dir(self):
            attr = getattr(self, name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def:
                    tools.append(tool_def)
        return tools

    async def execute_tool(self, tool_name: str, **kwargs):
        from odin.decorators.tool import get_tool_from_function, is_tool

        for name in dir(self):
            attr = getattr(self, name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def and tool_def.name == tool_name:
                    return await attr(**kwargs)
        raise ValueError(f"Tool '{tool_name}' not found")


class CalendarPlugin(AgentPlugin):
    """Calendar management plugin."""

    def __init__(self):
        super().__init__()
        self._events: list[dict] = []

    @property
    def name(self) -> str:
        return "calendar"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Calendar and event management"

    @tool(name="create_event", description="Create a new calendar event")
    async def create_event(
        self,
        title: str,
        start_time: str,
        duration_minutes: int = 60,
    ) -> dict:
        """Create calendar event.

        Args:
            title: Event title
            start_time: Start time (e.g., "2025-01-28T14:00:00")
            duration_minutes: Duration in minutes
        """
        logger.info("Creating event", title=title, start_time=start_time)

        event = {
            "id": len(self._events) + 1,
            "title": title,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._events.append(event)

        return event

    @tool(name="list_events", description="List upcoming calendar events")
    async def list_events(self, limit: int = 10) -> dict:
        """List events.

        Args:
            limit: Maximum events to return
        """
        logger.info("Listing events", limit=limit)

        return {
            "count": len(self._events[-limit:]),
            "events": self._events[-limit:],
        }

    async def get_tools(self):
        from odin.decorators.tool import get_tool_from_function, is_tool

        tools = []
        for name in dir(self):
            attr = getattr(self, name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def:
                    tools.append(tool_def)
        return tools

    async def execute_tool(self, tool_name: str, **kwargs):
        from odin.decorators.tool import get_tool_from_function, is_tool

        for name in dir(self):
            attr = getattr(self, name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def and tool_def.name == tool_name:
                    return await attr(**kwargs)
        raise ValueError(f"Tool '{tool_name}' not found")


# ============================================================================
# FastAPI Application with Lifespan
# ============================================================================

odin_app: Odin | None = None
copilotkit_adapter = None


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global odin_app, copilotkit_adapter

    # Startup
    logger.info("=" * 60)
    logger.info("Starting Odin + CopilotKit Backend")
    logger.info("=" * 60)

    # Initialize Odin
    logger.info("Initializing Odin framework")
    odin_app = Odin()
    await odin_app.initialize()

    # Register plugins
    logger.info("Registering plugins")
    await odin_app.register_plugin(WeatherPlugin())
    await odin_app.register_plugin(CalendarPlugin())

    logger.info(
        "Plugins registered",
        count=len(odin_app.list_plugins()),
        tools=len(odin_app.list_tools()),
    )

    # Mount CopilotKit
    try:
        from odin.protocols.copilotkit import CopilotKitAdapter

        copilotkit_adapter = CopilotKitAdapter(odin_app)
        copilotkit_adapter.mount(app, "/copilotkit")

        logger.info("CopilotKit endpoint mounted at /copilotkit")

    except ImportError as e:
        logger.error(
            "CopilotKit not installed",
            error=str(e),
            hint="Run: pip install copilotkit",
        )
        raise

    logger.info("=" * 60)
    logger.info("Server ready!")
    logger.info("CopilotKit endpoint: http://localhost:8000/copilotkit")
    logger.info("Health check: http://localhost:8000/health")
    logger.info("=" * 60)

    yield  # Application runs here

    # Shutdown
    if odin_app:
        await odin_app.shutdown()
        logger.info("Odin shutdown complete")


app = FastAPI(
    title="Odin + CopilotKit Backend",
    description="Backend server exposing Odin tools to CopilotKit frontend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "framework": "odin"}


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
