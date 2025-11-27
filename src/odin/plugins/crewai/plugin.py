"""CrewAI plugin implementation."""

from typing import Any

from crewai import Agent, Crew, Task
from crewai.tools import BaseTool as CrewAIBaseTool
from pydantic import Field

from odin.errors import ErrorCode, ExecutionError
from odin.logging import get_logger
from odin.plugins.base import (
    AgentPlugin,
    PluginConfig,
    Tool,
    ToolParameter,
    ToolParameterType,
)

logger = get_logger(__name__)


class CrewAIToolAdapter(CrewAIBaseTool):
    """Adapter to convert Odin tools to CrewAI tools."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    odin_tool: Tool = Field(..., description="Original Odin tool")
    executor: Any = Field(..., description="Tool executor function")

    def _run(self, **kwargs: Any) -> Any:
        """Synchronous execution (not used in async context)."""
        raise NotImplementedError("Use async execution")

    async def _arun(self, **kwargs: Any) -> Any:
        """Asynchronous execution."""
        return await self.executor(self.odin_tool.name, **kwargs)


class CrewAIPlugin(AgentPlugin):
    """Plugin for integrating CrewAI agents into Odin framework.

    This plugin allows you to:
    1. Create CrewAI agents with specific roles and tools
    2. Define tasks for agents to execute
    3. Orchestrate multi-agent crews
    4. Execute crew workflows
    """

    def __init__(self, config: PluginConfig | None = None) -> None:
        """Initialize CrewAI plugin."""
        super().__init__(config)
        self._agents: dict[str, Agent] = {}
        self._crews: dict[str, Crew] = {}
        self._tasks: dict[str, Task] = {}

    @property
    def name(self) -> str:
        """Get plugin name."""
        return "crewai"

    @property
    def version(self) -> str:
        """Get plugin version."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """Get plugin description."""
        return "CrewAI agent orchestration framework integration"

    async def get_tools(self) -> list[Tool]:
        """Get available tools for CrewAI operations."""
        return [
            Tool(
                name="create_agent",
                description="Create a new CrewAI agent with specific role and capabilities",
                parameters=[
                    ToolParameter(
                        name="agent_id",
                        type=ToolParameterType.STRING,
                        description="Unique identifier for the agent",
                        required=True,
                    ),
                    ToolParameter(
                        name="role",
                        type=ToolParameterType.STRING,
                        description="Agent's role (e.g., 'researcher', 'writer')",
                        required=True,
                    ),
                    ToolParameter(
                        name="goal",
                        type=ToolParameterType.STRING,
                        description="Agent's primary goal",
                        required=True,
                    ),
                    ToolParameter(
                        name="backstory",
                        type=ToolParameterType.STRING,
                        description="Agent's background and expertise",
                        required=False,
                    ),
                    ToolParameter(
                        name="allow_delegation",
                        type=ToolParameterType.BOOLEAN,
                        description="Whether agent can delegate tasks to other agents",
                        required=False,
                        default=False,
                    ),
                    ToolParameter(
                        name="verbose",
                        type=ToolParameterType.BOOLEAN,
                        description="Enable verbose logging",
                        required=False,
                        default=True,
                    ),
                ],
            ),
            Tool(
                name="create_task",
                description="Create a task for an agent to execute",
                parameters=[
                    ToolParameter(
                        name="task_id",
                        type=ToolParameterType.STRING,
                        description="Unique identifier for the task",
                        required=True,
                    ),
                    ToolParameter(
                        name="description",
                        type=ToolParameterType.STRING,
                        description="Detailed task description",
                        required=True,
                    ),
                    ToolParameter(
                        name="agent_id",
                        type=ToolParameterType.STRING,
                        description="ID of agent assigned to this task",
                        required=True,
                    ),
                    ToolParameter(
                        name="expected_output",
                        type=ToolParameterType.STRING,
                        description="Expected output format or content",
                        required=False,
                    ),
                ],
            ),
            Tool(
                name="create_crew",
                description="Create a crew of agents to work together",
                parameters=[
                    ToolParameter(
                        name="crew_id",
                        type=ToolParameterType.STRING,
                        description="Unique identifier for the crew",
                        required=True,
                    ),
                    ToolParameter(
                        name="agent_ids",
                        type=ToolParameterType.ARRAY,
                        description="List of agent IDs in the crew",
                        required=True,
                    ),
                    ToolParameter(
                        name="task_ids",
                        type=ToolParameterType.ARRAY,
                        description="List of task IDs to execute",
                        required=True,
                    ),
                    ToolParameter(
                        name="verbose",
                        type=ToolParameterType.BOOLEAN,
                        description="Enable verbose logging",
                        required=False,
                        default=True,
                    ),
                ],
            ),
            Tool(
                name="execute_crew",
                description="Execute a crew's tasks and return results",
                parameters=[
                    ToolParameter(
                        name="crew_id",
                        type=ToolParameterType.STRING,
                        description="ID of crew to execute",
                        required=True,
                    ),
                    ToolParameter(
                        name="inputs",
                        type=ToolParameterType.OBJECT,
                        description="Input data for the crew execution",
                        required=False,
                    ),
                ],
            ),
            Tool(
                name="list_agents",
                description="List all created agents",
                parameters=[],
            ),
            Tool(
                name="list_tasks",
                description="List all created tasks",
                parameters=[],
            ),
            Tool(
                name="list_crews",
                description="List all created crews",
                parameters=[],
            ),
        ]

    async def execute_tool(
        self, tool_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Execute a CrewAI tool."""
        logger.info("Executing CrewAI tool", tool=tool_name, params=kwargs)

        if tool_name == "create_agent":
            return await self._create_agent(**kwargs)
        elif tool_name == "create_task":
            return await self._create_task(**kwargs)
        elif tool_name == "create_crew":
            return await self._create_crew(**kwargs)
        elif tool_name == "execute_crew":
            return await self._execute_crew(**kwargs)
        elif tool_name == "list_agents":
            return await self._list_agents()
        elif tool_name == "list_tasks":
            return await self._list_tasks()
        elif tool_name == "list_crews":
            return await self._list_crews()
        else:
            raise ExecutionError(
                f"Unknown CrewAI tool: {tool_name}",
                code=ErrorCode.TOOL_NOT_FOUND,
                details={"tool": tool_name},
            )

    async def _create_agent(
        self,
        agent_id: str,
        role: str,
        goal: str,
        backstory: str = "",
        allow_delegation: bool = False,
        verbose: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a CrewAI agent."""
        if agent_id in self._agents:
            raise ExecutionError(
                f"Agent '{agent_id}' already exists",
                code=ErrorCode.VALIDATION_ERROR,
                details={"agent_id": agent_id},
            )

        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory or f"An expert {role}",
            allow_delegation=allow_delegation,
            verbose=verbose,
        )

        self._agents[agent_id] = agent

        logger.info("Created CrewAI agent", agent_id=agent_id, role=role)

        return {
            "success": True,
            "agent_id": agent_id,
            "role": role,
            "goal": goal,
        }

    async def _create_task(
        self,
        task_id: str,
        description: str,
        agent_id: str,
        expected_output: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a task for an agent."""
        if task_id in self._tasks:
            raise ExecutionError(
                f"Task '{task_id}' already exists",
                code=ErrorCode.VALIDATION_ERROR,
                details={"task_id": task_id},
            )

        if agent_id not in self._agents:
            raise ExecutionError(
                f"Agent '{agent_id}' not found",
                code=ErrorCode.VALIDATION_ERROR,
                details={"agent_id": agent_id},
            )

        task = Task(
            description=description,
            agent=self._agents[agent_id],
            expected_output=expected_output or "Task completion summary",
        )

        self._tasks[task_id] = task

        logger.info("Created task", task_id=task_id, agent_id=agent_id)

        return {
            "success": True,
            "task_id": task_id,
            "agent_id": agent_id,
            "description": description,
        }

    async def _create_crew(
        self,
        crew_id: str,
        agent_ids: list[str],
        task_ids: list[str],
        verbose: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a crew of agents."""
        if crew_id in self._crews:
            raise ExecutionError(
                f"Crew '{crew_id}' already exists",
                code=ErrorCode.VALIDATION_ERROR,
                details={"crew_id": crew_id},
            )

        # Validate agents
        agents = []
        for agent_id in agent_ids:
            if agent_id not in self._agents:
                raise ExecutionError(
                    f"Agent '{agent_id}' not found",
                    code=ErrorCode.VALIDATION_ERROR,
                    details={"agent_id": agent_id},
                )
            agents.append(self._agents[agent_id])

        # Validate tasks
        tasks = []
        for task_id in task_ids:
            if task_id not in self._tasks:
                raise ExecutionError(
                    f"Task '{task_id}' not found",
                    code=ErrorCode.VALIDATION_ERROR,
                    details={"task_id": task_id},
                )
            tasks.append(self._tasks[task_id])

        crew = Crew(
            agents=agents,
            tasks=tasks,
            verbose=verbose,
        )

        self._crews[crew_id] = crew

        logger.info(
            "Created crew",
            crew_id=crew_id,
            agent_count=len(agents),
            task_count=len(tasks),
        )

        return {
            "success": True,
            "crew_id": crew_id,
            "agents": agent_ids,
            "tasks": task_ids,
        }

    async def _execute_crew(
        self, crew_id: str, inputs: dict[str, Any] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Execute a crew."""
        if crew_id not in self._crews:
            raise ExecutionError(
                f"Crew '{crew_id}' not found",
                code=ErrorCode.VALIDATION_ERROR,
                details={"crew_id": crew_id},
            )

        crew = self._crews[crew_id]

        logger.info("Executing crew", crew_id=crew_id, inputs=inputs)

        try:
            # CrewAI kickoff is sync, so we need to handle it carefully
            # In a real implementation, you might want to run this in a thread pool
            result = crew.kickoff(inputs=inputs or {})

            return {
                "success": True,
                "crew_id": crew_id,
                "result": str(result),
            }
        except Exception as e:
            raise ExecutionError(
                f"Crew execution failed: {e}",
                code=ErrorCode.AGENT_EXECUTION_FAILED,
                details={"crew_id": crew_id, "error": str(e)},
            ) from e

    async def _list_agents(self) -> dict[str, Any]:
        """List all agents."""
        return {
            "agents": [
                {
                    "id": agent_id,
                    "role": agent.role,
                    "goal": agent.goal,
                }
                for agent_id, agent in self._agents.items()
            ]
        }

    async def _list_tasks(self) -> dict[str, Any]:
        """List all tasks."""
        return {
            "tasks": [
                {
                    "id": task_id,
                    "description": task.description,
                }
                for task_id, task in self._tasks.items()
            ]
        }

    async def _list_crews(self) -> dict[str, Any]:
        """List all crews."""
        return {
            "crews": [
                {
                    "id": crew_id,
                    "agent_count": len(crew.agents),
                    "task_count": len(crew.tasks),
                }
                for crew_id, crew in self._crews.items()
            ]
        }

    async def shutdown(self) -> None:
        """Cleanup resources."""
        self._agents.clear()
        self._tasks.clear()
        self._crews.clear()
        await super().shutdown()
