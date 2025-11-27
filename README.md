# Odin

A modern, protocol-agnostic agent development framework with first-class support for MCP, A2A, AG-UI, and CopilotKit.

## Features

- **Plugin-First Architecture**: All capabilities expressed through a unified plugin interface
- **Multi-Protocol Support**:
  - **AG-UI**: Real-time streaming for generative UI (CopilotKit compatible)
  - **A2A**: Agent-to-agent communication (Google A2A standard)
  - **MCP**: Claude Desktop integration
- **Zero-Boilerplate Tools**: `@tool` decorator generates schemas from type hints
- **Production-Ready Observability**: OpenTelemetry, Prometheus, structured logging
- **Modern Tooling**: Python 3.12+, async-first, uv package manager

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/odin.git
cd odin
uv sync
```

### Create a Plugin

```python
from odin import DecoratorPlugin, tool

class WeatherPlugin(DecoratorPlugin):
    @property
    def name(self) -> str:
        return "weather"

    @property
    def version(self) -> str:
        return "1.0.0"

    @tool(description="Get weather for a location")
    async def get_weather(self, location: str) -> dict:
        """Get current weather.

        Args:
            location: City name
        """
        return {"location": location, "temp": "22°C", "condition": "Sunny"}
```

### Run the Demo

```bash
# Start backend (CopilotKit)
cd examples/demo
PYTHONPATH=../../src python main.py

# Start frontend (in another terminal)
cd examples/demo/frontend
npm install && npm run dev

# Open http://localhost:3000
```

### Protocol Options

```bash
# CopilotKit (default) - for React frontends
python main.py --protocol copilotkit

# AG-UI - raw AG-UI protocol
python main.py --protocol agui

# A2A - agent-to-agent communication
python main.py --protocol a2a
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Your App                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  AG-UI   │  │   A2A    │  │   MCP    │  │   HTTP   │        │
│  │ Protocol │  │ Protocol │  │ Protocol │  │   REST   │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │             │               │
│       └─────────────┴─────────────┴─────────────┘               │
│                           │                                      │
│                    ┌──────┴──────┐                              │
│                    │  Odin Core  │                              │
│                    │  (Runtime)  │                              │
│                    └──────┬──────┘                              │
│                           │                                      │
│       ┌───────────────────┼───────────────────┐                 │
│       │                   │                   │                 │
│  ┌────┴─────┐       ┌─────┴────┐       ┌─────┴────┐            │
│  │ Weather  │       │ Calendar │       │   Data   │            │
│  │ Plugin   │       │  Plugin  │       │  Plugin  │            │
│  └──────────┘       └──────────┘       └──────────┘            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
odin/
├── src/odin/
│   ├── core/            # Core framework runtime
│   ├── plugins/         # Plugin system (DecoratorPlugin, AgentPlugin)
│   ├── protocols/       # Protocol adapters
│   │   ├── agui/        # AG-UI (CopilotKit compatible)
│   │   ├── a2a/         # Agent-to-Agent
│   │   ├── mcp/         # Model Context Protocol
│   │   └── copilotkit/  # CopilotKit adapter
│   ├── decorators/      # @tool, @measure_latency, etc.
│   ├── tracing/         # OpenTelemetry integration
│   └── logging/         # Structured logging
├── examples/
│   └── demo/            # Complete demo with frontend
├── tests/               # Unit and integration tests
└── docs/                # Documentation
```

## Documentation

- [Protocol Documentation](docs/README.md)
- [AG-UI Protocol](docs/AGUI_PROTOCOL.md)
- [A2A Protocol](docs/A2A_PROTOCOL.md)

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Type checking
uv run mypy src/odin

# Linting
uv run ruff check src/odin

# Format code
uv run ruff format src/odin
```

## License

MIT
