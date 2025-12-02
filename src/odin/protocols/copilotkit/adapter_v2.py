"""CopilotKit adapter v2 - Protocol-agnostic version using IAgent interface.

This new adapter supports multiple agent backends (CrewAI, LangGraph) through
the unified IAgent interface.
"""

from typing import TYPE_CHECKING, Any

from odin.logging import get_logger
from odin.protocols.base_adapter import IProtocolAdapter

if TYPE_CHECKING:
    from fastapi import FastAPI

    from odin.core.agent_interface import IAgent

logger = get_logger(__name__)


class CopilotKitAdapter(IProtocolAdapter):
    """CopilotKit protocol adapter.

    This adapter supports multiple agent backends:
    - CrewAI: Uses official copilotkit.crewai.CrewAIAgent
    - LangGraph: Uses custom OdinLangGraphAgent wrapper
    - Custom: Falls back to Actions-only mode

    Example:
        ```python
        from odin.core.agent_factory import create_agent
        from odin.protocols.copilotkit.adapter_v2 import CopilotKitAdapter

        # Create agent (CrewAI by default)
        agent = create_agent()

        # Create adapter
        adapter = CopilotKitAdapter(agent)

        # Mount to FastAPI
        adapter.mount(app, "/copilotkit")
        ```
    """

    def __init__(self, agent: IAgent):
        """Initialize CopilotKit adapter.

        Args:
            agent: Unified agent instance
        """
        super().__init__(agent)
        self._sdk = None
        self._actions = []

    def convert_tools(self) -> list:
        """Convert Odin tools to CopilotKit Actions.

        Returns:
            List of CopilotKit Action objects
        """
        try:
            from copilotkit import Action as CopilotAction  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "copilotkit package is required. Install with: pip install copilotkit"
            ) from e

        if self._actions:
            return self._actions

        # Get agent metadata to access tools
        metadata = self.agent.get_metadata()
        tool_names = metadata.get("tools", [])

        logger.info(
            "Converting tools to CopilotKit actions",
            tool_count=len(tool_names),
            agent=self.agent.name,
        )

        # TODO: Get actual Tool objects
        # For now, we'll create placeholder actions
        # This should be improved to get actual tools from agent

        self._actions = []
        logger.debug("CopilotKit actions created", action_count=len(self._actions))

        return self._actions

    def get_sdk(self):
        """Get CopilotKit SDK instance.

        This method creates the appropriate CopilotKit SDK based on agent backend type.

        Returns:
            CopilotKitRemoteEndpoint instance
        """
        if self._sdk is not None:
            return self._sdk

        try:
            from copilotkit import CopilotKitRemoteEndpoint
        except ImportError as e:
            raise ImportError(
                "copilotkit package is required. Install with: pip install copilotkit"
            ) from e

        logger.info(
            "Creating CopilotKit SDK",
            agent=self.agent.name,
            agent_type=self.agent.get_metadata().get("type"),
        )

        # Check agent backend type
        agent_type = self.agent.get_metadata().get("type")

        if agent_type == "crewai":
            # Use official CrewAI integration
            logger.info("Using official CopilotKit CrewAI integration")

            # Import CrewAI backend
            from odin.core.agent_backends.crewai_backend import CrewAIAgentBackend

            if isinstance(self.agent, CrewAIAgentBackend):
                # Get CopilotKit-wrapped agent
                crewai_agent = self.agent.get_copilotkit_agent()

                self._sdk = CopilotKitRemoteEndpoint(
                    agents=[crewai_agent],
                    actions=self.convert_tools(),  # Actions still work alongside agents
                )

                logger.info(
                    "CopilotKit SDK created with CrewAI agent",
                    agent_name=self.agent.name,
                )
            else:
                logger.warning(
                    "Agent type is crewai but instance is not CrewAIAgentBackend. "
                    "Falling back to actions-only mode."
                )
                self._sdk = CopilotKitRemoteEndpoint(
                    actions=self.convert_tools()
                )

        elif agent_type == "langgraph":
            # Use LangGraph integration (existing implementation)
            logger.info("Using LangGraph integration")

            # TODO: Implement LangGraphAgentBackend
            logger.warning("LangGraph backend not yet implemented. Using actions-only mode.")
            self._sdk = CopilotKitRemoteEndpoint(
                actions=self.convert_tools()
            )

        else:
            # Custom or unknown agent: use actions-only mode
            logger.info(
                "Using actions-only mode for custom agent",
                agent_type=agent_type,
            )
            self._sdk = CopilotKitRemoteEndpoint(
                actions=self.convert_tools()
            )

        return self._sdk

    async def handle_request(self, request: Any) -> Any:
        """Handle CopilotKit GraphQL request.

        Args:
            request: FastAPI Request object

        Returns:
            GraphQL response
        """
        logger.debug(
            "Handling CopilotKit request",
            path=request.url.path,
            method=request.method,
        )

        # CopilotKit SDK handles the actual request processing
        sdk = self.get_sdk()

        # This will be handled by the mounted FastAPI endpoint
        # The actual GraphQL handling is done by CopilotKit's FastAPI integration
        return await sdk.handle_request(request)

    def mount(self, app: FastAPI, path: str = "/copilotkit"):
        """Mount CopilotKit endpoints on FastAPI app.

        Args:
            app: FastAPI application
            path: Endpoint path (default: "/copilotkit")
        """
        try:
            from copilotkit.integrations.fastapi import add_fastapi_endpoint
        except ImportError as e:
            raise ImportError(
                "copilotkit package is required. Install with: pip install copilotkit"
            ) from e

        logger.info(
            "Mounting CopilotKit endpoint",
            path=path,
            agent=self.agent.name,
            agent_type=self.agent.get_metadata().get("type"),
        )

        sdk = self.get_sdk()
        add_fastapi_endpoint(app, sdk, path)

        logger.info(
            "CopilotKit endpoint mounted successfully",
            path=path,
            actions=len(self._actions),
        )
