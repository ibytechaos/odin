# Odin Demo

A complete end-to-end example demonstrating Odin framework with a React frontend using CopilotKit.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Browser (localhost:3000)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Next.js + CopilotKit                     │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │               <CopilotChat />                       │  │  │
│  │  │  - Renders chat UI                                  │  │  │
│  │  │  - Streams responses in real-time                   │  │  │
│  │  │  - Displays tool execution results                  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTP POST + SSE (AG-UI Protocol)
                                │ /copilotkit
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (localhost:8000)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              FastAPI + CopilotKit SDK + Odin              │  │
│  │                                                           │  │
│  │  CopilotKitAdapter                                        │  │
│  │    └── Converts Odin tools → CopilotKit actions          │  │
│  │                                                           │  │
│  │  Odin Plugins                                             │  │
│  │    ├── WeatherPlugin                                      │  │
│  │    │     ├── get_weather(location, unit)                 │  │
│  │    │     └── get_forecast(location, days)                │  │
│  │    └── CalendarPlugin                                     │  │
│  │          ├── create_event(title, date, time)             │  │
│  │          ├── list_events(limit)                          │  │
│  │          └── delete_event(event_id)                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Option 1: Using start.sh (Recommended)

```bash
cd examples/demo

# Copy and configure environment
cp .env.example .env

# Install frontend dependencies
cd frontend && npm install && cd ..

# Start both backend and frontend
./start.sh

# Or start individually:
./start.sh backend   # Backend only
./start.sh frontend  # Frontend only
```

### Option 2: Using Supervisor

```bash
cd examples/demo

# Set environment variables
export HOST=0.0.0.0 BACKEND_PORT=8000 FRONTEND_PORT=3000 PROTOCOL=copilotkit

# Start with supervisor
supervisord -c supervisord.conf

# Control services
supervisorctl -c supervisord.conf status
supervisorctl -c supervisord.conf restart backend
supervisorctl -c supervisord.conf stop all
```

### Option 3: Manual Start

```bash
# Terminal 1: Backend
cd examples/demo
PYTHONPATH=../../src python main.py

# Terminal 2: Frontend
cd examples/demo/frontend
npm install && npm run dev
```

### Access the Application

- **Frontend**: <http://localhost:3000>
- **Backend**: <http://localhost:8000>
- **Health Check**: <http://localhost:8000/health>

## What You Can Ask

### Weather Queries
- "What's the weather in Tokyo?"
- "Show me the weather in San Francisco in fahrenheit"
- "Get the 5-day forecast for London"
- "Is it rainy in Paris?"

### Calendar Management
- "Create a meeting called 'Team Standup' for tomorrow at 9am"
- "Schedule a doctor appointment for next Monday at 2pm"
- "List my upcoming events"
- "Delete event 1"

### Data & Analytics

- "Show me the sales report"
- "Get user analytics"
- "Compare iPhone vs Samsung"
- "Show the gaming leaderboard"

## Project Structure

```
demo/
├── .env.example             # Environment configuration
├── start.sh                 # Startup script
├── supervisord.conf         # Supervisor configuration (optional)
├── main.py                  # Backend entry point
├── plugins/
│   ├── __init__.py
│   ├── weather.py          # Weather plugin with @tool decorator
│   ├── calendar.py         # Calendar plugin with @tool decorator
│   └── data.py             # Data analysis plugin (tables, charts)
├── frontend/
│   ├── package.json
│   ├── src/
│   │   └── app/
│   │       ├── layout.tsx  # Next.js layout
│   │       ├── page.tsx    # Main chat page
│   │       └── globals.css
│   └── ...
└── README.md
```

## Protocol Options

The backend supports multiple protocols:

```bash
# CopilotKit (default) - for React/CopilotKit frontends
python main.py --protocol copilotkit

# AG-UI - raw AG-UI protocol
python main.py --protocol agui

# A2A - for agent-to-agent communication
python main.py --protocol a2a
```

## Configuration

### Backend Port

```bash
python main.py --port 8001
```

### Frontend Backend URL

Create `.env.local` in the frontend directory:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8001/copilotkit
```

## Adding New Tools

### 1. Create a Plugin

```python
# plugins/my_plugin.py
from odin import DecoratorPlugin, tool

class MyPlugin(DecoratorPlugin):
    @property
    def name(self) -> str:
        return "my_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    @tool(description="Do something cool")
    async def my_tool(self, param1: str, param2: int = 10) -> dict:
        """Do something cool with the given parameters.

        Args:
            param1: The main parameter
            param2: Optional count (default 10)
        """
        return {"result": f"Did something with {param1}"}
```

### 2. Register in main.py

```python
from plugins.my_plugin import MyPlugin

# In main():
await odin_app.register_plugin(MyPlugin())
```

### 3. Restart Backend

The new tool will automatically be available in the chat!

## Troubleshooting

### CORS Error

If you see CORS errors in the browser console, make sure:
1. The backend is running
2. The backend URL is correct in the frontend

### Connection Refused

```bash
# Check if backend is running
curl http://localhost:8000/health
```

### Tools Not Showing

Check the backend logs for registered tools:
```
INFO: Tool registered name=get_weather description=Get current weather for a location
INFO: Tool registered name=get_forecast description=Get weather forecast for multiple days
...
```

### CopilotKit SDK Not Found

```bash
pip install copilotkit
```

## Development Tips

### Hot Reload

- Frontend: Changes auto-reload with Next.js
- Backend: Restart manually or use `--reload` with uvicorn

### Debug Mode

Set log level to debug:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Tools Directly

```bash
curl -X POST http://localhost:8000/copilotkit \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "weather in tokyo"}]}'
```

## Next Steps

- Add authentication
- Deploy to production
- Add more plugins
- Customize the UI
- Integrate with real APIs (weather service, calendar service)
