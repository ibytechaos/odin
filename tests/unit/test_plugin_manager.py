"""Tests for the Plugin Manager."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from odin.plugins.manager import PluginManager
from odin.plugins.base import AgentPlugin, DecoratorPlugin, Tool, ToolParameter
from odin.decorators import tool
from odin.errors import PluginError, ExecutionError, ErrorCode


class SimplePlugin(DecoratorPlugin):
    """Simple plugin for testing."""

    name = "simple"
    version = "1.0.0"
    description = "A simple test plugin"

    @tool(description="Echo a message")
    async def echo(self, message: str) -> dict:
        """Echo the input message."""
        return {"echo": message}

    @tool(description="Add two numbers")
    async def add(self, a: int, b: int) -> dict:
        """Add two numbers together."""
        return {"result": a + b}


class DependentPlugin(DecoratorPlugin):
    """Plugin that depends on SimplePlugin."""

    name = "dependent"
    version = "1.0.0"
    dependencies = ["simple"]

    @tool(description="Use simple plugin")
    async def use_simple(self) -> dict:
        return {"status": "ok"}


class FailingInitPlugin(DecoratorPlugin):
    """Plugin that fails during initialization."""

    name = "failing_init"
    version = "1.0.0"

    async def initialize(self) -> None:
        raise RuntimeError("Init failed")

    @tool(description="A tool")
    async def some_tool(self) -> dict:
        return {}


class FailingToolPlugin(DecoratorPlugin):
    """Plugin with a tool that always fails."""

    name = "failing_tool"
    version = "1.0.0"

    @tool(description="Always fails")
    async def always_fails(self) -> dict:
        raise ValueError("Tool execution failed")


class TestPluginManager:
    """Test PluginManager basic functionality."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test plugin manager initialization."""
        pm = PluginManager()
        assert pm._plugins == {}
        assert pm._tools == {}

    @pytest.mark.asyncio
    async def test_register_plugin(self):
        """Test plugin registration."""
        pm = PluginManager()
        plugin = SimplePlugin()

        await pm.register_plugin(plugin)

        assert "simple" in pm._plugins
        assert pm._plugins["simple"] == plugin
        assert plugin.is_initialized()

    @pytest.mark.asyncio
    async def test_register_plugin_twice_raises(self):
        """Test that registering same plugin twice raises error."""
        pm = PluginManager()
        plugin = SimplePlugin()

        await pm.register_plugin(plugin)

        with pytest.raises(PluginError) as exc_info:
            await pm.register_plugin(plugin)

        assert exc_info.value.code == ErrorCode.PLUGIN_ALREADY_REGISTERED

    @pytest.mark.asyncio
    async def test_register_plugin_with_dependencies(self):
        """Test plugin with dependencies."""
        pm = PluginManager()

        # Register dependency first
        await pm.register_plugin(SimplePlugin())
        await pm.register_plugin(DependentPlugin())

        assert "simple" in pm._plugins
        assert "dependent" in pm._plugins

    @pytest.mark.asyncio
    async def test_register_plugin_missing_dependency(self):
        """Test plugin with missing dependency raises error."""
        pm = PluginManager()

        with pytest.raises(PluginError) as exc_info:
            await pm.register_plugin(DependentPlugin())

        assert exc_info.value.code == ErrorCode.PLUGIN_DEPENDENCY_MISSING

    @pytest.mark.asyncio
    async def test_register_plugin_init_failure(self):
        """Test plugin initialization failure."""
        pm = PluginManager()

        with pytest.raises(PluginError) as exc_info:
            await pm.register_plugin(FailingInitPlugin())

        assert exc_info.value.code == ErrorCode.PLUGIN_INIT_FAILED
        assert "failing_init" not in pm._plugins


class TestPluginManagerUnregister:
    """Test plugin unregistration."""

    @pytest.mark.asyncio
    async def test_unregister_plugin(self):
        """Test plugin unregistration."""
        pm = PluginManager()
        plugin = SimplePlugin()

        await pm.register_plugin(plugin)
        assert "simple" in pm._plugins

        await pm.unregister_plugin("simple")

        assert "simple" not in pm._plugins
        assert "echo" not in pm._tools
        assert "add" not in pm._tools

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_plugin(self):
        """Test unregistering nonexistent plugin raises error."""
        pm = PluginManager()

        with pytest.raises(PluginError) as exc_info:
            await pm.unregister_plugin("nonexistent")

        assert exc_info.value.code == ErrorCode.PLUGIN_NOT_FOUND

    @pytest.mark.asyncio
    async def test_unregister_plugin_shutdown_error(self):
        """Test that shutdown errors during unregister are handled."""
        pm = PluginManager()
        plugin = SimplePlugin()

        await pm.register_plugin(plugin)

        # Mock shutdown to raise error
        plugin.shutdown = AsyncMock(side_effect=RuntimeError("Shutdown failed"))

        # Should not raise, just log warning
        await pm.unregister_plugin("simple")

        assert "simple" not in pm._plugins


