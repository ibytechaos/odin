"""Decorator usage demonstration.

Shows how to use Odin's decorators for:
1. Automatic tool registration with @tool
2. Automatic metrics collection
3. Zero-boilerplate plugin development
"""

import asyncio
from typing import Any

from odin import (
    Odin,
    AgentPlugin,
    tool,
    measure_latency,
    count_calls,
    track_errors,
)
from odin.decorators.tool import get_tool_from_function, is_tool


class DecoratedPlugin(AgentPlugin):
    """Plugin demonstrating decorator-based tool registration."""

    @property
    def name(self) -> str:
        return "decorated"

    @property
    def version(self) -> str:
        return "1.0.0"

    # ========================================
    # Tool 1: Basic @tool decorator
    # ========================================
    @tool(name="greet", description="Greet a user")
    async def greet_user(self, name: str, greeting: str = "Hello") -> dict:
        """
        Greet a user with a custom message.

        Args:
            name: The user's name
            greeting: The greeting message (defaults to "Hello")

        Returns:
            A greeting response
        """
        return {"message": f"{greeting}, {name}!"}

    # ========================================
    # Tool 2: With automatic metrics
    # ========================================
    @tool()
    @measure_latency(metric_name="api.search")
    @count_calls(metric_name="api.search.calls")
    async def search(self, query: str, max_results: int = 10) -> dict:
        """
        Search for information.

        Args:
            query: Search query string
            max_results: Maximum number of results
        """
        # Simulate search
        await asyncio.sleep(0.1)
        return {
            "query": query,
            "results": [f"Result {i}" for i in range(max_results)],
        }

    # ========================================
    # Tool 3: With error tracking
    # ========================================
    @tool()
    @track_errors(metric_name="api.process.errors")
    @measure_latency()
    async def process_data(self, data: str, validate: bool = True) -> dict:
        """
        Process and validate data.

        Args:
            data: Input data to process
            validate: Whether to perform validation
        """
        if validate and not data:
            raise ValueError("Data cannot be empty")

        return {"processed": data.upper(), "validated": validate}

    # ========================================
    # Tool 4: Complex types
    # ========================================
    @tool()
    async def analyze(
        self,
        text: str,
        options: dict = None,
        tags: list = None,
    ) -> dict:
        """
        Analyze text with options.

        Args:
            text: Text to analyze
            options: Analysis options (optional)
            tags: List of tags (optional)
        """
        return {
            "text_length": len(text),
            "options": options or {},
            "tags": tags or [],
        }

    # ========================================
    # Plugin interface implementation
    # ========================================
    async def get_tools(self):
        """Auto-discover tools from decorated methods."""
        tools = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def:
                    tools.append(tool_def)
        return tools

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a tool by name."""
        # Find the method
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def and tool_def.name == tool_name:
                    # Call the method
                    return await attr(**kwargs)

        raise ValueError(f"Tool '{tool_name}' not found")


async def main():
    """Run decorator demonstration."""
    print("=" * 70)
    print("Odin Decorator Demonstration")
    print("=" * 70)

    # Initialize framework
    app = Odin()
    await app.initialize()

    # Register plugin
    plugin = DecoratedPlugin()
    await app.register_plugin(plugin)

    print("\n[1/5] Auto-discovered tools from @tool decorator")
    tools = app.list_tools()
    for i, tool in enumerate(tools, 1):
        print(f"\n  {i}. {tool['name']}")
        print(f"     Description: {tool['description']}")
        print(f"     Parameters:")
        for param in tool["parameters"]:
            req = " (required)" if param["required"] else ""
            print(f"       - {param['name']}: {param['type']}{req}")
            print(f"         {param['description']}")

    # Test tools
    print("\n" + "=" * 70)
    print("Tool Execution Examples")
    print("=" * 70)

    print("\n[2/5] Basic tool with auto-parsed parameters")
    result = await app.execute_tool("greet", name="Alice")
    print(f"  Result: {result}")

    print("\n[3/5] Tool with automatic latency measurement")
    result = await app.execute_tool("search", query="Python async", max_results=3)
    print(f"  Result: {result}")
    print("  ✓ Metrics recorded: api.search (latency), api.search.calls (counter)")

    print("\n[4/5] Tool with error tracking")
    result = await app.execute_tool("process_data", data="hello", validate=True)
    print(f"  Result: {result}")

    try:
        await app.execute_tool("process_data", data="", validate=True)
    except Exception as e:
        print(f"  Expected error: {e}")
        print("  ✓ Error metric recorded: api.process.errors")

    print("\n[5/5] Tool with complex types")
    result = await app.execute_tool(
        "analyze",
        text="Sample text",
        options={"detailed": True},
        tags=["sample", "test"],
    )
    print(f"  Result: {result}")

    # Show benefits
    print("\n" + "=" * 70)
    print("Benefits of Decorator Approach")
    print("=" * 70)
    print("""
  ✓ Zero Boilerplate
    - No manual Tool() creation
    - Parameter types auto-detected from type hints
    - Descriptions from docstrings

  ✓ Automatic Metrics
    - @measure_latency → automatic latency tracking
    - @count_calls → automatic call counting
    - @track_errors → automatic error tracking

  ✓ Type Safety
    - Type hints preserved
    - IDE autocomplete works
    - Mypy compatible

  ✓ Self-Documenting
    - Docstrings become tool descriptions
    - Parameter docs from Google/NumPy style docstrings

  ✓ Composable
    - Stack multiple decorators
    - Mix and match as needed
    """)

    print("\n" + "=" * 70)
    print("Developer Experience Comparison")
    print("=" * 70)

    print("\n  OLD WAY (Manual):")
    print("""
    async def get_tools(self):
        return [
            Tool(
                name="greet",
                description="Greet a user",
                parameters=[
                    ToolParameter(
                        name="name",
                        type=ToolParameterType.STRING,
                        description="User's name",
                        required=True,
                    ),
                    ToolParameter(
                        name="greeting",
                        type=ToolParameterType.STRING,
                        description="Greeting message",
                        required=False,
                        default="Hello",
                    ),
                ],
            ),
        ]
    """)

    print("  NEW WAY (Decorator):")
    print("""
    @tool()
    async def greet(self, name: str, greeting: str = "Hello"):
        '''Greet a user.

        Args:
            name: User's name
            greeting: Greeting message
        '''
        return {"message": f"{greeting}, {name}!"}
    """)

    print("\n  Result: ~80% less code, more readable, less error-prone!")

    # Cleanup
    print("\n" + "=" * 70)
    await app.shutdown()
    print("✓ Demo complete")


if __name__ == "__main__":
    asyncio.run(main())
