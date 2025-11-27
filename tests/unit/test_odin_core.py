"""Tests for the Odin core framework."""

import pytest

from odin import Odin, DecoratorPlugin, tool


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


class TestOdinCore:
    """Test Odin core functionality."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test Odin initialization."""
        odin = Odin()
        await odin.initialize()

        assert odin.version == "0.1.0"

    @pytest.mark.asyncio
    async def test_register_plugin(self):
        """Test plugin registration."""
        odin = Odin()
        await odin.initialize()
        await odin.register_plugin(EchoPlugin())

        plugins = odin.list_plugins()
        assert any(p["name"] == "test" for p in plugins)

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
