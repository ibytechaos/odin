"""ReAct agent for mobile automation."""

import json
from typing import Any

from odin.agents.mobile.base import AgentResult, AgentStatus, MobileAgentBase


class MobileReActAgent(MobileAgentBase):
    """ReAct-style mobile automation agent.

    Implements the ReAct pattern: Reasoning + Acting in a loop.
    Each round: Screenshot → Think (VLM) → Act (Tool) → Observe

    This is the simplest agent strategy, suitable for straightforward
    tasks that don't require complex planning.
    """

    async def execute(self, task: str) -> AgentResult:
        """Execute a task using ReAct loop.

        Args:
            task: The task description to execute

        Returns:
            AgentResult with execution outcome
        """
        self.reset()
        self._status = AgentStatus.RUNNING
        self._log("info", f"Starting task: {task}")

        try:
            while self._current_round < self._max_rounds:
                if self._status == AgentStatus.PAUSED:
                    self._log("warning", "Execution paused")
                    return AgentResult(
                        success=False,
                        message="Execution paused",
                        steps_executed=self._current_round,
                    )

                self._current_round += 1
                self._log("info", f"Round {self._current_round}/{self._max_rounds}")

                # Step 1: Take screenshot and analyze
                self._log("debug", "Taking screenshot...")
                screenshot, analysis = await self.take_screenshot_and_analyze(
                    task=task,
                    context=self._build_context(),
                )
                self._log("info", f"Screen: {analysis.description[:100]}...")

                # Step 2: Decide next action using LLM
                self._log("debug", "Deciding next action...")
                action = await self._decide_action(task, analysis)
                self._log("info", f"Action: {action.get('type', 'unknown')}")

                # Check if task is complete
                if action.get("type") == "complete":
                    self._status = AgentStatus.COMPLETED
                    self._log("info", f"Task completed: {action.get('message', '')}")
                    return AgentResult(
                        success=True,
                        message=action.get("message", "Task completed"),
                        steps_executed=self._current_round,
                        final_screenshot=screenshot,
                        variables=self._plugin._variables.copy(),
                    )

                # Check if task failed
                if action.get("type") == "fail":
                    self._status = AgentStatus.FAILED
                    self._log("error", f"Task failed: {action.get('message', '')}")
                    return AgentResult(
                        success=False,
                        message=action.get("message", "Task failed"),
                        steps_executed=self._current_round,
                        error=action.get("error"),
                    )

                # Step 3: Execute the action
                self._log("debug", f"Executing: {json.dumps(action, ensure_ascii=False)}")
                result = await self._execute_action(action)
                self._log("debug", f"Result: {result.get('success', False)}")

                # Step 4: Record to history
                self._add_to_history(
                    action=json.dumps(action),
                    result=result,
                    analysis=analysis,
                )

            # Max rounds reached
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

    def _build_context(self) -> str:
        """Build context from recent history.

        Returns:
            Context string for VLM
        """
        if not self._history:
            return ""

        # Include last 3 actions for context
        recent = self._history[-3:]
        context_parts = []
        for entry in recent:
            action = entry.get("action", "")
            result = entry.get("result", {})
            success = result.get("success", False)
            context_parts.append(f"Action: {action} -> {'Success' if success else 'Failed'}")

        return "\n".join(context_parts)

    async def _decide_action(
        self,
        task: str,
        analysis: Any,
    ) -> dict[str, Any]:
        """Decide the next action based on screen analysis.

        Args:
            task: The task being executed
            analysis: VisionAnalysis from screen

        Returns:
            Action dict with type and parameters
        """
        system_prompt = """You are a mobile automation agent. Based on the task and current screen state, decide the next action.

Available actions:
- click: {"type": "click", "x": 0.5, "y": 0.5} - Click at position (0-1 normalized)
- long_press: {"type": "long_press", "x": 0.5, "y": 0.5, "duration_ms": 1000}
- input_text: {"type": "input_text", "text": "hello", "press_enter": false}
- scroll: {"type": "scroll", "x1": 0.5, "y1": 0.8, "x2": 0.5, "y2": 0.2} - Scroll up
- press_key: {"type": "press_key", "key": "back"} - Keys: back, home, enter
- open_app: {"type": "open_app", "app_name": "微信"}
- wait: {"type": "wait", "duration_ms": 1000}
- complete: {"type": "complete", "message": "Task done"} - Task completed successfully
- fail: {"type": "fail", "message": "Cannot proceed", "error": "reason"}

Respond with a single JSON action. Think step by step about what action will help achieve the task."""

        user_message = f"""Task: {task}

Current screen: {analysis.description}
Visible elements: {json.dumps(analysis.elements) if analysis.elements else "Not specified"}
Suggested action: {analysis.suggested_action or "None"}
Confidence: {analysis.confidence}

Recent history:
{self._build_context() or "No previous actions"}

What is the next action? Respond with JSON only."""

        response = await self._llm_client.chat.completions.create(
            model=self._llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=256,
        )

        content = response.choices[0].message.content or ""

        # Parse JSON action
        try:
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result: dict[str, Any] = json.loads(content[json_start:json_end])
                return result
        except json.JSONDecodeError:
            pass

        # Fallback: try to interpret as simple action
        return {"type": "wait", "duration_ms": 500}

    async def _execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute an action using the plugin.

        Args:
            action: Action dict with type and parameters

        Returns:
            Result dict from the tool
        """
        action_type = action.get("type", "")

        if action_type == "click":
            return await self._plugin.click(
                x=action.get("x", 0.5),
                y=action.get("y", 0.5),
                count=action.get("count", 1),
            )

        elif action_type == "long_press":
            return await self._plugin.long_press(
                x=action.get("x", 0.5),
                y=action.get("y", 0.5),
                duration_ms=action.get("duration_ms", 1000),
            )

        elif action_type == "input_text":
            return await self._plugin.input_text(
                text=action.get("text", ""),
                press_enter=action.get("press_enter", False),
            )

        elif action_type == "scroll":
            return await self._plugin.scroll(
                x1=action.get("x1", 0.5),
                y1=action.get("y1", 0.8),
                x2=action.get("x2", 0.5),
                y2=action.get("y2", 0.2),
                duration_ms=action.get("duration_ms", 300),
            )

        elif action_type == "press_key":
            return await self._plugin.press_key(key=action.get("key", "back"))

        elif action_type == "open_app":
            return await self._plugin.open_app(app_name=action.get("app_name", ""))

        elif action_type == "wait":
            return await self._plugin.wait(duration_ms=action.get("duration_ms", 1000))

        else:
            return {"success": False, "error": f"Unknown action type: {action_type}"}
