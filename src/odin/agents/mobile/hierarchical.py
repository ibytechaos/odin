"""Hierarchical agent for mobile automation."""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

from odin.agents.mobile.base import AgentResult, AgentStatus, MobileAgentBase
from odin.agents.mobile.prompts import HIERARCHICAL_PLAN_SYSTEM_PROMPT
from odin.agents.mobile.react import MobileReActAgent


@dataclass
class SubTask:
    """A sub-task in the hierarchical plan."""

    index: int
    app: str
    objective: str
    status: str = "pending"  # pending, running, completed, failed
    result: AgentResult | None = None
    variables_in: dict[str, str] = field(default_factory=dict)
    variables_out: dict[str, str] = field(default_factory=dict)


@dataclass
class HierarchicalPlan:
    """High-level plan with app-level sub-tasks."""

    task: str
    sub_tasks: list[SubTask] = field(default_factory=list)
    current_index: int = 0

    @property
    def is_complete(self) -> bool:
        """Check if all sub-tasks are done."""
        return self.current_index >= len(self.sub_tasks)

    @property
    def current_sub_task(self) -> SubTask | None:
        """Get current sub-task."""
        if 0 <= self.current_index < len(self.sub_tasks):
            return self.sub_tasks[self.current_index]
        return None


class MobileHierarchicalAgent(MobileAgentBase):
    """Hierarchical mobile automation agent.

    Uses two levels of planning:
    1. High-level: Breaks task into app-level sub-tasks
    2. Low-level: Each sub-task is executed by a ReAct agent

    This is suitable for complex tasks spanning multiple apps,
    where each app interaction is a distinct sub-goal.

    Example task: "Take a photo and share it on WeChat"
    - Sub-task 1: Open Camera, take photo, save (Camera app)
    - Sub-task 2: Open WeChat, select photo, send to friend (WeChat app)
    """

    def __init__(
        self,
        *args: Any,
        sub_agent_max_rounds: int = 20,
        **kwargs: Any,
    ) -> None:
        """Initialize the hierarchical agent.

        Args:
            sub_agent_max_rounds: Max rounds for each sub-task's ReAct agent
            *args, **kwargs: Passed to MobileAgentBase
        """
        super().__init__(*args, **kwargs)
        self._sub_agent_max_rounds = sub_agent_max_rounds
        self._plan: HierarchicalPlan | None = None
        self._sub_agent: MobileReActAgent | None = None

    @property
    def plan(self) -> HierarchicalPlan | None:
        """Get current hierarchical plan."""
        return self._plan

    async def execute(self, task: str) -> AgentResult:
        """Execute a task using hierarchical planning.

        Args:
            task: The task description to execute

        Returns:
            AgentResult with execution outcome
        """
        self.reset()
        self._status = AgentStatus.RUNNING
        self._plan = None
        self._log("info", f"Starting task: {task}")

        try:
            # Step 1: Generate hierarchical plan (no screenshot needed for high-level planning)
            self._log("info", "Generating hierarchical plan...")
            self._plan = await self._generate_hierarchical_plan(task)

            if not self._plan.sub_tasks:
                self._status = AgentStatus.FAILED
                self._log("error", "Failed to generate hierarchical plan")
                return AgentResult(
                    success=False,
                    message="Failed to generate hierarchical plan",
                    error="empty_plan",
                )

            self._log("info", f"Plan generated with {len(self._plan.sub_tasks)} sub-tasks:")
            for st in self._plan.sub_tasks:
                self._log("info", f"  {st.index}. [{st.app}] {st.objective}")

            # Step 3: Execute each sub-task
            while not self._plan.is_complete and self._current_round < self._max_rounds:
                if self._status == AgentStatus.PAUSED:
                    self._log("warning", "Execution paused")
                    return AgentResult(
                        success=False,
                        message="Execution paused",
                        steps_executed=self._current_round,
                    )

                current_task = self._plan.current_sub_task
                if current_task is None:
                    break

                self._current_round += 1
                current_task.status = "running"
                self._log("info", f"Executing sub-task {current_task.index}/{len(self._plan.sub_tasks)}: [{current_task.app}] {current_task.objective}")

                # Pass variables from previous sub-tasks
                current_task.variables_in = self._plugin._variables.copy()

                # Execute sub-task with ReAct agent
                sub_result = await self._execute_sub_task(current_task)

                current_task.result = sub_result
                current_task.variables_out = self._plugin._variables.copy()

                if sub_result.success:
                    current_task.status = "completed"
                    self._plan.current_index += 1
                    self._log("info", f"Sub-task {current_task.index} completed (steps: {sub_result.steps_executed})")

                    self._add_to_history(
                        action=f"SubTask {current_task.index}: {current_task.app} - {current_task.objective}",
                        result={"success": True, "steps": sub_result.steps_executed},
                    )
                else:
                    current_task.status = "failed"
                    self._log("error", f"Sub-task {current_task.index} failed: {sub_result.error}")

                    # Try to recover or fail
                    self._status = AgentStatus.FAILED
                    return AgentResult(
                        success=False,
                        message=f"Sub-task {current_task.index} failed: {current_task.objective}",
                        steps_executed=self._current_round,
                        error=sub_result.error,
                        variables=self._plugin._variables.copy(),
                    )

            # Check if completed or max rounds reached
            if self._plan.is_complete:
                self._status = AgentStatus.COMPLETED
                self._log("info", "All sub-tasks completed successfully")
                # Take final screenshot (just for result, no analysis needed)
                final_screenshot = await self._plugin._controller.screenshot()  # type: ignore[union-attr]
                return AgentResult(
                    success=True,
                    message="Hierarchical plan executed successfully",
                    steps_executed=self._current_round,
                    final_screenshot=final_screenshot,
                    variables=self._plugin._variables.copy(),
                )
            else:
                self._status = AgentStatus.FAILED
                self._log("error", f"Max rounds ({self._max_rounds}) reached")
                return AgentResult(
                    success=False,
                    message=f"Max rounds ({self._max_rounds}) reached",
                    steps_executed=self._current_round,
                    error="max_rounds_exceeded",
                )

        except Exception as e:
            self._status = AgentStatus.FAILED
            self._log("error", f"Execution error: {e!s}")
            return AgentResult(
                success=False,
                message=f"Execution error: {e!s}",
                steps_executed=self._current_round,
                error=str(e),
            )

    async def _generate_hierarchical_plan(
        self,
        task: str,
    ) -> HierarchicalPlan:
        """Generate a hierarchical plan with app-level sub-tasks.

        Args:
            task: Task description

        Returns:
            HierarchicalPlan with sub-tasks
        """
        # Use validated prompt from prompts.py
        system_prompt = HIERARCHICAL_PLAN_SYSTEM_PROMPT

        user_message = f"""Task: {task}

Current variables: {json.dumps(self._plugin._variables) if self._plugin._variables else "None"}

Break this task into app-level sub-tasks. Respond with JSON array only."""

        # ============ DEBUG: Log full request ============
        logger.info("=" * 80)
        logger.info("[DEBUG] LLM REQUEST (hierarchical planner)")
        logger.info("=" * 80)
        debug_payload = {
            "model": self._llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": 512,
        }
        logger.info(json.dumps(debug_payload, indent=2, ensure_ascii=False))
        logger.info("=" * 80)

        response = await self._llm_client.chat.completions.create(
            model=self._llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=512,
        )

        content = response.choices[0].message.content or ""

        # ============ DEBUG: Log full response ============
        logger.info("=" * 80)
        logger.info("[DEBUG] LLM RESPONSE (hierarchical planner)")
        logger.info("=" * 80)
        debug_response = {
            "content": content,
        }
        logger.info(json.dumps(debug_response, indent=2, ensure_ascii=False))
        logger.info("=" * 80)

        # Parse JSON plan
        sub_tasks = []
        try:
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                raw_tasks = json.loads(content[json_start:json_end])
                for i, task_data in enumerate(raw_tasks):
                    sub_tasks.append(
                        SubTask(
                            index=i + 1,
                            app=task_data.get("app", "Unknown"),
                            objective=task_data.get("objective", f"Sub-task {i + 1}"),
                        )
                    )
        except json.JSONDecodeError:
            pass

        return HierarchicalPlan(task=task, sub_tasks=sub_tasks)

    async def _execute_sub_task(self, sub_task: SubTask) -> AgentResult:
        """Execute a sub-task using a ReAct agent.

        Args:
            sub_task: The sub-task to execute

        Returns:
            AgentResult from the sub-agent
        """
        # Create a fresh ReAct agent for this sub-task
        self._sub_agent = MobileReActAgent(
            plugin=self._plugin,
            llm_client=self._llm_client,
            vlm_client=self._vlm_client,
            llm_model=self._llm_model,
            vlm_model=self._vlm_model,
            max_rounds=self._sub_agent_max_rounds,
            log_callback=self._log_callback,
        )

        # Build the sub-task prompt
        prompt = f"App: {sub_task.app}\nObjective: {sub_task.objective}"

        if sub_task.variables_in:
            prompt += f"\nAvailable variables: {json.dumps(sub_task.variables_in)}"

        # Execute the sub-task
        result = await self._sub_agent.execute(prompt)

        return result
