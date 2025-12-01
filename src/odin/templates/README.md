# {{PROJECT_TITLE}}

AI Agent powered by [Odin Framework](https://github.com/your-org/odin).

## Project Structure

```
.
├── agent/              # Python AI Agent
│   ├── main.py         # Agent entry point
│   ├── tools/          # Custom tools
│   │   ├── example.py  # Example tool implementations
│   │   └── utilities.py # Built-in utility tools
│   ├── Dockerfile      # Agent container
│   └── pyproject.toml  # Python dependencies
├── ui/                 # Next.js Frontend
│   ├── src/app/        # App router pages
│   ├── Dockerfile      # UI container
│   └── package.json    # Node dependencies
├── docker-compose.yml  # Multi-container setup
├── Makefile            # Development commands
└── .env.example        # Environment template
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key (or compatible endpoint)

### Setup

1. **Install dependencies**

```bash
make install
```

2. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your API key
```

3. **Start development servers**

```bash
make dev
```

4. **Open the UI**

- UI: [http://localhost:3000](http://localhost:3000)
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## CLI Commands

Use the Odin CLI to manage and test your tools:

```bash
# List all available tools
odin list

# List tools as JSON
odin list --json

# Test a specific tool
odin test greet
odin test greet -p name=Alice
odin test add -p a=1 -p b=2

# Start interactive REPL
odin repl
```

## API Documentation

When the server is running, you can access:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and tool list |
| `/tools` | GET | List all available tools |
| `/tools/{name}` | GET | Get tool information |
| `/tools/{name}` | POST | Execute a tool |
| `/copilotkit` | POST | CopilotKit AG-UI protocol |

## Development

### Adding Custom Tools

Create new tools in `agent/tools/`:

```python
from odin.plugins import DecoratorPlugin
from odin.decorators import tool

class MyTools(DecoratorPlugin):
    @property
    def name(self) -> str:
        return "my_tools"

    @tool()
    def my_custom_tool(self, param: str) -> dict:
        """Description for the AI."""
        return {"result": f"Processed: {param}"}
```

### Built-in Utility Tools

The project includes built-in utility tools in `agent/tools/utilities.py`:

- **Text Processing**: `text_length`, `text_case`, `text_replace`, `regex_match`
- **Data Processing**: `json_parse`, `json_format`
- **Validation**: `validate_email`, `validate_url`
- **Hashing**: `hash_text` (md5, sha1, sha256, sha512)
- **Math**: `calculate`, `random_number`, `uuid_generate`

These are "pan-agents" - simple atomic operations that don't require LLM but can be composed by the AI to build complex workflows.

### Available Commands

```bash
make help         # Show all commands
make dev          # Start development servers
make build        # Build for production
make docker-up    # Start with Docker
make test         # Run tests
make lint         # Run linters
```

## Docker Deployment

```bash
# Build and start all services
make docker-build
make docker-up

# View logs
docker-compose logs -f

# Stop services
make docker-down
```

## License

MIT
