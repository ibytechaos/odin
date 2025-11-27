# AG-UI (Agent-User Interaction) Protocol Support

Odin provides comprehensive support for the [AG-UI Protocol](https://docs.ag-ui.com/), enabling real-time agent interactions with generative UI systems.

## Overview

AG-UI (Agent-User Interaction Protocol) is an open standard created by CopilotKit that connects agent backends to frontend applications. It enables:

- **Real-time Streaming**: Server-Sent Events (SSE) for immediate feedback
- **Generative UI**: Dynamic UI generation based on agent responses
- **Tool Execution**: Backend tools rendered in the frontend
- **Human-in-the-Loop**: Approval workflows
- **Shared State**: Bidirectional state synchronization

**Official Documentation**: [https://docs.ag-ui.com/](https://docs.ag-ui.com/)

## Quick Start

### 1. Create an AG-UI Server

```python
from odin import Odin
from odin.protocols.agui import AGUIServer

# Initialize Odin and register plugins
app = Odin()
await app.initialize()
await app.register_plugin(YourPlugin())

# Create AG-UI server
agui_server = AGUIServer(app, path="/")

# Start server
await agui_server.run(host="0.0.0.0", port=8000)
```

### 2. Test with curl

```bash
curl -N -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "thread_id": "thread-123",
    "run_id": "run-456",
    "messages": [
      {
        "role": "user",
        "content": "What can you do?"
      }
    ]
  }'
```

### 3. Use Python Client

```python
import httpx

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://localhost:8000/",
        json={
            "thread_id": "thread-001",
            "run_id": "run-001",
            "messages": [
                {"role": "user", "content": "Hello!"}
            ]
        },
        headers={"Accept": "text/event-stream"}
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data:"):
                data = json.loads(line[5:])
                print(f"Event: {data.get('event')}")
```

## Complete End-to-End Example

See `examples/end_to_end_agent.py` for a production-ready example with:

- **Weather Plugin**: Current weather and forecasts
- **Calendar Plugin**: Event management
- **Multi-Protocol Support**: MCP, A2A, and AG-UI
- **Proper Logging**: Structured logging (no print statements)
- **Observability**: Full OpenTelemetry integration

### Running the Example

```bash
# Start AG-UI server
PYTHONPATH=src uv run python examples/end_to_end_agent.py --protocol agui

# Run client tests
PYTHONPATH=src uv run python examples/agui_client_demo.py
```

## Protocol Specification

### Request Format

**POST** `/` (or custom path)

```json
{
  "thread_id": "string",
  "run_id": "string",
  "messages": [
    {
      "role": "user" | "assistant" | "system" | "tool",
      "content": "string",
      "tool_calls": [...],  // Optional
      "tool_call_id": "string"  // Optional
    }
  ],
  "tools": [  // Optional
    {
      "name": "string",
      "description": "string",
      "parameters": {...}  // JSON Schema
    }
  ]
}
```

### Response Format (SSE)

The server responds with Server-Sent Events:

```
data: {"event": "RUN_STARTED", "thread_id": "...", "run_id": "..."}

data: {"event": "TEXT_MESSAGE_CHUNK", "message_id": "...", "delta": "Hello"}

data: {"event": "TEXT_MESSAGE_CHUNK", "message_id": "...", "delta": " world"}

data: {"event": "RUN_FINISHED", "thread_id": "...", "run_id": "..."}
```

## Event Types

### Lifecycle Events

| Event Type | Description | Fields |
|------------|-------------|--------|
| `RUN_STARTED` | Run begins | `thread_id`, `run_id` |
| `RUN_FINISHED` | Run completes successfully | `thread_id`, `run_id` |
| `RUN_ERROR` | Run encounters error | `thread_id`, `run_id`, `message`, `error` |

### Content Events

| Event Type | Description | Fields |
|------------|-------------|--------|
| `TEXT_MESSAGE_CHUNK` | Streaming text content | `message_id`, `delta`, `thread_id`, `run_id` |
| `TOOL_CALL_CHUNK` | Tool execution | `tool_call_id`, `tool_call_name`, `parent_message_id`, `delta`, `thread_id`, `run_id` |
| `STATE_UPDATE` | Shared state update | `thread_id`, `run_id`, `state` |

## Advanced Features

### Custom Endpoint Path

```python
agui_server = AGUIServer(app, path="/my-agent")
# Endpoint available at: http://localhost:8000/my-agent
```

### Health Check

Built-in health check endpoint:

```bash
curl http://localhost:8000/health
# {"status": "healthy", "version": "1.0.0"}
```

### Streaming Text Chunks

The server automatically streams responses in chunks for a better user experience:

```python
# Response text is split into chunks
chunk_size = 30
for i in range(0, len(response_text), chunk_size):
    chunk = response_text[i : i + chunk_size]
    yield TextMessageChunkEvent(
        message_id=message_id,
        delta=chunk,
        ...
    )
    await asyncio.sleep(0.05)  # Smooth streaming effect
```

### Tool Routing

The AG-UI server includes intelligent tool routing:

```python
# Automatically matches tool names in user messages
user_text = "What's the weather in Paris?"

# Matches "weather" tool if registered
matched_tool = find_tool_by_name_in_text(user_text, available_tools)

# Executes tool and streams results
result = await odin_app.execute_tool(matched_tool["name"])
```

## Integration with Frontend

### Using with CopilotKit

```typescript
import { CopilotKit } from "@copilotkit/react-core";

<CopilotKit
  runtimeUrl="http://localhost:8000/"
  agent="your-agent-name"
>
  {/* Your app components */}
</CopilotKit>
```

### Using with Custom Frontend

```javascript
const eventSource = new EventSource('http://localhost:8000/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    thread_id: 'thread-001',
    run_id: 'run-001',
    messages: [{role: 'user', content: 'Hello!'}]
  })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.event);

  if (data.event === 'TEXT_MESSAGE_CHUNK') {
    // Update UI with text delta
    appendText(data.delta);
  }
};
```

## Multi-Protocol Architecture

Odin allows you to expose the same agent via multiple protocols:

```python
from odin import Odin
from odin.protocols.mcp import MCPServer
from odin.protocols.a2a import A2AServer
from odin.protocols.agui import AGUIServer

app = Odin()
await app.initialize()
await app.register_plugin(MyPlugin())

# Option 1: MCP (for Claude Desktop)
# mcp_server = MCPServer(app)
# await mcp_server.run()

# Option 2: A2A (for agent collaboration)
# a2a_server = A2AServer(app)
# await a2a_server.run(port=8000)

# Option 3: AG-UI (for generative UI)
agui_server = AGUIServer(app)
await agui_server.run(port=8000)
```

## Best Practices

### 1. Use Proper Logging

❌ **Don't use print statements:**
```python
print(f"Processing message: {text}")
```

✅ **Use structured logging:**
```python
from odin.logging import get_logger

logger = get_logger(__name__)
logger.info("Processing message", text_preview=text[:100])
```

### 2. Handle Errors Gracefully

```python
try:
    result = await execute_tool(tool_name, **params)
    yield TextMessageChunkEvent(...)
except Exception as e:
    logger.error("Tool execution failed", tool=tool_name, error=str(e))
    yield RunErrorEvent(
        thread_id=thread_id,
        run_id=run_id,
        message=str(e),
        error=e.__class__.__name__
    )
```

### 3. Implement Streaming for Long Responses

```python
# Split long responses into chunks
async def stream_response(text: str):
    chunk_size = 50
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        yield TextMessageChunkEvent(delta=chunk, ...)
        await asyncio.sleep(0.05)  # Smooth streaming
```

### 4. Use Meaningful Thread and Run IDs

```python
# Client side: Use consistent IDs for conversation tracking
request = {
    "thread_id": f"user-{user_id}-session-{session_id}",
    "run_id": f"run-{timestamp}-{random_id}",
    "messages": [...]
}
```

### 5. Enable Observability

```python
# Odin automatically tracks:
# - Tool execution latency
# - Error rates
# - Request counts

# Access metrics via Prometheus
# http://localhost:9090/metrics
```

## Comparison: AG-UI vs A2A vs MCP

| Feature | AG-UI | A2A | MCP |
|---------|-------|-----|-----|
| **Primary Use** | Generative UI | Agent collaboration | Claude Desktop |
| **Transport** | HTTP + SSE | HTTP + SSE | stdio / SSE |
| **Streaming** | ✅ Real-time | ✅ Real-time | ✅ Real-time |
| **State Management** | ✅ Bidirectional | ✅ Task-based | ❌ Stateless |
| **Tool Execution** | ✅ | ✅ | ✅ |
| **Human-in-Loop** | ✅ | ⚠️ Possible | ❌ |
| **UI Generation** | ✅ Native | ❌ | ❌ |
| **Best For** | Web apps | Multi-agent | Claude integration |

**Recommendation**:
- Use **MCP** for Claude Desktop integration
- Use **A2A** for agent-to-agent communication
- Use **AG-UI** for web applications with generative UI

## Troubleshooting

### Server Won't Start

**Issue**: Port already in use

```bash
# Find process using port
lsof -i :8000

# Use different port
python examples/end_to_end_agent.py --protocol agui --port 8001
```

### No Events Received

**Issue**: SSE connection not streaming

- Ensure `Accept: text/event-stream` header is set
- Use `-N` flag with curl: `curl -N ...`
- Check that response is not being buffered
- Verify server is running and accessible

### Tool Not Executing

**Issue**: Tool mentioned in message but not executing

- Ensure tool name is mentioned in user message
- Check tool is registered: `app.list_tools()`
- Verify tool execution doesn't raise exceptions
- Check server logs for errors

### CORS Issues (Web Frontend)

**Issue**: Browser blocks requests due to CORS

```python
from fastapi.middleware.cors import CORSMiddleware

agui_server.app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Examples

### 1. Weather Agent

See `examples/end_to_end_agent.py` - Weather and calendar management agent

### 2. Client Demo

See `examples/agui_client_demo.py` - Complete client with health check, weather queries, and calendar events

### 3. Multi-Protocol

Run same agent with different protocols:

```bash
# Terminal 1: AG-UI server
PYTHONPATH=src uv run python examples/end_to_end_agent.py --protocol agui

# Terminal 2: A2A server (same agent, different protocol)
PYTHONPATH=src uv run python examples/end_to_end_agent.py --protocol a2a --port 8001

# Terminal 3: MCP server (for Claude Desktop)
PYTHONPATH=src uv run python examples/end_to_end_agent.py --protocol mcp
```

## Resources

- **AG-UI Documentation**: https://docs.ag-ui.com/
- **CopilotKit**: https://www.copilotkit.ai/
- **Microsoft Integration**: https://learn.microsoft.com/en-us/agent-framework/integrations/ag-ui/
- **Odin Examples**: `examples/end_to_end_agent.py`

## What's Next?

- **Authentication**: Add API key or OAuth2 authentication
- **Rate Limiting**: Implement request throttling
- **Webhooks**: Push notifications for proactive updates
- **UI Components**: Custom generative UI components
- **Production Deployment**: Docker, Kubernetes, load balancing

---

**Status**: ✅ Fully implemented and production-ready
**Version**: 1.0.0
**Last Updated**: 2025-11-27