class TestPluginManagerTools:
    """Test tool-related methods."""

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing tools."""
        pm = PluginManager()
        await pm.register_plugin(SimplePlugin())

        tools = pm.list_tools()

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "echo" in tool_names
        assert "add" in tool_names

    @pytest.mark.asyncio
    async def test_get_tool(self):
        """Test getting a specific tool."""
        pm = PluginManager()
        await pm.register_plugin(SimplePlugin())

        tool = pm.get_tool("echo")

        assert tool.name == "echo"
        assert tool.description == "Echo a message"

    @pytest.mark.asyncio
    async def test_get_nonexistent_tool(self):
        """Test getting nonexistent tool raises error."""
        pm = PluginManager()

        with pytest.raises(ExecutionError) as exc_info:
            pm.get_tool("nonexistent")

        assert exc_info.value.code == ErrorCode.TOOL_NOT_FOUND

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test tool execution."""
        pm = PluginManager()
        await pm.register_plugin(SimplePlugin())

        result = await pm.execute_tool("echo", message="hello")

        assert result == {"echo": "hello"}

    @pytest.mark.asyncio
    async def test_execute_tool_with_multiple_params(self):
        """Test tool execution with multiple parameters."""
        pm = PluginManager()
        await pm.register_plugin(SimplePlugin())

        result = await pm.execute_tool("add", a=5, b=3)

        assert result == {"result": 8}

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        """Test executing nonexistent tool raises error."""
        pm = PluginManager()

        with pytest.raises(ExecutionError) as exc_info:
            await pm.execute_tool("nonexistent")

        assert exc_info.value.code == ErrorCode.TOOL_NOT_FOUND

    @pytest.mark.asyncio
    async def test_execute_tool_failure(self):
        """Test tool execution failure."""
        pm = PluginManager()
        await pm.register_plugin(FailingToolPlugin())

        with pytest.raises(ExecutionError) as exc_info:
            await pm.execute_tool("always_fails")

        assert exc_info.value.code == ErrorCode.TOOL_EXECUTION_FAILED


class TestPluginManagerGetPlugin:
    """Test get_plugin method."""

    @pytest.mark.asyncio
    async def test_get_plugin(self):
        """Test getting a registered plugin."""
        pm = PluginManager()
        plugin = SimplePlugin()

        await pm.register_plugin(plugin)

        retrieved = pm.get_plugin("simple")
        assert retrieved == plugin

    @pytest.mark.asyncio
    async def test_get_nonexistent_plugin(self):
        """Test getting nonexistent plugin raises error."""
        pm = PluginManager()

        with pytest.raises(PluginError) as exc_info:
            pm.get_plugin("nonexistent")

        assert exc_info.value.code == ErrorCode.PLUGIN_NOT_FOUND


class TestPluginManagerListPlugins:
    """Test list_plugins method."""

    @pytest.mark.asyncio
    async def test_list_plugins_empty(self):
        """Test listing plugins when none registered."""
        pm = PluginManager()

        plugins = pm.list_plugins()

        assert plugins == []

    @pytest.mark.asyncio
    async def test_list_plugins(self):
        """Test listing registered plugins."""
        pm = PluginManager()
        await pm.register_plugin(SimplePlugin())

        plugins = pm.list_plugins()

        assert len(plugins) == 1
        assert plugins[0]["name"] == "simple"
        assert plugins[0]["version"] == "1.0.0"
        assert plugins[0]["description"] == "A simple test plugin"
        assert plugins[0]["initialized"] is True
        assert plugins[0]["tools"] == 2


class TestPluginManagerShutdown:
    """Test shutdown functionality."""

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        """Test shutting down all plugins."""
        pm = PluginManager()
        await pm.register_plugin(SimplePlugin())

        assert len(pm._plugins) == 1

        await pm.shutdown_all()

        assert len(pm._plugins) == 0
        assert len(pm._tools) == 0

    @pytest.mark.asyncio
    async def test_shutdown_all_with_error(self):
        """Test shutdown all handles errors gracefully."""
        pm = PluginManager()
        plugin = SimplePlugin()
        await pm.register_plugin(plugin)

        # Mock unregister to raise error
        original_unregister = pm.unregister_plugin
        pm.unregister_plugin = AsyncMock(side_effect=RuntimeError("Unregister failed"))

        # Should not raise
        await pm.shutdown_all()


class TestPluginManagerToolConflict:
    """Test tool name conflict handling."""

    @pytest.mark.asyncio
    async def test_tool_name_conflict(self):
        """Test that tool name conflicts are handled with warning."""
        pm = PluginManager()

        # Create two plugins with same tool name
        class Plugin1(DecoratorPlugin):
            name = "plugin1"
            version = "1.0.0"

            @tool(description="Tool from plugin1")
            async def shared_tool(self) -> dict:
                return {"source": "plugin1"}

        class Plugin2(DecoratorPlugin):
            name = "plugin2"
            version = "1.0.0"

            @tool(description="Tool from plugin2")
            async def shared_tool(self) -> dict:
                return {"source": "plugin2"}

        await pm.register_plugin(Plugin1())
        await pm.register_plugin(Plugin2())

        # Second plugin should overwrite the tool
        result = await pm.execute_tool("shared_tool")
        assert result == {"source": "plugin2"}
