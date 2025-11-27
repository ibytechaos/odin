"""Example of creating a custom plugin for Odin.

This example shows how to:
1. Create a custom plugin by subclassing AgentPlugin
2. Define tools for the plugin
3. Implement tool execution logic
4. Register and use the plugin
"""

import asyncio
from typing import Any

from odin import Odin, AgentPlugin, Tool, ToolParameter
from odin.plugins.base import ToolParameterType


class CalculatorPlugin(AgentPlugin):
    """Simple calculator plugin for demonstration."""

    @property
    def name(self) -> str:
        """Get plugin name."""
        return "calculator"

    @property
    def version(self) -> str:
        """Get plugin version."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """Get plugin description."""
        return "Basic mathematical operations"

    async def get_tools(self) -> list[Tool]:
        """Get calculator tools."""
        return [
            Tool(
                name="add",
                description="Add two numbers",
                parameters=[
                    ToolParameter(
                        name="a",
                        type=ToolParameterType.NUMBER,
                        description="First number",
                        required=True,
                    ),
                    ToolParameter(
                        name="b",
                        type=ToolParameterType.NUMBER,
                        description="Second number",
                        required=True,
                    ),
                ],
            ),
            Tool(
                name="multiply",
                description="Multiply two numbers",
                parameters=[
                    ToolParameter(
                        name="a",
                        type=ToolParameterType.NUMBER,
                        description="First number",
                        required=True,
                    ),
                    ToolParameter(
                        name="b",
                        type=ToolParameterType.NUMBER,
                        description="Second number",
                        required=True,
                    ),
                ],
            ),
            Tool(
                name="power",
                description="Raise a number to a power",
                parameters=[
                    ToolParameter(
                        name="base",
                        type=ToolParameterType.NUMBER,
                        description="Base number",
                        required=True,
                    ),
                    ToolParameter(
                        name="exponent",
                        type=ToolParameterType.NUMBER,
                        description="Exponent",
                        required=True,
                    ),
                ],
            ),
        ]

    async def execute_tool(
        self, tool_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Execute a calculator tool."""
        if tool_name == "add":
            result = kwargs["a"] + kwargs["b"]
            return {
                "operation": "addition",
                "a": kwargs["a"],
                "b": kwargs["b"],
                "result": result,
            }
        elif tool_name == "multiply":
            result = kwargs["a"] * kwargs["b"]
            return {
                "operation": "multiplication",
                "a": kwargs["a"],
                "b": kwargs["b"],
                "result": result,
            }
        elif tool_name == "power":
            result = kwargs["base"] ** kwargs["exponent"]
            return {
                "operation": "exponentiation",
                "base": kwargs["base"],
                "exponent": kwargs["exponent"],
                "result": result,
            }
        else:
            raise ValueError(f"Unknown tool: {tool_name}")


async def main() -> None:
    """Run custom plugin example."""
    # Initialize Odin
    app = Odin()
    await app.initialize()

    # Register custom calculator plugin
    calc_plugin = CalculatorPlugin()
    await app.register_plugin(calc_plugin)

    print("=== Custom Calculator Plugin Registered ===")
    print(f"Plugins: {app.list_plugins()}")
    print(f"\nAvailable tools: {[t['name'] for t in app.list_tools()]}")

    # Use the calculator tools
    print("\n=== Using Calculator Tools ===")

    result = await app.execute_tool("add", a=10, b=5)
    print(f"10 + 5 = {result['result']}")

    result = await app.execute_tool("multiply", a=7, b=6)
    print(f"7 * 6 = {result['result']}")

    result = await app.execute_tool("power", base=2, exponent=10)
    print(f"2^10 = {result['result']}")

    # Cleanup
    await app.shutdown()
    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
