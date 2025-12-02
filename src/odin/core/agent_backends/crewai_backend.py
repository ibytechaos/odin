"""CrewAI agent backend implementation for Odin framework.

This is the default agent backend for Odin, using CrewAI for multi-agent orchestration.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from crewai import Agent as CrewAgent
from crewai import Crew, Task
from crewai.tools import BaseTool as CrewAIBaseTool
from pydantic import Field

from odin.core.agent_interface import AgentEvent, AgentState, IAgent
from odin.core.llm_factory import create_llm
from odin.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from odin.plugins.base import Tool

logger = get_logger(__name__)


class OdinToolWrapper(CrewAIBaseTool):
    """Adapter to convert Odin tools to CrewAI tools."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    odin_tool: Any = Field(..., description="Original Odin tool")

    def _run(self, **kwargs: Any) -> Any:
        """Synchronous execution (not recommended)."""
        raise NotImplementedError("Use async execution with _arun")

    async def _arun(self, **kwargs: Any) -> Any:
        """Asynchronous execution."""
        # Execute Odin tool

        # Get Odin instance from tool
        odin_app = getattr(self.odin_tool, "_odin_app", None)
        if odin_app:
            result = await odin_app.execute_tool(self.odin_tool.name, **kwargs)
        else:
            # Fallback: direct execution
            result = await self.odin_tool.execute(**kwargs)

        return result


