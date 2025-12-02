"""MCP Protocol Adapter for Odin framework.

This adapter implements the IProtocolAdapter interface for MCP (Model Context Protocol),
enabling protocol-agnostic development.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent
from mcp.types import Tool as MCPTool

from odin.logging import get_logger
from odin.protocols.base_adapter import IProtocolAdapter

if TYPE_CHECKING:
    from odin.core.agent_interface import IAgent

logger = get_logger(__name__)


class MCPAdapter(IProtocolAdapter):
    """MCP (Model Context Protocol) Adapter.

    Implements IProtocolAdapter interface for MCP protocol.
    Exposes all registered tools as MCP tools that can be called by
    MCP-compatible clients (e.g., Claude Desktop, IDEs, etc.).

    Example:
        ```python
        from odin.core.agent_factory import AgentFactory
        from odin.protocols.mcp import MCPAdapter

        # Create agent
        agent = AgentFactory.create_agent()

        # Create MCP adapter
        adapter = MCPAdapter(agent)

        # Run MCP server
        await adapter.run()
        ```
    """

    def __init__(self, agent: IAgent, name: str = "odin") -> None:
        """Initialize MCP adapter.

        Args:
            agent: Unified agent instance
            name: Server name for identification
        """
        super().__init__(agent)
        self._name = name
        self.server = Server(name)
        self._setup_handlers()

    def convert_tools(self) -> list[MCPTool]:
        """Convert Odin tools to MCP tool format.

        Returns:
            List of MCP Tool objects
        """
        metadata = self.agent.get_metadata()
        tool_names = metadata.get("tools", [])

        mcp_tools = []
        for tool_name in tool_names:
            # Basic tool conversion - agent should provide more details
            input_schema = {
                "type": "object",
                "properties": {},
                "required": [],
            }

            mcp_tool = MCPTool(
                name=tool_name,
                description=f"Tool: {tool_name}",
                inputSchema=input_schema,
            )
            mcp_tools.append(mcp_tool)

        return mcp_tools

    async def handle_request(self, request: Any) -> Any:
        """Handle MCP request.

        For MCP, requests are handled through the server handlers.
        This method is primarily for ProtocolDispatcher integration.

        Args:
            request: MCP request (tool call or list tools)

        Returns:
            MCP response
        """
        # MCP uses its own request/response handling via server handlers
        # This is mainly for compatibility with the interface
        if hasattr(request, "method"):
            if request.method == "list_tools":
                return self.convert_tools()
            elif request.method == "call_tool":
                return await self._execute_tool(
                    request.params.get("name"),
                    request.params.get("arguments", {})
                )
        return None

    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute a tool and return results.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            List of TextContent with results
        """
        logger.info("MCP: Calling tool", tool=name, arguments=arguments)

        try:
            # Execute through agent
            events = []
            async for event in self.agent.execute(
                input=f"Execute tool {name} with arguments: {json.dumps(arguments)}",
                thread_id="mcp-tool-execution",
            ):
                events.append(event)

            # Extract result from events
            result = None
            for event in events:
                if event.get("type") == "message":
                    result = event.get("content")
                    break

            result_text = json.dumps(result, indent=2, ensure_ascii=False) if result else "Tool executed successfully"

            return [
                TextContent(
                    type="text",
                    text=result_text,
                )
            ]
        except Exception as e:
            logger.error("MCP: Tool execution failed", tool=name, error=str(e))

            error_text = f"Error executing tool '{name}': {e!s}"
            return [
                TextContent(
                    type="text",
                    text=error_text,
                )
            ]

    def _setup_handlers(self) -> None:
        """Setup MCP request handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[MCPTool]:
            """List all available tools."""
            logger.info("MCP: Listing tools")
            mcp_tools = self.convert_tools()
            logger.info("MCP: Returning tools", count=len(mcp_tools))
            return mcp_tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Execute a tool and return results."""
            return await self._execute_tool(name, arguments)

    async def run(self) -> None:
        """Run MCP server using stdio transport.

        This allows the server to be used with Claude Desktop and other
        MCP clients that communicate via stdin/stdout.
        """
        logger.info("Starting MCP server", name=self._name)

        try:
            async with stdio_server() as (read_stream, write_stream):
                logger.info("MCP server running on stdio")
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
        except Exception as e:
            logger.error("MCP server error", error=str(e))
            raise

    async def run_sse(self, host: str = "localhost", port: int = 8000) -> None:
        """Run MCP server using SSE (Server-Sent Events) transport.

        This provides an HTTP endpoint for web-based clients.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        logger.info("Starting MCP server (SSE)", host=host, port=port)

        from mcp.server.sse import sse_server
        from starlette.applications import Starlette
        from starlette.routing import Route

        sse = sse_server()

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,
            ) as streams:
                await self.server.run(
                    streams[0],
                    streams[1],
                    self.server.create_initialization_options(),
                )

        app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
            ]
        )

        import uvicorn

        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        try:
            await server.serve()
        except Exception as e:
            logger.error("MCP SSE server error", error=str(e))
            raise
