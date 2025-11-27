"""A2A Server demonstration.

This example shows how to expose Odin tools as an A2A (Agent-to-Agent) server.

The A2A protocol enables agents to communicate with each other using a standardized
REST API with Server-Sent Events for streaming updates.

To run this server:
```bash
python examples/a2a_server_demo.py
```

The server will start on http://localhost:8000 with the following endpoints:

- GET /.well-known/agent-card - Agent capability card
- POST /message/send - Send a message
- POST /message/send/streaming - Send with streaming response
- GET /tasks/{id} - Get task status
- GET /tasks - List tasks
- GET /tasks/{id}/subscribe - Subscribe to task updates

To test manually:
```bash
# Get agent card
curl http://localhost:8000/.well-known/agent-card

# Send a message
curl -X POST http://localhost:8000/message/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "role": "USER",
      "parts": [{"type": "text", "text": "What can you do?"}]
    }
  }'

# Get task status
curl http://localhost:8000/tasks/{task-id}

# Streaming message (with curl)
curl -N -X POST http://localhost:8000/message/send/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "role": "USER",
      "parts": [{"type": "text", "text": "Hello agent!"}]
    }
  }'
```
"""

import asyncio

from odin import Odin, tool
from odin.plugins import AgentPlugin
from odin.protocols.a2a import A2AServer
from odin.protocols.a2a.agent_card import ProviderInfo


class MathPlugin(AgentPlugin):
    """Mathematical operations plugin."""

    @property
    def name(self) -> str:
        return "math"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Mathematical operations and calculations"

    @tool(name="add", description="Add two numbers")
    async def add(self, a: float, b: float) -> dict:
        """Add two numbers.

        Args:
            a: First number
            b: Second number

        Returns:
            Sum of the numbers
        """
        result = a + b
        return {
            "operation": "add",
            "inputs": {"a": a, "b": b},
            "result": result,
        }

    @tool(name="multiply", description="Multiply two numbers")
    async def multiply(self, a: float, b: float) -> dict:
        """Multiply two numbers.

        Args:
            a: First number
            b: Second number

        Returns:
            Product of the numbers
        """
        result = a * b
        return {
            "operation": "multiply",
            "inputs": {"a": a, "b": b},
            "result": result,
        }

    @tool(name="power", description="Calculate power (a^b)")
    async def power(self, base: float, exponent: float) -> dict:
        """Calculate power (a to the power of b).

        Args:
            base: Base number
            exponent: Exponent

        Returns:
            Result of base^exponent
        """
        result = base**exponent
        return {
            "operation": "power",
            "inputs": {"base": base, "exponent": exponent},
            "result": result,
        }

    async def get_tools(self):
        """Auto-discover tools from decorated methods."""
        from odin.decorators.tool import get_tool_from_function, is_tool

        tools = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def:
                    tools.append(tool_def)
        return tools

    async def execute_tool(self, tool_name: str, **kwargs):
        """Execute a tool by name."""
        from odin.decorators.tool import get_tool_from_function, is_tool

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def and tool_def.name == tool_name:
                    return await attr(**kwargs)

        raise ValueError(f"Tool '{tool_name}' not found")


class UtilityPlugin(AgentPlugin):
    """Utility functions plugin."""

    @property
    def name(self) -> str:
        return "utility"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Utility functions for text processing and data manipulation"

    @tool(name="reverse_text", description="Reverse text string")
    async def reverse_text(self, text: str) -> dict:
        """Reverse a text string.

        Args:
            text: Text to reverse

        Returns:
            Reversed text
        """
        return {
            "original": text,
            "reversed": text[::-1],
        }

    @tool(name="count_words", description="Count words in text")
    async def count_words(self, text: str) -> dict:
        """Count words in text.

        Args:
            text: Text to analyze

        Returns:
            Word count statistics
        """
        words = text.split()
        return {
            "text": text,
            "word_count": len(words),
            "char_count": len(text),
            "words": words,
        }

    async def get_tools(self):
        """Auto-discover tools from decorated methods."""
        from odin.decorators.tool import get_tool_from_function, is_tool

        tools = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def:
                    tools.append(tool_def)
        return tools

    async def execute_tool(self, tool_name: str, **kwargs):
        """Execute a tool by name."""
        from odin.decorators.tool import get_tool_from_function, is_tool

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def and tool_def.name == tool_name:
                    return await attr(**kwargs)

        raise ValueError(f"Tool '{tool_name}' not found")


async def main():
    """Run A2A server."""
    print("=" * 70)
    print("Odin A2A (Agent-to-Agent) Server Demo")
    print("=" * 70)

    # Create Odin app
    print("\n[1/3] Initializing Odin framework...")
    app = Odin()
    await app.initialize()

    # Register plugins
    print("[2/3] Registering plugins...")
    math_plugin = MathPlugin()
    utility_plugin = UtilityPlugin()

    await app.register_plugin(math_plugin)
    await app.register_plugin(utility_plugin)

    print(f"  Registered {len(app.list_plugins())} plugins:")
    for plugin in app.list_plugins():
        print(f"    - {plugin['name']}: {plugin['description']}")

    print(f"\n  Total tools available: {len(app.list_tools())}")
    for tool in app.list_tools():
        print(f"    - {tool['name']}: {tool['description']}")

    # Create A2A server
    print("\n[3/3] Creating A2A server...")
    a2a_server = A2AServer(
        odin_app=app,
        name="odin-demo-agent",
        description="Demo agent showcasing Odin framework capabilities via A2A protocol",
    )

    # Customize agent card (optional)
    from odin.protocols.a2a.models import SecurityScheme

    a2a_server.agent_card_generator.add_security_scheme(
        SecurityScheme(
            type="http",
            scheme="bearer",
        )
    )

    print("  ✓ A2A server created")

    print("\n" + "=" * 70)
    print("Server Information")
    print("=" * 70)
    print("\nEndpoints:")
    print("  - GET  /.well-known/agent-card")
    print("  - POST /message/send")
    print("  - POST /message/send/streaming")
    print("  - GET  /tasks/{id}")
    print("  - GET  /tasks")
    print("  - GET  /tasks/{id}/subscribe")

    print("\nFeatures:")
    print("  ✓ Agent Card (self-describing capabilities)")
    print("  ✓ Message send with task creation")
    print("  ✓ Streaming responses via SSE")
    print("  ✓ Task lifecycle management")
    print("  ✓ Task subscription and updates")

    print("\nTest Commands:")
    print("  # Get agent card")
    print("  curl http://localhost:8000/.well-known/agent-card")
    print("")
    print("  # Send a message")
    print('  curl -X POST http://localhost:8000/message/send \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"message": {"role": "USER", "parts": [')
    print('      {"type": "text", "text": "calculate add with a=10 and b=5"}')
    print("    ]}}\'")

    print("\n" + "=" * 70)
    print("Starting server on http://localhost:8000")
    print("Press Ctrl+C to stop")
    print("=" * 70 + "\n")

    # Run server
    try:
        await a2a_server.run(host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("\n\nShutting down A2A server...")
    finally:
        await app.shutdown()
        print("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
