"""Agent abstraction interface for Odin framework.

This module defines the unified Agent interface that all agent backends
(CrewAI, LangGraph, custom) must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator
from typing_extensions import TypedDict

from odin.plugins.base import Tool


class AgentState(TypedDict, total=False):
    """Unified agent state across all backends.

    This state structure is protocol-agnostic and can be used with
    MCP, A2A, AG-UI, and CopilotKit.
    """

    messages: list[dict]  # Conversation history
    current_step: str  # Current execution step
    intermediate_results: list[Any]  # Intermediate results
    ui_components: list[dict]  # Generative UI components
    error: str | None  # Error message if any
    metadata: dict[str, Any]  # Custom metadata


class AgentEvent(TypedDict, total=False):
    """Events emitted by agent during execution.

    These events are protocol-agnostic and will be converted to
    protocol-specific format by adapters.
    """

    type: str  # Event type: message, tool_call, state_update, ui_component, error
    content: Any  # Event content
    role: str  # Message role: user, assistant, system
    tool: str  # Tool name (for tool_call events)
    args: dict  # Tool arguments (for tool_call events)
    state: AgentState  # Agent state (for state_update events)
    component: dict  # UI component definition (for ui_component events)
    error: str  # Error message (for error events)


class IAgent(ABC):
    """Unified agent interface.

    All agent backends (CrewAI, LangGraph, custom) must implement this interface.
    This allows Odin to support multiple agent frameworks while providing a
    consistent API to protocol adapters.

    Example:
        ```python
        # Create agent backend
        agent = CrewAIAgentBackend(name="my_agent")

        # Add tools
        for tool in odin_app.list_tools():
            agent.add_tool(tool)

        # Execute agent
        async for event in agent.execute(
            input="Hello, how are you?",
            thread_id="thread-123"
        ):
            print(event)
        ```
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description."""
        pass

    @abstractmethod
    async def execute(
        self,
        *,
        input: str | dict,
        state: AgentState | None = None,
        thread_id: str,
        **kwargs: Any,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute agent and yield events.

        Args:
            input: User input (text or structured data)
            state: Current agent state
            thread_id: Thread ID for persistence
            **kwargs: Additional arguments

        Yields:
            AgentEvent objects representing agent actions:
            - message: Agent response message
            - tool_call: Tool invocation
            - state_update: State change
            - ui_component: Generated UI component
            - error: Error during execution
        """
        pass

    @abstractmethod
    async def get_state(self, thread_id: str) -> AgentState | None:
        """Get agent state for a thread.

        Args:
            thread_id: Thread ID

        Returns:
            Agent state or None if thread doesn't exist
        """
        pass

    @abstractmethod
    async def update_state(self, thread_id: str, state: AgentState) -> None:
        """Update agent state for a thread.

        Args:
            thread_id: Thread ID
            state: New state
        """
        pass

    @abstractmethod
    def add_tool(self, tool: Tool) -> None:
        """Add tool to agent.

        Args:
            tool: Odin tool to add
        """
        pass

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """Get agent metadata.

        Returns:
            Dictionary with:
            - name: Agent name
            - description: Agent description
            - type: Backend type (crewai, langgraph, custom)
            - capabilities: List of capabilities
            - tools: List of available tool names
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup resources."""
        pass
