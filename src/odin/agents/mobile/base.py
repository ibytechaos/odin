"""Base class for mobile automation agents."""

import base64
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openai import AsyncOpenAI

    from odin.plugins.builtin.mobile.interaction import HumanInteractionHandler
    from odin.plugins.builtin.mobile.plugin import MobilePlugin


# Type for log callback: (level, message) -> None
LogCallback = Callable[[str, str], None]


class AgentStatus(str, Enum):
    """Status of the agent execution."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class VisionAnalysis:
    """Result of visual analysis of a screenshot."""

    description: str
    elements: list[dict[str, Any]] = field(default_factory=list)
    suggested_action: str | None = None
    confidence: float = 0.0
    raw_response: str = ""


@dataclass
class AgentResult:
    """Result of agent execution."""

    success: bool
    message: str
    steps_executed: int = 0
    final_screenshot: bytes | None = None
    variables: dict[str, str] = field(default_factory=dict)
    error: str | None = None


class MobileAgentBase(ABC):
    """Abstract base class for mobile automation agents.

    Provides common functionality for screen analysis, tool execution,
    and agent lifecycle management. Subclasses implement specific
    execution strategies (ReAct, Plan+Execute, Hierarchical).
    """

    def __init__(
        self,
        plugin: MobilePlugin,
        llm_client: AsyncOpenAI,
        vlm_client: AsyncOpenAI | None = None,
        llm_model: str = "gpt-4o",
        vlm_model: str = "gpt-4o",
        max_rounds: int = 50,
        interaction_handler: HumanInteractionHandler | None = None,
        log_callback: LogCallback | None = None,
    ):
        """Initialize the mobile agent.

        Args:
            plugin: MobilePlugin instance with configured controller
            llm_client: OpenAI-compatible client for text generation
            vlm_client: OpenAI-compatible client for vision (defaults to llm_client)
            llm_model: Model name for text generation
            vlm_model: Model name for vision analysis
            max_rounds: Maximum execution rounds before stopping
            interaction_handler: Handler for human interaction requests
            log_callback: Optional callback for logging (level, message) -> None
        """
        self._plugin = plugin
        self._llm_client = llm_client
        self._vlm_client = vlm_client or llm_client
        self._llm_model = llm_model
        self._vlm_model = vlm_model
        self._max_rounds = max_rounds
        self._interaction_handler = interaction_handler
        self._log_callback = log_callback

        self._status = AgentStatus.IDLE
        self._current_round = 0
        self._history: list[dict[str, Any]] = []

    def _log(self, level: str, message: str) -> None:
        """Log a message via callback if available.

        Args:
            level: Log level (info, debug, warning, error)
            message: Log message
        """
        if self._log_callback:
            self._log_callback(level, message)

    @property
    def status(self) -> AgentStatus:
        """Get current agent status."""
        return self._status

    @property
    def current_round(self) -> int:
        """Get current execution round."""
        return self._current_round

    @property
    def history(self) -> list[dict[str, Any]]:
        """Get execution history."""
        return self._history.copy()

    def reset(self) -> None:
        """Reset agent state for new execution."""
        self._status = AgentStatus.IDLE
        self._current_round = 0
        self._history.clear()

    async def analyze_screen(
        self,
        screenshot: bytes,
        context: str = "",
        task: str = "",
    ) -> VisionAnalysis:
        """Analyze screenshot using VLM.

        Args:
            screenshot: PNG image bytes
            context: Additional context about current state
            task: The task being performed

        Returns:
            VisionAnalysis with description and suggested actions
        """
        base64_image = base64.b64encode(screenshot).decode("utf-8")

        system_prompt = """You are a mobile UI analyzer. Analyze the screenshot and provide:
1. A brief description of the current screen state
2. Key UI elements visible (buttons, text fields, lists, etc.)
3. Suggested next action based on the task

Respond in JSON format:
{
    "description": "Brief description of the screen",
    "elements": [{"type": "button", "text": "Submit", "location": "bottom"}],
    "suggested_action": "What action to take next",
    "confidence": 0.0-1.0
}"""

        user_content: list[dict[str, Any]] = []
        if task:
            user_content.append({"type": "text", "text": f"Task: {task}"})
        if context:
            user_content.append({"type": "text", "text": f"Context: {context}"})
        user_content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
        )

        response = await self._vlm_client.chat.completions.create(
            model=self._vlm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},  # type: ignore[misc,list-item]
            ],
            max_tokens=1024,
        )

        raw_response = response.choices[0].message.content or ""

        # Parse JSON response
        try:
            import json

            # Try to extract JSON from the response
            json_start = raw_response.find("{")
            json_end = raw_response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(raw_response[json_start:json_end])
                return VisionAnalysis(
                    description=data.get("description", ""),
                    elements=data.get("elements", []),
                    suggested_action=data.get("suggested_action"),
                    confidence=float(data.get("confidence", 0.0)),
                    raw_response=raw_response,
                )
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback if JSON parsing fails
        return VisionAnalysis(
            description=raw_response,
            raw_response=raw_response,
        )

    async def take_screenshot_and_analyze(
        self,
        context: str = "",
        task: str = "",
    ) -> tuple[bytes, VisionAnalysis]:
        """Take a screenshot and analyze it.

        Args:
            context: Additional context
            task: Current task description

        Returns:
            Tuple of (screenshot_bytes, analysis)
        """
        result = await self._plugin.screenshot()
        screenshot = base64.b64decode(result["image_base64"])
        analysis = await self.analyze_screen(screenshot, context, task)
        return screenshot, analysis

    def _add_to_history(
        self,
        action: str,
        result: dict[str, Any],
        analysis: VisionAnalysis | None = None,
    ) -> None:
        """Add an entry to execution history.

        Args:
            action: The action taken
            result: Result of the action
            analysis: Optional screen analysis
        """
        entry = {
            "round": self._current_round,
            "action": action,
            "result": result,
        }
        if analysis:
            entry["analysis"] = {
                "description": analysis.description,
                "suggested_action": analysis.suggested_action,
            }
        self._history.append(entry)

    @abstractmethod
    async def execute(self, task: str) -> AgentResult:
        """Execute a task.

        This is the main entry point for running the agent.
        Subclasses implement specific execution strategies.

        Args:
            task: The task description to execute

        Returns:
            AgentResult with execution outcome
        """
        ...

    async def stop(self) -> None:
        """Request the agent to stop execution."""
        if self._status == AgentStatus.RUNNING:
            self._status = AgentStatus.PAUSED

    async def resume(self) -> AgentResult | None:
        """Resume paused execution.

        Returns:
            AgentResult if execution completes, None if not applicable
        """
        if self._status != AgentStatus.PAUSED:
            return None
        self._status = AgentStatus.RUNNING
        return None  # Subclasses may override to continue execution
