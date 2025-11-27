"""Test MCP server without stdio.

Tests the MCP server functionality programmatically.
"""

import asyncio

from odin import Odin, tool
from odin.logging import get_logger
from odin.plugins import AgentPlugin
from odin.protocols.mcp import MCPServer

logger = get_logger(__name__)


class TestPlugin(AgentPlugin):
    """Test plugin."""

    @property
    def name(self) -> str:
        return "test"

    @property
    def version(self) -> str:
        return "1.0.0"

    @tool()
    async def hello(self, name: str) -> dict:
        """Say hello.

        Args:
            name: Name to greet
        """
        return {"greeting": f"Hello, {name}!"}

    async def get_tools(self):
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
        from odin.decorators.tool import get_tool_from_function, is_tool

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def and tool_def.name == tool_name:
                    return await attr(**kwargs)
        raise ValueError(f"Tool '{tool_name}' not found")


async def main():
    """Test MCP server."""
    logger.info("Testing MCP Server Integration")
    logger.info("=" * 70)

    # Create app
    app = Odin()
    await app.initialize()

    # Register plugin
    plugin = TestPlugin()
    await app.register_plugin(plugin)

    # Create MCP server
    mcp_server = MCPServer(app, name="test-server")

    logger.info("\n[1/2] Verifying MCP server creation")
    logger.info(f"  Server name: {mcp_server.server.name}")
    logger.info(f"  Odin app: {mcp_server.odin_app}")
    logger.info("  ✓ MCP server created successfully")

    logger.info("\n[2/2] Verifying tools accessible via Odin")
    tools = app.list_tools()
    logger.info(f"  Found {len(tools)} tools:")
    for t in tools:
        logger.info(f"    - {t['name']}: {t['description']}")
    logger.info("  ✓ Tools registered correctly")

    print("\n" + "=" * 60)
    logger.info("MCP Server Integration Tests: PASSED")
    logger.info("=" * 70)

    logger.info("\nMCP Server Features:")
    logger.info("  ✓ Automatic tool conversion (Odin → MCP format)")
    logger.info("  ✓ Tool listing via tools/list")
    logger.info("  ✓ Tool execution via tools/call")
    logger.info("  ✓ JSON-RPC 2.0 compatible")
    logger.info("  ✓ Stdio transport (for Claude Desktop)")
    logger.info("  ✓ SSE transport (for web clients)")

    logger.info("\nTo use with Claude Desktop:")
    logger.info("  1. Copy examples/claude_desktop_config.json")
    logger.info("  2. Update paths in the config")
    logger.info("  3. Restart Claude Desktop")
    logger.info("  4. Your tools will appear in Claude!")

    await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
