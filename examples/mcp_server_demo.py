"""MCP Server demonstration.

This example shows how to expose Odin tools as an MCP server.

To use with Claude Desktop:
1. Run this script: python mcp_server_demo.py
2. Configure Claude Desktop to use this server
3. Tools will be available in Claude Desktop

To test manually:
```bash
# The server communicates via stdin/stdout
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | python mcp_server_demo.py
```
"""

import asyncio

from odin import Odin, tool
from odin.plugins import AgentPlugin
from odin.protocols.mcp import MCPServer


class ExamplePlugin(AgentPlugin):
    """Example plugin with some useful tools."""

    @property
    def name(self) -> str:
        return "example"

    @property
    def version(self) -> str:
        return "1.0.0"

    @tool(name="get_weather", description="Get weather for a location")
    async def get_weather(self, location: str, units: str = "celsius") -> dict:
        """
        Get current weather for a location.

        Args:
            location: City name or coordinates
            units: Temperature units (celsius or fahrenheit)

        Returns:
            Weather information
        """
        # Simulated weather data
        return {
            "location": location,
            "temperature": 22 if units == "celsius" else 72,
            "units": units,
            "condition": "Sunny",
            "humidity": 65,
        }

    @tool(name="calculate", description="Perform mathematical calculations")
    async def calculate(self, expression: str) -> dict:
        """
        Evaluate a mathematical expression.

        Args:
            expression: Math expression (e.g., "2 + 2", "10 * 5")

        Returns:
            Calculation result
        """
        try:
            # Safe eval for simple math
            result = eval(
                expression,
                {"__builtins__": {}},
                {
                    "abs": abs,
                    "min": min,
                    "max": max,
                    "sum": sum,
                    "round": round,
                    "pow": pow,
                },
            )
            return {
                "expression": expression,
                "result": result,
            }
        except Exception as e:
            return {
                "expression": expression,
                "error": str(e),
            }

    @tool(name="search_docs", description="Search documentation")
    async def search_docs(self, query: str, category: str = "all") -> dict:
        """
        Search through documentation.

        Args:
            query: Search query
            category: Documentation category (all, api, guides, examples)

        Returns:
            Search results
        """
        # Simulated search results
        results = [
            {
                "title": f"Result for: {query}",
                "url": f"/docs/{category}/result-1",
                "snippet": f"Information about {query}...",
            },
            {
                "title": f"Tutorial: {query}",
                "url": f"/docs/{category}/result-2",
                "snippet": f"Learn how to use {query}...",
            },
        ]
        return {
            "query": query,
            "category": category,
            "count": len(results),
            "results": results,
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
    """Run MCP server."""
    print("Initializing Odin MCP Server...")

    # Create Odin app
    app = Odin()
    await app.initialize()

    # Register plugin
    plugin = ExamplePlugin()
    await app.register_plugin(plugin)

    print(f"Registered {len(app.list_tools())} tools:")
    for tool in app.list_tools():
        print(f"  - {tool['name']}: {tool['description']}")

    print("\nStarting MCP server on stdio...")
    print("Server ready for MCP clients (e.g., Claude Desktop)")
    print("-" * 60)

    # Create and run MCP server
    mcp_server = MCPServer(app, name="odin-example")

    try:
        await mcp_server.run()
    except KeyboardInterrupt:
        print("\nShutting down MCP server...")
    finally:
        await app.shutdown()
        print("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
