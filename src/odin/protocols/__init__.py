"""Protocol adapters for Odin framework.

Supports:
- MCP (Model Context Protocol) - Anthropic's standard
- A2A (Agent-to-Agent) - Multi-agent communication
- HTTP/REST - Web API
- AG-UI (Agent-User Interaction) - CopilotKit protocol
- CopilotKit - CopilotKit integration
"""

from odin.protocols.mcp import MCPServer
from odin.protocols.http import HTTPServer

__all__ = [
    "MCPServer",
    "HTTPServer",
]
