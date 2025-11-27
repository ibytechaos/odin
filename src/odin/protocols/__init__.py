"""Protocol adapters for Odin framework.

Supports:
- MCP (Model Context Protocol) - Anthropic's standard
- A2A (Agent-to-Agent) - Multi-agent communication
- HTTP/REST - Web API
"""

from odin.protocols.mcp import MCPServer
from odin.protocols.http import create_http_app

__all__ = [
    "MCPServer",
    "create_http_app",
]
