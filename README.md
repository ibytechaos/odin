# Odin

A modern, protocol-agnostic agent development framework with first-class support for MCP, A2A, and CrewAI.

## Features

- **Plugin-First Architecture**: All capabilities expressed through a unified plugin interface
- **Protocol-Agnostic**: Native support for MCP, A2A, HTTP/REST, and WebSocket protocols
- **CrewAI Integration**: First-class support for CrewAI agent orchestration
- **Production-Ready**: Built-in logging, tracing (OpenTelemetry), error handling, and monitoring
- **Modern Tooling**: Built with Python 3.12+, uv, and async-first design
- **Developer Experience**: Rich CLI, auto-generated docs, and comprehensive testing

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

```python
from odin import Odin
from odin.plugins.crewai import CrewAIPlugin

# Initialize framework
app = Odin()

# Load CrewAI plugin
crewai_plugin = CrewAIPlugin()
app.register_plugin(crewai_plugin)

# Start MCP server
await app.serve_mcp(port=8001)
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

