"""Protocol dispatcher for automatic protocol detection and routing."""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from odin.logging import get_logger

if TYPE_CHECKING:
    from fastapi import Request

    from odin.core.agent_interface import IAgent
    from odin.protocols.base_adapter import IProtocolAdapter

logger = get_logger(__name__)


class ProtocolType(Enum):
    """Supported protocol types."""

    MCP = "mcp"
    A2A = "a2a"
    AGUI = "agui"
    COPILOTKIT = "copilotkit"
    HTTP = "http"


class ProtocolDispatcher:
    """Protocol dispatcher for automatic protocol detection and routing.

    This dispatcher automatically detects the protocol type from incoming requests
    and routes them to the appropriate protocol adapter.

    This enables protocol-agnostic development - business code doesn't need to know
    which protocol is being used.

    Example:
        ```python
        from odin.core.agent_factory import create_agent
        from odin.protocols.protocol_dispatcher import ProtocolDispatcher

        # Create agent
        agent = create_agent()

        # Create dispatcher
        dispatcher = ProtocolDispatcher(agent)

        # Use in FastAPI
        @app.post("/agent")
        async def unified_endpoint(request: Request):
            return await dispatcher.dispatch(request)
        ```
    """

    def __init__(self, agent: IAgent):
        """Initialize protocol dispatcher.

        Args:
            agent: Unified agent instance
        """
        self.agent = agent
        self._adapters: dict[ProtocolType, IProtocolAdapter] = {}

        # Lazy-load adapters on first use
        logger.info(
            "Protocol dispatcher initialized",
            agent=agent.name,
        )

    def _get_adapter(self, protocol: ProtocolType) -> IProtocolAdapter:
        """Get or create protocol adapter.

        Args:
            protocol: Protocol type

        Returns:
            Protocol adapter instance
        """
        if protocol in self._adapters:
            return self._adapters[protocol]

        # Lazy-load adapter
        logger.debug("Loading protocol adapter", protocol=protocol.value)

        if protocol == ProtocolType.MCP:
            from odin.protocols.mcp.adapter import MCPAdapter

            adapter = MCPAdapter(self.agent)

        elif protocol == ProtocolType.A2A:
            from odin.protocols.a2a.adapter import A2AAdapter

            adapter = A2AAdapter(self.agent)

        elif protocol == ProtocolType.AGUI:
            from odin.protocols.agui.adapter import AGUIAdapter

            adapter = AGUIAdapter(self.agent)

        elif protocol == ProtocolType.COPILOTKIT:
            from odin.protocols.copilotkit.adapter_v2 import CopilotKitAdapter

            adapter = CopilotKitAdapter(self.agent)

        elif protocol == ProtocolType.HTTP:
            from odin.protocols.http.adapter import HTTPAdapter

            adapter = HTTPAdapter(self.agent)

        else:
            raise ValueError(f"Unknown protocol type: {protocol}")

        self._adapters[protocol] = adapter
        logger.info("Protocol adapter loaded", protocol=protocol.value)

        return adapter

    @staticmethod
    async def detect_protocol(request: Request) -> ProtocolType:
        """Automatically detect protocol type from request.

        Detection logic:
        1. CopilotKit: GraphQL query in JSON body with "copilot" keyword
        2. AG-UI: Accept header contains "text/event-stream"
        3. A2A: URL path starts with "/.well-known/agent-card" or "/message"
        4. MCP: Not applicable (uses stdio, not HTTP)
        5. HTTP: Default fallback for REST API

        Args:
            request: FastAPI Request object

        Returns:
            Detected protocol type
        """
        # Check URL path first (most specific)
        path = request.url.path

        # A2A: Well-known endpoints
        if path.startswith("/.well-known/agent-card"):
            logger.debug("Protocol detected: A2A (agent-card)")
            return ProtocolType.A2A

        if path.startswith("/message/send"):
            logger.debug("Protocol detected: A2A (message)")
            return ProtocolType.A2A

        # Check Content-Type and body
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            try:
                # Try to parse body
                body = await request.json()

                # CopilotKit: GraphQL request
                if isinstance(body, dict) and "query" in body:
                    query = body.get("query", "").lower()
                    if "copilot" in query or "agent" in query:
                        logger.debug("Protocol detected: CopilotKit (GraphQL)")
                        return ProtocolType.COPILOTKIT

            except Exception:
                # If body parsing fails, continue to other checks
                pass

        # Check Accept header
        accept = request.headers.get("accept", "")

        # AG-UI: Server-Sent Events
        if "text/event-stream" in accept:
            logger.debug("Protocol detected: AG-UI (SSE)")
            return ProtocolType.AGUI

        # Default: HTTP/REST
        logger.debug("Protocol detected: HTTP (default)")
        return ProtocolType.HTTP

    async def dispatch(self, request: Request) -> Any:
        """Dispatch request to appropriate protocol adapter.

        Args:
            request: FastAPI Request object

        Returns:
            Protocol-specific response
        """
        # Detect protocol
        protocol = await self.detect_protocol(request)

        logger.info(
            "Dispatching request",
            protocol=protocol.value,
            path=request.url.path,
            method=request.method,
        )

        # Get adapter
        adapter = self._get_adapter(protocol)

        # Handle request
        return await adapter.handle_request(request)

    def get_adapter(self, protocol: ProtocolType) -> IProtocolAdapter:
        """Get protocol adapter (create if not exists).

        This is useful for manual protocol mounting in FastAPI.

        Args:
            protocol: Protocol type

        Returns:
            Protocol adapter instance

        Example:
            ```python
            # Get CopilotKit adapter and mount manually
            copilot_adapter = dispatcher.get_adapter(ProtocolType.COPILOTKIT)
            copilot_adapter.mount(app, "/copilotkit")
            ```
        """
        return self._get_adapter(protocol)

    @property
    def adapters(self) -> dict[ProtocolType, IProtocolAdapter]:
        """Get all loaded adapters.

        Returns:
            Dictionary of protocol type to adapter
        """
        return self._adapters