class CrewAIAgentBackend(IAgent):
    """CrewAI-based agent backend.

    This is the default agent backend for Odin framework, providing:
    - Multi-agent orchestration
    - Task delegation
    - Robust error handling
    - Integration with all LLM providers

    Example:
        ```python
        from odin.core.llm_factory import create_llm

        agent = CrewAIAgentBackend(
            name="research_agent",
            description="AI research assistant",
            llm=create_llm()
        )

        # Add tools
        agent.add_tool(search_tool)
        agent.add_tool(analyze_tool)

        # Execute
        async for event in agent.execute(
            input="Research AI safety",
            thread_id="thread-1"
        ):
            print(event)
        ```
    """

    def __init__(
        self,
        name: str = "odin_agent",
        description: str = "AI assistant powered by Odin + CrewAI",
        llm: Any | None = None,
        role: str = "AI Assistant",
        goal: str | None = None,
        backstory: str | None = None,
        verbose: bool = True,
    ):
        """Initialize CrewAI agent backend.

        Args:
            name: Agent name
            description: Agent description
            llm: Language model (from create_llm())
            role: Agent role
            goal: Agent goal
            backstory: Agent backstory
            verbose: Enable verbose logging
        """
        self._name = name
        self._description = description
        self._llm = llm or create_llm()
        self._verbose = verbose

        # CrewAI components
        self._agents: list[CrewAgent] = []
        self._tasks: list[Task] = []
        self._crew: Crew | None = None
        self._tools: list[OdinToolWrapper] = []

        # State management
        self._states: dict[str, AgentState] = {}

        # Initialize crew
        self._initialize_crew(
            role=role,
            goal=goal or description,
            backstory=backstory or f"An expert {role} powered by Odin framework",
        )

    def _initialize_crew(self, role: str, goal: str, backstory: str):
        """Initialize CrewAI crew with default agent and task."""
        # Create main agent
        main_agent = CrewAgent(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=self._verbose,
            llm=self._llm,
            allow_delegation=False,  # Single agent by default
        )
        self._agents.append(main_agent)

        # Create default task
        default_task = Task(
            description="{user_request}",  # Templated from input
            agent=main_agent,
            expected_output="A helpful, accurate, and comprehensive response",
        )
        self._tasks.append(default_task)

        logger.info(
            "CrewAI agent initialized",
            agent=self._name,
            role=role,
        )

    @property
    def name(self) -> str:
        """Agent name."""
        return self._name

    @property
    def description(self) -> str:
        """Agent description."""
        return self._description

    def add_tool(self, tool: Tool) -> None:
        """Add Odin tool to CrewAI agent."""
        logger.info("Adding tool to CrewAI agent", tool=tool.name, agent=self._name)

        # Wrap Odin tool as CrewAI tool
        wrapper = OdinToolWrapper(
            name=tool.name,
            description=tool.description,
            odin_tool=tool,
        )
        self._tools.append(wrapper)

        # Add to all agents
        for agent in self._agents:
            if wrapper not in agent.tools:
                agent.tools.append(wrapper)

        # Rebuild crew
        self._rebuild_crew()

    def _rebuild_crew(self):
        """Rebuild crew with updated agents and tasks."""
        self._crew = Crew(
            agents=self._agents,
            tasks=self._tasks,
            verbose=self._verbose,
        )
        logger.debug("CrewAI crew rebuilt", agents=len(self._agents), tasks=len(self._tasks))

    async def execute(
        self,
        *,
        input: str | dict,
        state: AgentState | None = None,
        thread_id: str,
        **kwargs: Any,  # noqa: ARG002
    ) -> AsyncGenerator[AgentEvent]:
        """Execute CrewAI crew and yield events."""
        logger.info("Executing CrewAI agent", agent=self._name, thread_id=thread_id)

        # Initialize state if needed
        if thread_id not in self._states:
            self._states[thread_id] = state or AgentState(
                messages=[],
                current_step="start",
                intermediate_results=[],
                ui_components=[],
                error=None,
                metadata={},
            )

        # Prepare input
        if isinstance(input, str):
            crew_input = {"user_request": input}
            user_message = input
        else:
            crew_input = input
            user_message = input.get("user_request", str(input))

        # Add user message to state
        self._states[thread_id]["messages"].append({
            "role": "user",
            "content": user_message,
        })

        # Emit run started event
        yield AgentEvent(
            type="run_started",
            content=f"Starting {self._name}",
            metadata={"thread_id": thread_id, "agent": self._name},
        )

        # Update state
        self._states[thread_id]["current_step"] = "executing"
        yield AgentEvent(
            type="state_update",
            state=self._states[thread_id],
        )

        try:
            # Execute crew (sync method, run in thread pool)
            logger.debug("Kicking off CrewAI crew", input=crew_input)

            result = await asyncio.to_thread(
                self._crew.kickoff,
                inputs=crew_input,
            )

            result_text = str(result)
            logger.info("CrewAI execution completed", result_length=len(result_text))

            # Add assistant message to state
            self._states[thread_id]["messages"].append({
                "role": "assistant",
                "content": result_text,
            })

            # Emit message event
            yield AgentEvent(
                type="message",
                content=result_text,
                role="assistant",
            )

            # Update state
            self._states[thread_id]["current_step"] = "completed"
            self._states[thread_id]["intermediate_results"].append(result_text)

            yield AgentEvent(
                type="state_update",
                state=self._states[thread_id],
            )

            # Emit run finished event
            yield AgentEvent(
                type="run_finished",
                content="Execution completed successfully",
                metadata={"thread_id": thread_id, "agent": self._name},
            )

        except Exception as e:
            logger.error("CrewAI execution failed", error=str(e), agent=self._name)

            # Update state with error
            self._states[thread_id]["error"] = str(e)
            self._states[thread_id]["current_step"] = "failed"

            yield AgentEvent(
                type="error",
                error=str(e),
                metadata={"thread_id": thread_id, "agent": self._name},
            )

    async def get_state(self, thread_id: str) -> AgentState | None:
        """Get agent state for thread."""
        return self._states.get(thread_id)

    async def update_state(self, thread_id: str, state: AgentState) -> None:
        """Update agent state for thread."""
        self._states[thread_id] = state
        logger.debug("State updated", thread_id=thread_id, agent=self._name)

    def get_metadata(self) -> dict[str, Any]:
        """Get agent metadata."""
        return {
            "name": self._name,
            "description": self._description,
            "type": "crewai",
            "capabilities": [
                "multi_agent",
                "task_delegation",
                "tool_calling",
                "conversation",
            ],
            "tools": [tool.name for tool in self._tools],
            "agents": [
                {
                    "role": agent.role,
                    "goal": agent.goal,
                }
                for agent in self._agents
            ],
        }

    def get_crew(self) -> Crew:
        """Get underlying CrewAI Crew.

        This is useful for protocol adapters that need direct access to CrewAI.

        Returns:
            CrewAI Crew instance
        """
        if self._crew is None:
            self._rebuild_crew()
        return self._crew

    def get_copilotkit_agent(self):
        """Get CopilotKit-compatible agent wrapper.

        This method creates a CopilotKit CrewAIAgent wrapper for use with
        the CopilotKit protocol adapter.

        Returns:
            CopilotKit CrewAIAgent instance
        """
        try:
            from copilotkit.crewai import CrewAIAgent as CopilotKitCrewAIAgent
        except ImportError as e:
            raise ImportError(
                "copilotkit[crewai] is required for CopilotKit integration. "
                "Install with: pip install copilotkit[crewai]"
            ) from e

        return CopilotKitCrewAIAgent(
            name=self._name,
            description=self._description,
            crew=self._crew,
        )

    async def shutdown(self) -> None:
        """Cleanup resources."""
        logger.info("Shutting down CrewAI agent", agent=self._name)
        self._states.clear()
        self._tools.clear()
        self._agents.clear()
        self._tasks.clear()
        self._crew = None
