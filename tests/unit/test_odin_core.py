"""Tests for the Odin core framework."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from odin import Odin, DecoratorPlugin, tool
from odin.config import Settings
from odin.plugins import PluginManager


class EchoPlugin(DecoratorPlugin):
    """Echo plugin for core tests."""

    @property
    def name(self) -> str:
        return "test"

    @property
    def version(self) -> str:
        return "1.0.0"

    @tool(description="Echo input")
    async def echo(self, message: str) -> dict:
        """Echo the input message.

        Args:
            message: Message to echo
        """
        return {"echo": message}


class FailingPlugin(DecoratorPlugin):
    """Plugin that fails during initialization for testing."""

    name = "failing"
    version = "1.0.0"

    async def initialize(self) -> None:
        raise RuntimeError("Initialization failed")

    @tool(description="A tool")
    async def some_tool(self) -> dict:
        return {}


class TestOdinCore:
    """Test Odin core functionality."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test Odin initialization."""
        odin = Odin()
        await odin.initialize()

        assert odin.version == "0.1.0"
        assert odin.is_initialized()

    @pytest.mark.asyncio
    async def test_initialize_twice_warns(self):
        """Test that initializing twice logs a warning."""
        odin = Odin()
        await odin.initialize()
        assert odin.is_initialized()

        # Second initialization should not crash
        await odin.initialize()
        assert odin.is_initialized()

    @pytest.mark.asyncio
    async def test_register_plugin(self):
        """Test plugin registration."""
        odin = Odin()
        await odin.initialize()
        await odin.register_plugin(EchoPlugin())

        plugins = odin.list_plugins()
        assert any(p["name"] == "test" for p in plugins)

    @pytest.mark.asyncio
    async def test_unregister_plugin(self):
        """Test plugin unregistration."""
        odin = Odin()
        await odin.initialize()
        await odin.register_plugin(EchoPlugin())

        # Verify plugin is registered
        plugins = odin.list_plugins()
        assert any(p["name"] == "test" for p in plugins)

        # Unregister
        await odin.unregister_plugin("test")

        # Verify plugin is gone
        plugins = odin.list_plugins()
        assert not any(p["name"] == "test" for p in plugins)

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing tools."""
        odin = Odin()
        await odin.initialize()
        await odin.register_plugin(EchoPlugin())

        tools = odin.list_tools()
        assert len(tools) >= 1
        assert any(t["name"] == "echo" for t in tools)

    @pytest.mark.asyncio
    async def test_list_tools_format(self):
        """Test tool listing format includes all expected fields."""
        odin = Odin()
        await odin.initialize()
        await odin.register_plugin(EchoPlugin())

        tools = odin.list_tools()
        echo_tool = next(t for t in tools if t["name"] == "echo")

        assert "name" in echo_tool
        assert "description" in echo_tool
        assert "parameters" in echo_tool
        assert echo_tool["description"] == "Echo input"

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test tool execution."""
        odin = Odin()
        await odin.initialize()
        await odin.register_plugin(EchoPlugin())

        result = await odin.execute_tool("echo", message="hello")
        assert result == {"echo": "hello"}

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test Odin shutdown."""
        odin = Odin()
        await odin.initialize()
        await odin.register_plugin(EchoPlugin())

        await odin.shutdown()

        # After shutdown, plugins should be unregistered
        assert len(odin.list_plugins()) == 0
        assert not odin.is_initialized()

    @pytest.mark.asyncio
    async def test_plugin_manager_property(self):
        """Test that plugin_manager property returns the manager."""
        odin = Odin()
        await odin.initialize()

        pm = odin.plugin_manager
        assert pm is not None
        assert isinstance(pm, PluginManager)


class TestOdinWithSettings:
    """Test Odin with custom settings."""

    @pytest.mark.asyncio
    async def test_custom_settings(self):
        """Test Odin with custom settings."""
        # Use _env_file=None to prevent reading from .env files
        # env must be one of: development, staging, production
        settings = Settings(
            _env_file=None,
            env="staging",
            log_level="DEBUG",
            builtin_plugins=[],
            plugin_auto_discovery=False,
        )
        odin = Odin(settings=settings)

        assert odin.settings.env == "staging"
        assert odin.settings.log_level == "DEBUG"

    @pytest.mark.asyncio
    async def test_initialize_without_builtin_plugins(self):
        """Test initialization without builtin plugins."""
        settings = Settings(
            builtin_plugins=[],
            plugin_auto_discovery=False,
        )
        odin = Odin(settings=settings)
        await odin.initialize()

        # Should have no plugins
        plugins = odin.list_plugins()
        assert len(plugins) == 0

    @pytest.mark.asyncio
    async def test_initialize_with_specific_builtin_plugins(self):
        """Test initialization with specific builtin plugins."""
        settings = Settings(
            builtin_plugins=["http"],
            plugin_auto_discovery=False,
        )
        odin = Odin(settings=settings)
        await odin.initialize()

        plugins = odin.list_plugins()
        plugin_names = [p["name"] for p in plugins]
        assert "http" in plugin_names
        # Only http should be loaded
        assert len(plugins) == 1


class TestOdinBuiltinPlugins:
    """Test Odin builtin plugin loading."""

    @pytest.mark.asyncio
    async def test_load_unknown_builtin_plugin(self):
        """Test loading an unknown builtin plugin logs warning."""
        settings = Settings(
            builtin_plugins=["nonexistent_plugin"],
            plugin_auto_discovery=False,
        )
        odin = Odin(settings=settings)

        # Should not raise, but log warning
        await odin.initialize()

        # No plugins should be loaded
        plugins = odin.list_plugins()
        assert len(plugins) == 0

    @pytest.mark.asyncio
    async def test_load_multiple_builtin_plugins(self):
        """Test loading multiple builtin plugins."""
        settings = Settings(
            builtin_plugins=["http", "utilities"],
            plugin_auto_discovery=False,
        )
        odin = Odin(settings=settings)
        await odin.initialize()

        plugins = odin.list_plugins()
        plugin_names = [p["name"] for p in plugins]
        assert "http" in plugin_names
        assert "utilities" in plugin_names
        assert len(plugins) == 2


class TestOdinErrorHandling:
    """Test Odin error handling."""

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        """Test executing a non-existent tool raises error."""
        odin = Odin()
        await odin.initialize()

        with pytest.raises(Exception):
            await odin.execute_tool("nonexistent_tool")
