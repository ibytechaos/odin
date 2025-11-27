# Odin

A modern, protocol-agnostic agent development framework with first-class support for MCP, A2A, and CrewAI.

## Features

- **Plugin-First Architecture**: All capabilities expressed through a unified plugin interface
- **Multi-Protocol Support**:
  - **MCP (Model Context Protocol)**: Expose tools to Claude Desktop and other MCP clients
  - **A2A (Agent-to-Agent)**: Enable agents to communicate using the industry-standard A2A protocol
  - **AG-UI (Agent-User Interaction)**: Real-time generative UI with Server-Sent Events
  - **HTTP/REST**: Traditional REST APIs with OpenAPI documentation
- **Zero-Boilerplate Tools**: `@tool` decorator automatically generates schemas from type hints and docstrings
- **CrewAI Integration**: First-class support for CrewAI agent orchestration
- **Production-Ready Observability**:
  - OpenTelemetry tracing and metrics
  - AI/LLM-specific metrics (token counting, cost tracking, latency)
  - Prometheus export
  - Structured logging with structlog
- **Modern Tooling**: Built with Python 3.12+, uv, and async-first design
- **Self-Describing**: Agent Cards automatically generated from registered tools

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/odin.git
cd odin

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Configuration

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
# At minimum, set your LLM API keys
```

### Basic Usage

#### Create a Plugin with Tools

```python
from odin import Odin, tool, AgentPlugin

class WeatherPlugin(AgentPlugin):
    @property
    def name(self) -> str:
        return "weather"

    @property
    def version(self) -> str:
        return "1.0.0"

    @tool()
    async def get_weather(self, location: str, units: str = "celsius") -> dict:
        """Get current weather for a location.

        Args:
            location: City name or coordinates
            units: Temperature units (celsius or fahrenheit)
        """
        # Your implementation here
        return {"location": location, "temp": 22, "units": units}
```

#### Expose via MCP (for Claude Desktop)

```python
from odin.protocols.mcp import MCPServer

app = Odin()
await app.initialize()
await app.register_plugin(WeatherPlugin())

# Start MCP server (stdio for Claude Desktop)
mcp_server = MCPServer(app, name="weather-agent")
await mcp_server.run()
```

#### Expose via A2A (for Agent-to-Agent Communication)

```python
from odin.protocols.a2a import A2AServer

app = Odin()
await app.initialize()
await app.register_plugin(WeatherPlugin())

# Start A2A server (HTTP + SSE)
a2a_server = A2AServer(app, name="weather-agent")
await a2a_server.run(host="0.0.0.0", port=8000)
```

#### Expose via AG-UI (for Generative UI)

```python
from odin.protocols.agui import AGUIServer

app = Odin()
await app.initialize()
await app.register_plugin(WeatherPlugin())

# Start AG-UI server (HTTP + SSE)
agui_server = AGUIServer(app, path="/")
await agui_server.run(host="0.0.0.0", port=8000)
```

See [examples/](examples/) for complete working examples.

**Try the complete end-to-end example:**
```bash
# All protocols in one agent (MCP, A2A, AG-UI)
PYTHONPATH=src uv run python examples/end_to_end_agent.py --protocol agui
```

## Architecture

```
odin/
├── config/          # Configuration management
├── core/            # Core framework runtime
├── logging/         # Structured logging
├── errors/          # Error handling
├── plugins/         # Plugin system and built-in plugins
├── protocols/       # Protocol adapters (MCP, A2A, HTTP)
├── storage/         # Data persistence
├── tracing/         # OpenTelemetry integration
└── utils/           # Utilities
```

## Development

```bash
# Install with dev dependencies
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

