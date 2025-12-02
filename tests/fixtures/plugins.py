"""Plugin test fixtures and factories."""

from __future__ import annotations

from typing import Any

from odin.plugins.base import DecoratorPlugin, PluginConfig, Tool, ToolParameter, ParameterType
from odin.decorators import tool


def sample_tool_parameters() -> list[ToolParameter]:
    """Create sample tool parameters for testing."""
    return [
        ToolParameter(
            name="query",
            type=ParameterType.STRING,
            description="Search query",
            required=True,
        ),
        ToolParameter(
            name="limit",
            type=ParameterType.INTEGER,
            description="Max results",
            required=False,
            default=10,
        ),
        ToolParameter(
            name="include_metadata",
            type=ParameterType.BOOLEAN,
            description="Include metadata",
            required=False,
            default=False,
        ),
    ]


def create_test_tool(
    name: str = "test_tool",
    description: str = "A test tool",
    parameters: list[ToolParameter] | None = None,
) -> Tool:
    """Create a test tool for testing."""
    return Tool(
        name=name,
        description=description,
        parameters=parameters or sample_tool_parameters(),
    )


class SampleTestPlugin(DecoratorPlugin):
    """Sample plugin for testing."""

    name = "sample_test"
    version = "1.0.0"
    description = "A sample test plugin"

    @tool(description="Say hello to someone")
    async def say_hello(self, name: str = "World") -> dict[str, Any]:
        """Say hello.

        Args:
            name: Name to greet
        """
        return {"message": f"Hello, {name}!"}

    @tool(description="Add two numbers")
    async def add_numbers(self, a: int, b: int) -> dict[str, Any]:
        """Add two numbers.

        Args:
            a: First number
            b: Second number
        """
        return {"result": a + b}

    @tool(description="Search for items")
    async def search_items(
        self, query: str, limit: int = 10, include_metadata: bool = False
    ) -> dict[str, Any]:
        """Search for items.

        Args:
            query: Search query
            limit: Max results
            include_metadata: Include metadata
        """
        items = [{"id": i, "name": f"Item {i}"} for i in range(min(limit, 5))]
        if include_metadata:
            for item in items:
                item["metadata"] = {"created": "2024-01-01"}
        return {"items": items, "total": len(items)}


class FailingTestPlugin(DecoratorPlugin):
    """Plugin that raises errors for testing."""

    name = "failing_test"
    version = "1.0.0"
    description = "A plugin that fails for testing"

    @tool(description="Always fails")
    async def always_fails(self) -> dict[str, Any]:
        """This tool always fails."""
        raise ValueError("This tool always fails")

    @tool(description="Conditional failure")
    async def maybe_fails(self, should_fail: bool = False) -> dict[str, Any]:
        """May fail based on parameter.

        Args:
            should_fail: Whether to fail
        """
        if should_fail:
            raise RuntimeError("Conditional failure triggered")
        return {"success": True}


def create_test_plugin(
    name: str = "test_plugin",
    version: str = "1.0.0",
    description: str = "Test plugin",
) -> SampleTestPlugin:
    """Create a test plugin with specified metadata."""
    plugin = SampleTestPlugin()
    plugin.name = name
    plugin.version = version
    plugin.description = description
    return plugin
