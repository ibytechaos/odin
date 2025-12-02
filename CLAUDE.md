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
odin test <tool-name> -j '{"param": "value"}'
```

## Architecture

### Core Components

- **`src/odin/core/odin.py`**: Main Odin class - orchestrates plugin management, configuration, logging, and protocol servers
- **`src/odin/core/agent_factory.py`**: Factory for creating agent backends (CrewAI, LangGraph, custom)
- **`src/odin/core/llm_factory.py`**: Centralized LLM creation - supports OpenAI, Anthropic, Azure via environment variables
- **`src/odin/plugins/base.py`**: Plugin base classes (`AgentPlugin`, `DecoratorPlugin`) and tool definitions (`Tool`, `ToolParameter`)
- **`src/odin/plugins/manager.py`**: Plugin discovery and lifecycle management
- **`src/odin/decorators/tool.py`**: The `@tool` decorator for zero-boilerplate tool creation with automatic schema generation from type hints

### Plugin System

Plugins are organized into:

1. **Built-in Plugins** (`src/odin/plugins/builtin/`):
   - `http.py`: HTTP client tools for API calls and web requests
   - `utilities.py`: Utility tools for text, data, and math operations
   - `notebookllm.py`: Google NotebookLLM automation (presentation, mindmap, infographic generation)
   - `github.py`: GitHub trending repositories discovery and analysis
   - `xiaohongshu.py`: Xiaohongshu (小红书) automation and content tools
   - `gemini.py`: Google Gemini deep research automation
   - `google.py`: Google Custom Search API integration
   - `trending.py`: Hot topics mining from multiple sources
   - `content.py`: Content generation and storage (Obsidian, etc.)
   - `publishers.py`: Multi-platform blog publishing automation

2. **User Plugins**: Discovered from `plugin_dirs` configuration (default: `./plugins/`)

Two ways to create plugins:

1. **DecoratorPlugin** (recommended): Use `@tool` decorator on methods
   ```python
   class MyPlugin(DecoratorPlugin):
       @tool(description="Say hello")
       async def say_hello(self, name: str) -> dict:
           return {"message": f"Hello, {name}!"}
   ```

2. **AgentPlugin**: Implement `get_tools()` and `execute_tool()` manually for more control

### Built-in Plugin Registry

Built-in plugins are registered in `src/odin/plugins/builtin/__init__.py`:
```python
BUILTIN_PLUGINS = {
    "http": HTTPPlugin,
    "utilities": UtilitiesPlugin,
    "notebookllm": NotebookLLMPlugin,
    "github": GitHubPlugin,
    "xiaohongshu": XiaohongshuPlugin,
    "gemini": GeminiPlugin,
    "google": GooglePlugin,
    "trending": TrendingPlugin,
    "content": ContentPlugin,
    "publishers": PublishersPlugin,
}
```

Enable plugins via `ODIN_BUILTIN_PLUGINS` env var or settings:
```bash
ODIN_BUILTIN_PLUGINS=http,utilities,github,google
```

### Protocol Adapters

Located in `src/odin/protocols/`:

- **copilotkit/**: CopilotKit integration with LangGraph agent (`CopilotKitAdapter`)
- **agui/**: AG-UI protocol for generative UI (SSE streaming)
- **a2a/**: Agent-to-Agent protocol (Google A2A standard)
- **mcp/**: Model Context Protocol for Claude Desktop
- **http/**: REST API adapter

### Utility Modules

Located in `src/odin/utils/`:

- **browser_session.py**: Shared browser session management for Playwright automation
- **http_client.py**: HTTP client utilities
- **progress.py**: Progress bar utilities for long-running tasks

### Compatibility Module

Located in `src/odin/compat/`:

- Patches for third-party package compatibility issues (e.g., paddleocr 3.x + langchain)

### Key Patterns

- Tools convert to OpenAI format via `Tool.to_openai_format()` and MCP format via `Tool.to_mcp_format()`
- The `@tool` decorator extracts parameters from `Annotated[T, Field(...)]` (preferred) or Google-style docstrings (fallback)
- Async-first design: All plugin methods and tool executions are async

### CLI Structure

`src/odin/cli.py` provides:
- `odin create` - scaffold new projects from templates in `src/odin/templates/`
- `odin serve` - start server with specified protocol
- `odin list` - list available tools
- `odin test` - test individual tools with JSON parameters
- `odin repl` - interactive tool testing

### Configuration

Settings via `src/odin/config/settings.py` with Pydantic Settings. Key environment variables:

**General:**
- `ODIN_ENV`: development/staging/production
- `ODIN_LOG_LEVEL`: DEBUG/INFO/WARNING/ERROR

**LLM:**
- `ODIN_LLM_PROVIDER`: openai/anthropic/azure
- `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
- `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`

**Agent:**
- `ODIN_AGENT_BACKEND`: crewai/langgraph/custom
- `ODIN_CHECKPOINTER_TYPE`: memory/sqlite/postgres/redis

**Plugins:**
- `ODIN_BUILTIN_PLUGINS`: Comma-separated list of builtin plugins to load (default: http,utilities)
- `ODIN_PLUGIN_AUTO_DISCOVERY`: Enable/disable auto-discovery (default: true)
- `ODIN_PLUGIN_DIRS`: Comma-separated list of plugin directories

**Browser Automation:**
- `BROWSER_DEBUG_URL`: Chrome DevTools Protocol URL for browser automation
- `BROWSER_DOWNLOAD_DIR`: Download directory for browser automation

### Observability

- OpenTelemetry tracing in `src/odin/tracing/`
- Prometheus metrics via `src/odin/tracing/prometheus.py`
- Structured logging with structlog in `src/odin/logging/`

### Error Handling

Located in `src/odin/errors/`:
- Centralized error codes in `codes.py`
- Custom exception classes in `base.py`
- Error handlers in `handlers.py`

## Test Structure

- `tests/unit/` - Unit tests for core components
- Tests use pytest-asyncio with `asyncio_mode = "auto"`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.slow`

## Demo Application

`examples/demo/` contains a complete example with:
- Backend: FastAPI + Odin + CopilotKit
- Frontend: Next.js + CopilotKit React components
- Sample plugins: weather, calendar, data analysis
