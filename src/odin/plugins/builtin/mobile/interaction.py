"""Human interaction handlers for mobile automation."""

import asyncio
import inspect
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class InputType(str, Enum):
    """Types of input that can be requested from users."""

    TEXT = "text"
    CONFIRMATION = "confirmation"
    CHOICE = "choice"


class InteractionResult:
    """Result of a human interaction request."""

    def __init__(
        self,
        value: str | None,
        cancelled: bool = False,
        timed_out: bool = False,
    ):
        self.value = value
        self.cancelled = cancelled
        self.timed_out = timed_out

    @property
    def success(self) -> bool:
        """Check if interaction completed successfully."""
        return not self.cancelled and not self.timed_out and self.value is not None

    def __repr__(self) -> str:
        if self.cancelled:
            return "InteractionResult(cancelled=True)"
        if self.timed_out:
            return "InteractionResult(timed_out=True)"
        return f"InteractionResult(value={self.value!r})"


class HumanInteractionHandler(ABC):
    """Abstract base class for human interaction handlers.

    This defines the protocol for requesting human input during
    mobile automation tasks. Implementations can provide CLI,
    GUI, WebSocket, or other interaction methods.
    """

    @abstractmethod
    async def request_input(
        self,
        prompt: str,
        input_type: InputType = InputType.TEXT,
        choices: list[str] | None = None,
        timeout: float | None = None,
    ) -> InteractionResult:
        """Request input from a human operator.

        Args:
            prompt: The message to display to the user
            input_type: Type of input expected
            choices: List of choices for CHOICE input type
            timeout: Optional timeout in seconds

        Returns:
            InteractionResult with the user's response
        """
        ...

    async def confirm(self, prompt: str, timeout: float | None = None) -> bool:
        """Request a yes/no confirmation.

        Args:
            prompt: The confirmation message
            timeout: Optional timeout in seconds

        Returns:
            True if confirmed, False otherwise
        """
        result = await self.request_input(
            prompt,
            input_type=InputType.CONFIRMATION,
            timeout=timeout,
        )
        if not result.success or result.value is None:
            return False
        return result.value.lower() in ("y", "yes", "true", "1", "确认", "是")


class CLIInteractionHandler(HumanInteractionHandler):
    """Command-line interface interaction handler.

    Provides human interaction through stdin/stdout.
    Note: Uses synchronous input() wrapped in executor for async compatibility.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop | None = None):
        self._loop = loop

    async def request_input(
        self,
        prompt: str,
        input_type: InputType = InputType.TEXT,
        choices: list[str] | None = None,
        timeout: float | None = None,
    ) -> InteractionResult:
        """Request input via command line."""
        loop = self._loop or asyncio.get_event_loop()

        # Build the prompt message
        display_prompt = f"\n[Human Input Required] {prompt}"

        if input_type == InputType.CONFIRMATION:
            display_prompt += " (y/n)"
        elif input_type == InputType.CHOICE and choices:
            display_prompt += "\n"
            for i, choice in enumerate(choices, 1):
                display_prompt += f"  {i}. {choice}\n"
            display_prompt += "Enter number"

        display_prompt += ": "

        try:
            if timeout:
                # Run with timeout
                value = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: input(display_prompt)),
                    timeout=timeout,
                )
            else:
                value = await loop.run_in_executor(None, lambda: input(display_prompt))

            # Handle choice input
            if input_type == InputType.CHOICE and choices:
                try:
                    idx = int(value) - 1
                    if 0 <= idx < len(choices):
                        value = choices[idx]
                except ValueError:
                    pass  # Keep original value if not a number

            return InteractionResult(value=value.strip())

        except TimeoutError:
            print("\n[Timeout] No input received")
            return InteractionResult(value=None, timed_out=True)
        except EOFError:
            return InteractionResult(value=None, cancelled=True)
        except KeyboardInterrupt:
            return InteractionResult(value=None, cancelled=True)


class CallbackInteractionHandler(HumanInteractionHandler):
    """Callback-based interaction handler.

    Allows integration with external systems by providing
    callback functions for input requests.
    """

    def __init__(
        self,
        callback: Any,  # Callable that takes (prompt, input_type, choices, timeout) and returns str
    ):
        self._callback = callback

    async def request_input(
        self,
        prompt: str,
        input_type: InputType = InputType.TEXT,
        choices: list[str] | None = None,
        timeout: float | None = None,
    ) -> InteractionResult:
        """Request input via callback."""
        try:
            if inspect.iscoroutinefunction(self._callback):
                value = await self._callback(prompt, input_type, choices, timeout)
            else:
                value = self._callback(prompt, input_type, choices, timeout)

            if value is None:
                return InteractionResult(value=None, cancelled=True)

            return InteractionResult(value=str(value))
        except TimeoutError:
            return InteractionResult(value=None, timed_out=True)
        except Exception:
            return InteractionResult(value=None, cancelled=True)


class NoOpInteractionHandler(HumanInteractionHandler):
    """No-operation interaction handler.

    Always returns cancelled result. Useful for fully automated
    scenarios where human interaction should be skipped.
    """

    def __init__(self, default_value: str | None = None):
        self._default_value = default_value

    async def request_input(
        self,
        prompt: str,  # noqa: ARG002
        input_type: InputType = InputType.TEXT,  # noqa: ARG002
        choices: list[str] | None = None,  # noqa: ARG002
        timeout: float | None = None,  # noqa: ARG002
    ) -> InteractionResult:
        """Return default or cancelled result."""
        if self._default_value is not None:
            return InteractionResult(value=self._default_value)
        return InteractionResult(value=None, cancelled=True)
