# {{PROJECT_TITLE}}

AI Agent powered by [Odin Framework](https://github.com/your-org/odin).

## Project Structure

```
.
├── agent/              # Python AI Agent
│   ├── main.py         # Agent entry point
│   ├── tools/          # Custom tools
│   │   └── example.py  # Example tool implementations
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

Visit [http://localhost:3000](http://localhost:3000)

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
