"""MCP Streamable HTTP transport implementation.

This module provides MCP server support using the Streamable HTTP transport
(protocol version 2025-03-26), which supersedes the SSE transport.

Streamable HTTP enables:
- Single endpoint for all communication
- Bi-directional messaging
- Better scalability for production deployments

Example:
    ```python
    from odin import Odin
    from odin.protocols.mcp.streamable_http import MCPStreamableHTTP

    odin = Odin()
    await odin.initialize()

    mcp = MCPStreamableHTTP(odin)
    app.mount("/mcp", mcp.get_app())
    ```
"""

import json
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from odin.logging import get_logger

if TYPE_CHECKING:
    from odin.core.odin import Odin

logger = get_logger(__name__)

# JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class MCPStreamableHTTP:
    """MCP Server using Streamable HTTP transport.

    Implements the MCP Streamable HTTP transport specification (2025-03-26).
    All communication happens through a single HTTP endpoint that accepts
    JSON-RPC 2.0 messages.

    Supported methods:
        - initialize: Initialize the MCP session
        - tools/list: List available tools
        - tools/call: Execute a tool
        - ping: Health check
    """

    def __init__(
        self,
        odin: Odin,
        *,
        name: str = "odin-mcp",
        version: str = "0.1.0",
    ):
        """Initialize MCP Streamable HTTP server.

        Args:
            odin: Odin framework instance
            name: Server name
            version: Server version
        """
        self.odin = odin
        self.name = name
        self.version = version
        self.app = FastAPI(title=f"{name} MCP Server")
        self._setup_routes()

        # Session state (for stateful mode)
        self._initialized = False
        self._client_info: dict[str, Any] = {}

    def _setup_routes(self) -> None:
        """Setup MCP HTTP routes."""

        @self.app.post("/")
        async def handle_message(request: Request):
            """Handle MCP JSON-RPC messages.

            This is the main endpoint for all MCP communication.
            Accepts JSON-RPC 2.0 requests and returns responses.
            """
            try:
                body = await request.json()
            except Exception:
                return self._error_response(None, PARSE_ERROR, "Parse error")

            # Handle batch requests
            if isinstance(body, list):
                responses = []
                for msg in body:
                    resp = await self._handle_single_message(msg)
                    if resp is not None:  # Don't include responses to notifications
                        responses.append(resp)
                return JSONResponse(responses)

            # Handle single request
            response = await self._handle_single_message(body)
            if response is None:
                # Notification - no response
                return JSONResponse(content=None, status_code=204)
            return JSONResponse(response)

        @self.app.get("/")
        async def handle_sse(request: Request):  # noqa: ARG001
            """Handle SSE connections for server-initiated messages.

            This endpoint is used by clients that want to receive
            server-initiated notifications and requests.
            """

            async def event_stream():
                # For now, just keep the connection alive
                # In a full implementation, this would stream server events
                import asyncio

                while True:
                    # Send keepalive
                    yield f"event: ping\ndata: {{}}\n\n"
                    await asyncio.sleep(30)

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        @self.app.delete("/")
        async def handle_disconnect():
            """Handle session disconnect."""
            self._initialized = False
            self._client_info = {}
            return JSONResponse({"status": "disconnected"})

    async def _handle_single_message(self, msg: dict) -> dict | None:
        """Handle a single JSON-RPC message.

        Args:
            msg: JSON-RPC message

        Returns:
            JSON-RPC response or None for notifications
        """
        # Validate JSON-RPC structure
        if not isinstance(msg, dict):
            return self._error_response(None, INVALID_REQUEST, "Invalid request")

        jsonrpc = msg.get("jsonrpc")
        if jsonrpc != "2.0":
            return self._error_response(None, INVALID_REQUEST, "Invalid JSON-RPC version")

        method = msg.get("method")
        if not method:
            return self._error_response(None, INVALID_REQUEST, "Missing method")

        msg_id = msg.get("id")
        params = msg.get("params", {})

        # Handle notification (no id)
        is_notification = msg_id is None

        try:
            result = await self._dispatch_method(method, params)
            if is_notification:
                return None
            return self._success_response(msg_id, result)
        except MethodNotFoundError:
            return self._error_response(msg_id, METHOD_NOT_FOUND, f"Method not found: {method}")
        except InvalidParamsError as e:
            return self._error_response(msg_id, INVALID_PARAMS, str(e))
        except Exception as e:
            logger.error("MCP method error", method=method, error=str(e))
            return self._error_response(msg_id, INTERNAL_ERROR, str(e))

    async def _dispatch_method(self, method: str, params: dict) -> Any:
        """Dispatch a method call to the appropriate handler.

        Args:
            method: Method name
            params: Method parameters

        Returns:
            Method result
        """
        handlers = {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "ping": self._handle_ping,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
        }

        handler = handlers.get(method)
        if handler is None:
            raise MethodNotFoundError(f"Unknown method: {method}")

        return await handler(params)

    async def _handle_initialize(self, params: dict) -> dict:
        """Handle initialize request."""
        self._client_info = params.get("clientInfo", {})

        logger.info(
            "MCP client initialized",
            client=self._client_info.get("name", "unknown"),
            version=self._client_info.get("version", "unknown"),
        )

        # Return server capabilities
        return {
            "protocolVersion": "2025-03-26",
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
        }

    async def _handle_initialized(self, params: dict) -> dict:  # noqa: ARG002
        """Handle initialized notification."""
        self._initialized = True
        logger.info("MCP session initialized")
        return {}

    async def _handle_ping(self, params: dict) -> dict:  # noqa: ARG002
        """Handle ping request."""
        return {}

    async def _handle_tools_list(self, params: dict) -> dict:  # noqa: ARG002
        """Handle tools/list request."""
        tools = self.odin.list_tools()
        mcp_tools = []

        for tool in tools:
            # Convert to MCP tool format
            input_schema: dict[str, Any] = {
                "type": "object",
                "properties": {},
                "required": [],
            }

            for param in tool.get("parameters", []):
                input_schema["properties"][param["name"]] = {
                    "type": param.get("type", "string"),
                    "description": param.get("description", ""),
                }
                if param.get("required", False):
                    input_schema["required"].append(param["name"])

            mcp_tools.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "inputSchema": input_schema,
            })

        logger.debug("MCP tools list", count=len(mcp_tools))
        return {"tools": mcp_tools}

    async def _handle_tools_call(self, params: dict) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name")
        if not tool_name:
            raise InvalidParamsError("Missing tool name")

        arguments = params.get("arguments", {})

        logger.info("MCP tool call", tool=tool_name, arguments=arguments)

        try:
            result = await self.odin.execute_tool(tool_name, **arguments)

            # Convert result to MCP content format
            if isinstance(result, str):
                content = [{"type": "text", "text": result}]
            else:
                content = [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]

            return {"content": content, "isError": False}

        except Exception as e:
            logger.error("MCP tool call failed", tool=tool_name, error=str(e))
            return {
                "content": [{"type": "text", "text": f"Error: {e!s}"}],
                "isError": True,
            }

    async def _handle_resources_list(self, params: dict) -> dict:  # noqa: ARG002
        """Handle resources/list request."""
        # Odin doesn't have resources concept yet
        return {"resources": []}

    async def _handle_resources_read(self, params: dict) -> dict:
        """Handle resources/read request."""
        uri = params.get("uri")
        raise InvalidParamsError(f"Resource not found: {uri}")

    async def _handle_prompts_list(self, params: dict) -> dict:  # noqa: ARG002
        """Handle prompts/list request."""
        # Odin doesn't have prompts concept yet
        return {"prompts": []}

    async def _handle_prompts_get(self, params: dict) -> dict:
        """Handle prompts/get request."""
        name = params.get("name")
        raise InvalidParamsError(f"Prompt not found: {name}")

    def _success_response(self, msg_id: Any, result: Any) -> dict:
        """Create a success response."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        }

    def _error_response(self, msg_id: Any, code: int, message: str) -> dict:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    def get_app(self) -> FastAPI:
        """Get the FastAPI application.

        Returns:
            FastAPI application for mounting
        """
        return self.app


class MethodNotFoundError(Exception):
    """Raised when a method is not found."""

    pass


class InvalidParamsError(Exception):
    """Raised when parameters are invalid."""

    pass
