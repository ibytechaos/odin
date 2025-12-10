"""Plan and Execute agent for mobile automation."""

import json
from dataclasses import dataclass, field
from typing import Any

from odin.agents.mobile.base import AgentResult, AgentStatus, MobileAgentBase


@dataclass
class PlanStep:
    """A single step in the execution plan."""

    index: int
    description: str
    action_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, completed, failed, skipped
    result: dict[str, Any] | None = None


@dataclass
class ExecutionPlan:
    """Execution plan for a task."""

    task: str
    steps: list[PlanStep] = field(default_factory=list)
    current_step: int = 0

    @property
    def is_complete(self) -> bool:
        """Check if all steps are completed."""
        return self.current_step >= len(self.steps)

    @property
    def progress(self) -> float:
        """Get completion progress (0-1)."""
        if not self.steps:
            return 1.0
        return self.current_step / len(self.steps)


class MobilePlanExecuteAgent(MobileAgentBase):
    """Plan and Execute mobile automation agent.

    First generates a plan of steps, then executes each step
    while monitoring for deviations. Can replan if needed.

    Flow:
    1. Analyze initial screen state
    2. Generate execution plan
    3. Execute each step, verifying success
    4. Replan if step fails or state deviates
    """

    def __init__(
        self,
        *args: Any,
        replan_on_failure: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize the agent.

        Args:
            replan_on_failure: Whether to attempt replanning on step failure
            *args, **kwargs: Passed to MobileAgentBase
        """
        super().__init__(*args, **kwargs)
        self._replan_on_failure = replan_on_failure
        self._plan: ExecutionPlan | None = None
        self._replan_count = 0
        self._max_replans = 3

    @property
    def plan(self) -> ExecutionPlan | None:
        """Get current execution plan."""
        return self._plan

    async def execute(self, task: str) -> AgentResult:
        """Execute a task using plan and execute strategy.

        Args:
            task: The task description to execute

        Returns:
            AgentResult with execution outcome
        """
        self.reset()
        self._status = AgentStatus.RUNNING
        self._plan = None
        self._replan_count = 0
        self._log("info", f"Starting task: {task}")

        try:
            # Step 1: Take initial screenshot and analyze
            self._log("debug", "Taking initial screenshot...")
            _screenshot, analysis = await self.take_screenshot_and_analyze(task=task)
            self._log("info", f"Screen: {analysis.description[:100]}...")

            # Step 2: Generate initial plan
            self._log("info", "Generating execution plan...")
            self._plan = await self._generate_plan(task, analysis)

            if not self._plan.steps:
                self._status = AgentStatus.FAILED
                self._log("error", "Failed to generate execution plan")
                return AgentResult(
                    success=False,
                    message="Failed to generate execution plan",
                    error="empty_plan",
                )

            self._log("info", f"Plan generated with {len(self._plan.steps)} steps:")
            for step in self._plan.steps:
                self._log("info", f"  {step.index}. {step.description}")

            # Step 3: Execute plan steps
            while not self._plan.is_complete and self._current_round < self._max_rounds:
                if self._status == AgentStatus.PAUSED:
                    self._log("warning", "Execution paused")
                    return AgentResult(
                        success=False,
                        message="Execution paused",
                        steps_executed=self._current_round,
                    )

                self._current_round += 1
                step = self._plan.steps[self._plan.current_step]
                self._log("info", f"Executing step {step.index}/{len(self._plan.steps)}: {step.description}")

                # Execute the step
                step_result = await self._execute_step(step)
                self._log("debug", f"Step result: {step_result.get('success', False)}")

                if step_result["success"]:
                    step.status = "completed"
                    step.result = step_result
                    self._plan.current_step += 1
                    self._log("info", f"Step {step.index} completed")

                    self._add_to_history(
                        action=f"Step {step.index}: {step.description}",
                        result=step_result,
                    )
                else:
                    step.status = "failed"
                    step.result = step_result
                    self._log("warning", f"Step {step.index} failed")

                    # Try replanning if enabled
                    if self._replan_on_failure and self._replan_count < self._max_replans:
                        self._log("info", f"Attempting replan ({self._replan_count + 1}/{self._max_replans})...")
                        replan_success = await self._replan(task, step)
                        if not replan_success:
                            self._status = AgentStatus.FAILED
                            self._log("error", f"Replan failed for step {step.index}")
                            return AgentResult(
                                success=False,
                                message=f"Step {step.index} failed: {step.description}",
                                steps_executed=self._current_round,
                                error=str(step_result.get("error", "step_failed")),
                            )
                        self._log("info", "Replan successful, continuing execution...")
                    else:
                        self._status = AgentStatus.FAILED
                        self._log("error", f"Step {step.index} failed, max replans reached")
                        return AgentResult(
                            success=False,
                            message=f"Step {step.index} failed: {step.description}",
                            steps_executed=self._current_round,
                            error=str(step_result.get("error", "step_failed")),
                        )

            # Check completion
            if self._plan.is_complete:
                self._status = AgentStatus.COMPLETED
                self._log("info", "All steps completed successfully")
                final_screenshot, _ = await self.take_screenshot_and_analyze(task=task)
                return AgentResult(
                    success=True,
                    message="Plan executed successfully",
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

    async def _generate_plan(self, task: str, analysis: Any) -> ExecutionPlan:
        """Generate an execution plan for the task.

        Args:
            task: Task description
            analysis: Current screen analysis

        Returns:
            ExecutionPlan with steps
        """
        system_prompt = """You are a mobile automation planner. Generate a step-by-step plan to complete the task.

Each step should be a specific action:
- click: Click at a UI element
- input_text: Enter text
- scroll: Scroll the screen
- press_key: Press a key (back, home, enter)
- open_app: Open an application
- wait: Wait for something to load

Respond with a JSON array of steps:
[
    {"description": "Open WeChat app", "action_type": "open_app", "parameters": {"app_name": "微信"}},
    {"description": "Click search button", "action_type": "click", "parameters": {"x": 0.9, "y": 0.05}},
    {"description": "Enter search text", "action_type": "input_text", "parameters": {"text": "hello"}}
]

Keep plans concise (3-10 steps). Each step should be atomic and verifiable."""

        user_message = f"""Task: {task}

Current screen: {analysis.description}
Visible elements: {json.dumps(analysis.elements) if analysis.elements else "Not specified"}

Generate a plan to complete this task. Respond with JSON array only."""

        response = await self._llm_client.chat.completions.create(
            model=self._llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1024,
        )

        content = response.choices[0].message.content or ""

        # Parse JSON plan
        steps = []
        try:
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                raw_steps = json.loads(content[json_start:json_end])
                for i, step_data in enumerate(raw_steps):
                    steps.append(
                        PlanStep(
                            index=i + 1,
                            description=step_data.get("description", f"Step {i + 1}"),
                            action_type=step_data.get("action_type", "wait"),
                            parameters=step_data.get("parameters", {}),
                        )
                    )
        except json.JSONDecodeError:
            pass

        return ExecutionPlan(task=task, steps=steps)

    async def _execute_step(self, step: PlanStep) -> dict[str, Any]:
        """Execute a single plan step.

        Args:
            step: The step to execute

        Returns:
            Result dict from execution
        """
        action_type = step.action_type
        params = step.parameters

        if action_type == "click":
            return await self._plugin.click(
                x=params.get("x", 0.5),
                y=params.get("y", 0.5),
                count=params.get("count", 1),
            )

        elif action_type == "long_press":
            return await self._plugin.long_press(
                x=params.get("x", 0.5),
                y=params.get("y", 0.5),
                duration_ms=params.get("duration_ms", 1000),
            )

        elif action_type == "input_text":
            return await self._plugin.input_text(
                text=params.get("text", ""),
                press_enter=params.get("press_enter", False),
            )

        elif action_type == "scroll":
            return await self._plugin.scroll(
                x1=params.get("x1", 0.5),
                y1=params.get("y1", 0.8),
                x2=params.get("x2", 0.5),
                y2=params.get("y2", 0.2),
                duration_ms=params.get("duration_ms", 300),
            )

        elif action_type == "press_key":
            return await self._plugin.press_key(key=params.get("key", "back"))

        elif action_type == "open_app":
            return await self._plugin.open_app(app_name=params.get("app_name", ""))

        elif action_type == "wait":
            return await self._plugin.wait(duration_ms=params.get("duration_ms", 1000))

        else:
            return {"success": False, "error": f"Unknown action type: {action_type}"}

    async def _replan(self, task: str, failed_step: PlanStep) -> bool:
        """Attempt to replan after a step failure.

        Args:
            task: Original task
            failed_step: The step that failed

        Returns:
            True if replanning succeeded
        """
        self._replan_count += 1

        # Take new screenshot
        _screenshot, analysis = await self.take_screenshot_and_analyze(
            task=task,
            context=f"Step {failed_step.index} failed: {failed_step.description}",
        )

        # Generate new plan from current state
        remaining_task = f"{task} (continuing from failed step: {failed_step.description})"
        new_plan = await self._generate_plan(remaining_task, analysis)

        if new_plan.steps:
            # Replace remaining steps with new plan
            if self._plan is not None:
                completed_steps = [s for s in self._plan.steps if s.status == "completed"]
            else:
                completed_steps = []
            self._plan = ExecutionPlan(
                task=task,
                steps=completed_steps + new_plan.steps,
                current_step=len(completed_steps),
            )
            # Renumber steps
            for i, step in enumerate(self._plan.steps):
                step.index = i + 1
            return True

        return False
