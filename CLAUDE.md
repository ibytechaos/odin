# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Odin is a Python 3.14+ agent development framework with multi-protocol support for MCP, A2A, AG-UI, and CopilotKit. It uses a plugin-first architecture where all capabilities are expressed through a unified plugin interface.

## Common Commands

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run a single test file
uv run pytest tests/unit/test_plugins.py

# Run tests with specific marker
uv run pytest -m unit

# Type checking
uv run mypy src/odin

# Linting
uv run ruff check src/odin

# Format code
uv run ruff format src/odin

# Run the demo
cd examples/demo
PYTHONPATH=../../src python main.py

# Create a new project
odin create my-agent

# Start Odin server
odin serve --protocol copilotkit --port 8000

# List available tools
odin list --builtin

# Test a specific tool
odin test greet -p name=World
```

## Architecture

### Core Components

- **`src/odin/core/odin.py`**: Main Odin class - orchestrates plugin management, configuration, logging, and protocol servers
- **`src/odin/plugins/base.py`**: Plugin base classes (`AgentPlugin`, `DecoratorPlugin`) and tool definitions (`Tool`, `ToolParameter`)
- **`src/odin/plugins/manager.py`**: Plugin discovery and lifecycle management
- **`src/odin/decorators/tool.py`**: The `@tool` decorator for zero-boilerplate tool creation with automatic schema generation from type hints

### Plugin System

Two ways to create plugins:

1. **DecoratorPlugin** (recommended): Use `@tool` decorator on methods
   ```python
   class MyPlugin(DecoratorPlugin):
       @tool(description="Say hello")
       async def say_hello(self, name: str) -> dict:
           return {"message": f"Hello, {name}!"}
   ```

2. **AgentPlugin**: Implement `get_tools()` and `execute_tool()` manually for more control

### Protocol Adapters

Located in `src/odin/protocols/`:

- **copilotkit/**: CopilotKit integration with LangGraph agent (`CopilotKitAdapter`)
- **agui/**: AG-UI protocol for generative UI (SSE streaming)
- **a2a/**: Agent-to-Agent protocol (Google A2A standard)
- **mcp/**: Model Context Protocol for Claude Desktop
- **http/**: REST API adapter

### Key Patterns

- Tools convert to OpenAI format via `Tool.to_openai_format()` and MCP format via `Tool.to_mcp_format()`
- The `@tool` decorator extracts parameters from `Annotated[T, Field(...)]` (preferred) or Google-style docstrings (fallback)
- LLM creation is centralized in `src/odin/core/llm_factory.py` - supports OpenAI, Anthropic, Azure via environment variables

### CLI Structure

`src/odin/cli.py` provides:
- `odin create` - scaffold new projects from templates in `src/odin/templates/`
- `odin serve` - start server with specified protocol
- `odin list` - list available tools
- `odin test` - test individual tools
- `odin repl` - interactive tool testing

### Configuration

Settings via `src/odin/config/settings.py` with Pydantic Settings. Environment variables:
- `ODIN_ENV`: development/staging/production
- `ODIN_LOG_LEVEL`: DEBUG/INFO/WARNING/ERROR
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for LLM

### Observability

- OpenTelemetry tracing in `src/odin/tracing/`
- Prometheus metrics via `src/odin/tracing/prometheus.py`
- Structured logging with structlog in `src/odin/logging/`

## Test Structure

- `tests/unit/` - Unit tests for core components
- Tests use pytest-asyncio with `asyncio_mode = "auto"`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.slow`

## Demo Application

`examples/demo/` contains a complete example with:
- Backend: FastAPI + Odin + CopilotKit
- Frontend: Next.js + CopilotKit React components
- Sample plugins: weather, calendar, data analysis
