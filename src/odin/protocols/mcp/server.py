"""MCP Server implementation for Odin framework."""

from typing import TYPE_CHECKING, Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent
from mcp.types import Tool as MCPTool

from odin.logging import get_logger

if TYPE_CHECKING:
    from odin.core.odin import Odin

logger = get_logger(__name__)


class MCPServer:
    """MCP (Model Context Protocol) Server for Odin framework.

    Exposes all registered tools as MCP tools that can be called by
    MCP-compatible clients (e.g., Claude Desktop, IDEs, etc.).

    Example:
        ```python
        from odin import Odin
        from odin.protocols.mcp import MCPServer

        app = Odin()
        await app.initialize()

        # Register your plugins...

        # Start MCP server
        mcp_server = MCPServer(app)
        await mcp_server.run()
        ```
    """

    def __init__(self, odin_app: Odin, name: str = "odin") -> None:
        """Initialize MCP server.

        Args:
            odin_app: Odin framework instance
            name: Server name for identification
        """
        self.odin_app = odin_app
        self.server = Server(name)
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Setup MCP request handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[MCPTool]:
            """List all available tools from Odin."""
            logger.info("MCP: Listing tools")

            tools = self.odin_app.list_tools()
            mcp_tools = []

            for tool in tools:
                # Convert Odin tool to MCP tool format
                input_schema = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }

                for param in tool["parameters"]:
                    input_schema["properties"][param["name"]] = {
                        "type": param["type"],
                        "description": param["description"],
                    }
                    if param["required"]:
                        input_schema["required"].append(param["name"])

                mcp_tool = MCPTool(
                    name=tool["name"],
                    description=tool["description"],
                    inputSchema=input_schema,
                )
                mcp_tools.append(mcp_tool)

            logger.info("MCP: Returning tools", count=len(mcp_tools))
            return mcp_tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Execute a tool and return results.

            Args:
                name: Tool name
                arguments: Tool arguments

            Returns:
                List of text content with results
            """
            logger.info("MCP: Calling tool", tool=name, arguments=arguments)

            try:
                result = await self.odin_app.execute_tool(name, **arguments)

                # Convert result to MCP response
                # MCP expects a list of TextContent
                import json

                result_text = json.dumps(result, indent=2, ensure_ascii=False)

                return [
                    TextContent(
                        type="text",
                        text=result_text,
                    )
                ]
            except Exception as e:
                logger.error("MCP: Tool execution failed", tool=name, error=str(e))

                # Return error as text content
                error_text = f"Error executing tool '{name}': {e!s}"
                return [
                    TextContent(
                        type="text",
                        text=error_text,
                    )
                ]

    async def run(self) -> None:
        """Run MCP server using stdio transport.

        This allows the server to be used with Claude Desktop and other
        MCP clients that communicate via stdin/stdout.
        """
        logger.info("Starting MCP server", name=self.server.name)

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

        # Create SSE endpoint
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

        # Create Starlette app
        app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
            ]
        )

        # Run with uvicorn
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
