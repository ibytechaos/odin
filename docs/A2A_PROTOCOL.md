  # A2A (Agent-to-Agent) Protocol Support

Odin provides comprehensive support for the [A2A (Agent-to-Agent) Protocol](https://a2a-protocol.org/), enabling agents to communicate using an industry-standard REST API with Server-Sent Events (SSE) for streaming updates.

## Overview

The A2A protocol is an open standard designed for agent interoperability. It allows agents built with different frameworks and languages to collaborate seamlessly.

**Key Features:**
- **Self-Describing**: Agents expose capabilities via Agent Cards (JSON)
- **Task-Based**: Work organized around tasks with defined lifecycles
- **Streaming**: Real-time updates via Server-Sent Events
- **Standards-Based**: Uses HTTP, JSON-RPC 2.0, and SSE

**Specification**: [https://a2a-protocol.org/latest/specification/](https://a2a-protocol.org/latest/specification/)

## Quick Start

### 1. Create an A2A Server

```python
from odin import Odin, tool, AgentPlugin
from odin.protocols.a2a import A2AServer

class MathPlugin(AgentPlugin):
    @property
    def name(self) -> str:
        return "math"

    @property
    def version(self) -> str:
        return "1.0.0"

    @tool()
    async def add(self, a: float, b: float) -> dict:
        """Add two numbers.

        Args:
            a: First number
            b: Second number
        """
        return {"result": a + b}

# Initialize Odin
app = Odin()
await app.initialize()
await app.register_plugin(MathPlugin())

# Create A2A server
a2a_server = A2AServer(
    odin_app=app,
    name="math-agent",
    description="Mathematical operations agent"
)

# Start server
await a2a_server.run(host="0.0.0.0", port=8000)
```

### 2. Test with curl

```bash
# Get agent card
curl http://localhost:8000/.well-known/agent-card

# Send a message
curl -X POST http://localhost:8000/message/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "role": "USER",
      "parts": [
        {"type": "text", "text": "Can you add 10 and 20?"}
      ]
    }
  }'

# Get task status
curl http://localhost:8000/tasks/{task-id}?include_history=true

# Streaming message
curl -N -X POST http://localhost:8000/message/send/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "role": "USER",
      "parts": [{"type": "text", "text": "Hello!"}]
    }
  }'
```

### 3. Use A2A Client

```python
import httpx

async with httpx.AsyncClient() as client:
    # Get agent card
    response = await client.get("http://localhost:8000/.well-known/agent-card")
    agent_card = response.json()
    print(f"Agent: {agent_card['name']}")
    print(f"Skills: {len(agent_card['skills'])}")

    # Send message
    response = await client.post(
        "http://localhost:8000/message/send",
        json={
            "message": {
                "role": "USER",
                "parts": [
                    {"type": "text", "text": "What can you do?"}
                ]
            }
        }
    )

    task = response.json()["task"]
    print(f"Task ID: {task['id']}")
    print(f"Status: {task['status']['state']}")
```

## API Endpoints

### Agent Card

**GET** `/.well-known/agent-card`

Returns the agent's self-describing capability card.

**Response:**
```json
{
  "name": "math-agent",
  "description": "Mathematical operations agent",
  "protocolVersion": "1.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "securitySchemes": [...],
  "skills": [
    {
      "name": "math",
      "description": "Mathematical operations",
      "examples": ["add: Add two numbers"]
    }
  ],
  "provider": {...},
  "metadata": {
    "odin_version": "0.1.0",
    "total_tools": 3
  }
}
```

### Send Message

**POST** `/message/send`

Send a message to the agent and create a task.

**Request:**
```json
{
  "message": {
    "role": "USER",
    "parts": [
      {"type": "text", "text": "Your message here"}
    ]
  },
  "contextId": "optional-context-id"
}
```

**Response:**
```json
{
  "task": {
    "id": "task-uuid",
    "contextId": "context-id",
    "status": {
      "state": "SUBMITTED",
      "message": null,
      "timestamp": "2025-01-27T12:00:00Z"
    },
    "artifacts": [],
    "history": [...]
  }
}
```

### Streaming Message

**POST** `/message/send/streaming`

Send a message with streaming response via Server-Sent Events.

**Request:** Same as `/message/send`

**Response:** SSE stream with events:
- `taskCreated`: Initial task creation
- `taskStatus`: Status updates
- `taskArtifact`: New artifacts

**Example Event:**
```
event: taskStatus
data: {"taskId": "...", "status": {"state": "WORKING", ...}}

event: taskArtifact
data: {"taskId": "...", "artifact": {...}}
```

### Get Task

**GET** `/tasks/{task_id}?include_history={bool}`

Get task status and optionally include message history.

**Response:**
```json
{
  "task": {
    "id": "task-uuid",
    "status": {...},
    "artifacts": [...],
    "history": [...]
  }
}
```

### List Tasks

**GET** `/tasks?context_id={id}&status={state}&limit={n}&offset={n}`

List tasks with optional filtering.

**Query Parameters:**
- `context_id`: Filter by context
- `status`: Filter by state (SUBMITTED, WORKING, COMPLETED, etc.)
- `limit`: Max results (default 100)
- `offset`: Pagination offset

**Response:**
```json
{
  "tasks": [...],
  "total": 42,
  "hasMore": true
}
```

### Subscribe to Task

**GET** `/tasks/{task_id}/subscribe`

Subscribe to task updates via SSE.

**Response:** SSE stream with `taskStatus` events.

## Core Concepts

### Agent Card

The Agent Card is a JSON document that describes the agent's capabilities, authentication requirements, and skills. It's automatically generated from your registered tools.

**Components:**
- **Identity**: name, description, provider
- **Capabilities**: streaming support, push notifications
- **Security Schemes**: Authentication methods (API key, OAuth2, etc.)
- **Skills**: Derived from plugins and their tools
- **Metadata**: Additional information (version, tool count)

### Task Lifecycle

Tasks progress through well-defined states:

```
SUBMITTED → WORKING → COMPLETED
     ↓          ↓
     ↓    INPUT_REQUIRED
     ↓          ↓
     ↓     AUTH_REQUIRED
     ↓          ↓
CANCELLED  FAILED/REJECTED
```

**States:**
- `SUBMITTED`: Task created and acknowledged
- `WORKING`: Actively processing
- `INPUT_REQUIRED`: Needs additional input from user
- `AUTH_REQUIRED`: Needs authentication
- `COMPLETED`: Successfully finished
- `FAILED`: Encountered error
- `CANCELLED`: Cancelled by user
- `REJECTED`: Rejected by agent

### Messages and Parts

Messages are the primary communication unit. Each message contains:
- `messageId`: Unique identifier
- `role`: USER or AGENT
- `parts`: Array of content parts
- `contextId`: Optional conversation context
- `taskId`: Optional associated task

**Part Types:**
- **Text**: `{"type": "text", "text": "..."}`
- **File**: `{"type": "file", "uri": "...", "mimeType": "..."}`
- **Data**: `{"type": "data", "data": {...}}`

### Artifacts

Artifacts are the outputs produced by tasks. Each artifact contains:
- `artifactId`: Unique identifier
- `parts`: Content (text, file, data)
- `metadata`: Additional information
- `timestamp`: Creation time

## Advanced Configuration

### Custom Security Schemes

```python
from odin.protocols.a2a.models import SecurityScheme

# Add OAuth2 authentication
a2a_server.agent_card_generator.add_security_scheme(
    SecurityScheme(
        type="oauth2",
        flows={
            "clientCredentials": {
                "tokenUrl": "https://auth.example.com/token",
                "scopes": {"read": "Read access", "write": "Write access"}
            }
        }
    )
)

# Add Bearer token authentication
a2a_server.agent_card_generator.add_security_scheme(
    SecurityScheme(
        type="http",
        scheme="bearer"
    )
)

# Add API Key authentication
a2a_server.agent_card_generator.add_security_scheme(
    SecurityScheme(
        type="apiKey",
        name="X-API-Key",
        in_="header"
    )
)
```

### Custom Agent Card Generator

```python
from odin.protocols.a2a.agent_card import AgentCardGenerator
from odin.protocols.a2a.models import AgentCapabilities, ProviderInfo

generator = AgentCardGenerator(
    odin_app=app,
    agent_name="my-custom-agent",
    agent_description="A highly specialized agent",
    provider_info=ProviderInfo(
        organization="My Company",
        url="https://mycompany.com",
        contact="support@mycompany.com"
    )
)

# Enable push notifications
generator.set_capabilities(
    AgentCapabilities(
        streaming=True,
        pushNotifications=True
    )
)

a2a_server = A2AServer(
    odin_app=app,
    agent_card_generator=generator
)
```

### Task Management

Direct task manipulation is possible via the TaskManager:

```python
from odin.protocols.a2a.models import TaskState

# Update task status
await a2a_server.task_manager.update_task_status(
    task_id="...",
    state=TaskState.WORKING,
    message="Processing your request"
)

# Add artifact
from odin.protocols.a2a.models import TaskArtifact, TextPart

artifact = TaskArtifact(
    parts=[TextPart(text="Result: 42")],
    metadata={"computation": "deep_thought"}
)
await a2a_server.task_manager.add_task_artifact(task_id="...", artifact=artifact)

# Complete task
await a2a_server.task_manager.complete_task(
    task_id="...",
    message="All computations complete"
)
```

## Examples

### Complete Server Example

See [examples/a2a_server_demo.py](../examples/a2a_server_demo.py) for a full working server with multiple plugins.

### Client Example

See [examples/a2a_client_demo.py](../examples/a2a_client_demo.py) for a complete client implementation demonstrating all API endpoints.

### Testing

See [examples/test_a2a.py](../examples/test_a2a.py) for automated tests.

## Best Practices

### 1. Design Self-Describing Skills

Organize tools into logical plugins that represent cohesive skills:

```python
class DocumentProcessingPlugin(AgentPlugin):
    """Document processing and analysis."""

    @tool()
    async def extract_text(self, document_url: str) -> dict:
        """Extract text from document."""
        pass

    @tool()
    async def summarize(self, text: str, max_length: int = 200) -> dict:
        """Summarize text content."""
        pass
```

This creates a single "DocumentProcessing" skill in the Agent Card with multiple related capabilities.

### 2. Use Meaningful Task Contexts

Group related messages using `contextId` for better task management:

```python
{
  "message": {...},
  "contextId": "user-123-session-456"
}
```

### 3. Handle Long-Running Tasks

For operations that take time, update task status regularly:

```python
async def process_complex_task(task_id: str):
    await task_manager.update_task_status(
        task_id, TaskState.WORKING, "Step 1: Loading data"
    )

    # Do work...

    await task_manager.update_task_status(
        task_id, TaskState.WORKING, "Step 2: Processing"
    )

    # More work...

    await task_manager.complete_task(task_id, "All steps complete")
```

### 4. Use Streaming for Interactive Experiences

For real-time interactions, use the streaming endpoint:

```python
# Client side
async with client.stream(
    "POST",
    "/message/send/streaming",
    json=request
) as response:
    async for line in response.aiter_lines():
        if line.startswith("data:"):
            # Process SSE event
            data = json.loads(line.split(":", 1)[1])
            # Update UI in real-time
```

### 5. Implement Proper Error Handling

Always handle errors gracefully and update task status:

```python
try:
    result = await process_message(message)
    await task_manager.complete_task(task_id)
except ValueError as e:
    await task_manager.fail_task(
        task_id,
        f"Invalid input: {str(e)}"
    )
except Exception as e:
    await task_manager.fail_task(
        task_id,
        f"Internal error: {str(e)}"
    )
```

## Integration with Other Protocols

Odin allows you to expose the same tools via multiple protocols:

```python
from odin.protocols.mcp import MCPServer
from odin.protocols.a2a import A2AServer

app = Odin()
await app.initialize()
await app.register_plugin(MyPlugin())

# Expose via MCP (for Claude Desktop)
mcp_server = MCPServer(app, name="my-agent")
# Run in background or separate process

# Also expose via A2A (for agent collaboration)
a2a_server = A2AServer(app, name="my-agent")
await a2a_server.run(host="0.0.0.0", port=8000)
```

## Resources

- **A2A Protocol Specification**: https://a2a-protocol.org/latest/specification/
- **GitHub Repository**: https://github.com/a2aproject/A2A
- **Linux Foundation Project**: https://www.linuxfoundation.org/projects
- **Google Announcement**: https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/

## Troubleshooting

### Server Won't Start

**Issue**: Port already in use

```bash
# Check what's using the port
lsof -i :8000

# Kill the process or use a different port
await a2a_server.run(host="0.0.0.0", port=8001)
```

### Tasks Stuck in WORKING State

**Issue**: Task processing not completing

- Ensure you call `complete_task()` or `fail_task()`
- Check for unhandled exceptions in task processing
- Verify task_id is correct

### Agent Card Not Showing Tools

**Issue**: Skills list is empty

- Ensure plugins are registered before creating A2A server
- Verify `get_tools()` returns tool list
- Check that `@tool` decorator is used correctly

### Streaming Not Working

**Issue**: SSE events not received

- Ensure client supports SSE (Server-Sent Events)
- Use `-N` flag with curl: `curl -N ...`
- Check that response is being streamed, not buffered
- Verify Content-Type is `text/event-stream`

## What's Next?

- **Authentication**: Implement security scheme validation
- **Push Notifications**: Add webhook support for proactive updates
- **Extended Agent Cards**: Richer authenticated agent capabilities
- **Multi-Agent Orchestration**: Examples of agents collaborating
- **Production Deployment**: Docker, Kubernetes, and load balancing guides
