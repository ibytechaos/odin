"""Base protocol adapter interface for Odin framework.

All protocol adapters (MCP, A2A, AG-UI, CopilotKit, HTTP) must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from odin.logging import get_logger

if TYPE_CHECKING:
    from odin.core.agent_interface import IAgent

logger = get_logger(__name__)


class IProtocolAdapter(ABC):
    """Base interface for protocol adapters.

    Protocol adapters convert between Odin's unified agent interface (IAgent)
    and protocol-specific formats (MCP, A2A, AG-UI, CopilotKit, HTTP/REST).

    This allows business logic to be protocol-agnostic - write once, work with all protocols.

    Example:
        ```python
        class MyProtocolAdapter(IProtocolAdapter):
            def __init__(self, agent: IAgent):
                super().__init__(agent)

            def convert_tools(self) -> list:
                # Convert Odin tools to protocol format
                return [...]

            async def handle_request(self, request: Any) -> Any:
                # Handle protocol-specific request
                return response
        ```
    """

    def __init__(self, agent: IAgent):
        """Initialize protocol adapter.

        Args:
            agent: Unified agent instance
        """
        self.agent = agent
        logger.debug(
            "Protocol adapter initialized",
            adapter=self.__class__.__name__,
            agent=agent.name,
        )

    @abstractmethod
    def convert_tools(self) -> Any:
        """Convert Odin tools to protocol-specific format.

        Returns:
            Protocol-specific tool definitions

        Example:
            ```python
            # MCP adapter
            def convert_tools(self) -> list[MCPTool]:
                return [MCPTool(name=..., schema=...) for tool in self.agent.tools]

            # HTTP adapter
            def convert_tools(self) -> list[dict]:
                return [{"name": tool.name, "parameters": ...} for tool in ...]
            ```
        """
        pass

    @abstractmethod
    async def handle_request(self, request: Any) -> Any:
        """Handle protocol-specific request.

        Args:
            request: Protocol-specific request object

        Returns:
            Protocol-specific response object

        Example:
            ```python
            # FastAPI-based protocols
            async def handle_request(self, request: Request) -> Response:
                # Parse request
                # Call agent.execute()
                # Format response
                return response
            ```
        """
        pass

    def get_agent_metadata(self) -> dict:
        """Get agent metadata in protocol-agnostic format.

        Returns:
            Agent metadata dictionary
        """
        return self.agent.get_metadata()
