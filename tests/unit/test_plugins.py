"""Tests for the plugin system."""

import pytest

from odin import DecoratorPlugin, tool
from odin.plugins import AgentPlugin, PluginManager, Tool, ToolParameter
from odin.plugins.base import ToolParameterType
from odin.errors import PluginError


class SimplePlugin(DecoratorPlugin):
    """A simple test plugin."""

    @property
    def name(self) -> str:
        return "simple"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "A simple test plugin"

    @tool(description="Say hello")
    async def say_hello(self, name: str = "World") -> dict:
        """Say hello to someone.

        Args:
            name: Name to greet
        """
        return {"message": f"Hello, {name}!"}

    @tool(description="Add two numbers")
    async def add(self, a: int, b: int) -> dict:
        """Add two numbers.

        Args:
            a: First number
            b: Second number
        """
        return {"result": a + b}


class TestDecoratorPlugin:
    """Test DecoratorPlugin base class."""

    @pytest.mark.asyncio
    async def test_get_tools(self):
        """Test that tools are auto-discovered."""
        plugin = SimplePlugin()
        tools = await plugin.get_tools()

        assert len(tools) == 2
        tool_names = {t.name for t in tools}
        assert "say_hello" in tool_names
        assert "add" in tool_names

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test tool execution."""
        plugin = SimplePlugin()

        result = await plugin.execute_tool("say_hello", name="Alice")
        assert result == {"message": "Hello, Alice!"}

        result = await plugin.execute_tool("add", a=5, b=3)
        assert result == {"result": 8}

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        """Test error on executing non-existent tool."""
        plugin = SimplePlugin()

        with pytest.raises(ValueError, match="not found"):
            await plugin.execute_tool("nonexistent")


class TestPluginManager:
    """Test PluginManager functionality."""

    @pytest.mark.asyncio
    async def test_register_plugin(self):
        """Test plugin registration."""
        manager = PluginManager()
        plugin = SimplePlugin()

        await manager.register_plugin(plugin)

        assert "simple" in [p["name"] for p in manager.list_plugins()]

    @pytest.mark.asyncio
    async def test_register_duplicate_plugin(self):
        """Test that registering duplicate plugin raises error."""
        manager = PluginManager()
        plugin1 = SimplePlugin()
        plugin2 = SimplePlugin()

        await manager.register_plugin(plugin1)

        with pytest.raises(PluginError):
            await manager.register_plugin(plugin2)

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing all tools."""
        manager = PluginManager()
        await manager.register_plugin(SimplePlugin())

        tools = manager.list_tools()
        assert len(tools) == 2

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test tool execution through manager."""
        manager = PluginManager()
        await manager.register_plugin(SimplePlugin())

        result = await manager.execute_tool("say_hello", name="Bob")
        assert result == {"message": "Hello, Bob!"}

    @pytest.mark.asyncio
    async def test_unregister_plugin(self):
        """Test plugin unregistration."""
        manager = PluginManager()
        await manager.register_plugin(SimplePlugin())

        await manager.unregister_plugin("simple")

        assert "simple" not in [p["name"] for p in manager.list_plugins()]
        assert len(manager.list_tools()) == 0

    @pytest.mark.asyncio
    async def test_get_plugin(self):
        """Test getting a specific plugin."""
        manager = PluginManager()
        plugin = SimplePlugin()
        await manager.register_plugin(plugin)

        retrieved = manager.get_plugin("simple")
        assert retrieved is plugin

    @pytest.mark.asyncio
    async def test_get_nonexistent_plugin(self):
        """Test error on getting non-existent plugin."""
        manager = PluginManager()

        with pytest.raises(PluginError):
            manager.get_plugin("nonexistent")
