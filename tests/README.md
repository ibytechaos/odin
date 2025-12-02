# Odin Test Strategy

## Coverage Target: 90%

## Test Structure

```
tests/
├── conftest.py              # Global fixtures
├── fixtures/                # Shared test data and factories
│   ├── __init__.py
│   ├── plugins.py           # Plugin test factories
│   ├── tools.py             # Tool test data
│   └── mocks.py             # Common mocks
├── unit/                    # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_plugins.py      # Plugin base classes
│   ├── test_decorators.py   # @tool decorator
│   ├── test_errors.py       # Error handling
│   ├── test_odin_core.py    # Odin core class
│   ├── test_config.py       # Settings and config
│   ├── test_llm_factory.py  # LLM factory
│   ├── test_utils/          # Utils module tests
│   │   ├── test_browser_session.py
│   │   ├── test_http_client.py
│   │   └── test_progress.py
│   └── test_builtin/        # Builtin plugin tests
│       ├── test_http_plugin.py
│       ├── test_utilities_plugin.py
│       ├── test_github_plugin.py
│       ├── test_google_plugin.py
│       ├── test_trending_plugin.py
│       ├── test_content_plugin.py
│       ├── test_publishers_plugin.py
│       ├── test_xiaohongshu_plugin.py
│       ├── test_gemini_plugin.py
│       └── test_notebookllm_plugin.py
├── integration/             # Integration tests (slower, dependencies)
│   ├── __init__.py
│   ├── test_plugin_manager.py
│   └── test_protocols.py
└── e2e/                     # End-to-end tests (full stack)
    └── __init__.py
```

## Testing Principles

### 1. Unit Tests
- Test single functions/methods in isolation
- Mock all external dependencies
- Fast execution (< 100ms per test)
- No network calls, no file I/O (except temp files)

### 2. Plugin Tests
- Test tool registration and metadata
- Test tool execution with mocked dependencies
- Test error handling and edge cases
- Use fixtures for common plugin setup

### 3. Mock Strategy
- **Browser**: Mock `BrowserSession`, `get_browser_session`
- **HTTP**: Mock `httpx.AsyncClient`, `aiohttp.ClientSession`
- **File I/O**: Use `tempfile` or mock `Path`
- **External APIs**: Mock response data

### 4. Fixtures
- `@pytest.fixture` for reusable test setup
- Factory functions for test data
- Async fixtures for async tests

## Key Modules to Test

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| `plugins/base.py` | 70% | 95% | High |
| `plugins/manager.py` | 56% | 90% | High |
| `decorators/tool.py` | 82% | 95% | High |
| `config/settings.py` | 88% | 95% | Medium |
| `core/odin.py` | 81% | 95% | High |
| `core/llm_factory.py` | 0% | 90% | High |
| `utils/browser_session.py` | 18% | 85% | Medium |
| `utils/http_client.py` | 30% | 90% | Medium |
| `utils/progress.py` | 28% | 90% | Medium |
| `plugins/builtin/*.py` | ~20% | 80% | Medium |
| `protocols/*.py` | 0% | 70% | Low |

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=odin --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_plugins.py

# Run tests by marker
uv run pytest -m unit
uv run pytest -m integration

# Run with verbose output
uv run pytest -v

# Run single test
uv run pytest tests/unit/test_plugins.py::TestDecoratorPlugin::test_get_tools
```

## Markers

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow tests (> 1s)
