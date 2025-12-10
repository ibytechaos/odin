"""Tests for human interaction handlers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from odin.plugins.builtin.mobile.interaction import (
    CLIInteractionHandler,
    CallbackInteractionHandler,
    InputType,
    InteractionResult,
    NoOpInteractionHandler,
)


class TestInteractionResult:
    """Tests for InteractionResult class."""

    def test_successful_result(self):
        """Test creating a successful result."""
        result = InteractionResult(value="test")
        assert result.success is True
        assert result.value == "test"
        assert result.cancelled is False
        assert result.timed_out is False

    def test_cancelled_result(self):
        """Test creating a cancelled result."""
        result = InteractionResult(value=None, cancelled=True)
        assert result.success is False
        assert result.cancelled is True

    def test_timed_out_result(self):
        """Test creating a timed out result."""
        result = InteractionResult(value=None, timed_out=True)
        assert result.success is False
        assert result.timed_out is True

    def test_repr_success(self):
        """Test string representation of successful result."""
        result = InteractionResult(value="hello")
        assert "hello" in repr(result)

    def test_repr_cancelled(self):
        """Test string representation of cancelled result."""
        result = InteractionResult(value=None, cancelled=True)
        assert "cancelled" in repr(result)

    def test_repr_timed_out(self):
        """Test string representation of timed out result."""
        result = InteractionResult(value=None, timed_out=True)
        assert "timed_out" in repr(result)


class TestCLIInteractionHandler:
    """Tests for CLIInteractionHandler."""

    @pytest.fixture
    def handler(self):
        """Create a CLI handler for testing."""
        return CLIInteractionHandler()

    async def test_text_input(self, handler):
        """Test basic text input."""
        with patch("builtins.input", return_value="test input"):
            result = await handler.request_input("Enter text:")
            assert result.success is True
            assert result.value == "test input"

    async def test_confirmation_prompt(self, handler):
        """Test confirmation includes y/n hint."""
        with patch("builtins.input", return_value="y") as mock_input:
            await handler.request_input("Confirm?", input_type=InputType.CONFIRMATION)
            prompt = mock_input.call_args[0][0]
            assert "(y/n)" in prompt

    async def test_choice_input(self, handler):
        """Test choice input converts number to choice."""
        with patch("builtins.input", return_value="2"):
            result = await handler.request_input(
                "Select:",
                input_type=InputType.CHOICE,
                choices=["Apple", "Banana", "Cherry"],
            )
            assert result.success is True
            assert result.value == "Banana"

    async def test_choice_invalid_number(self, handler):
        """Test choice input with invalid number keeps original."""
        with patch("builtins.input", return_value="invalid"):
            result = await handler.request_input(
                "Select:",
                input_type=InputType.CHOICE,
                choices=["Apple", "Banana"],
            )
            assert result.value == "invalid"

    async def test_confirm_yes(self, handler):
        """Test confirm method returns True for yes."""
        with patch("builtins.input", return_value="y"):
            assert await handler.confirm("Continue?") is True

    async def test_confirm_no(self, handler):
        """Test confirm method returns False for no."""
        with patch("builtins.input", return_value="n"):
            assert await handler.confirm("Continue?") is False

    async def test_confirm_chinese(self, handler):
        """Test confirm accepts Chinese confirmations."""
        with patch("builtins.input", return_value="是"):
            assert await handler.confirm("继续？") is True

    async def test_keyboard_interrupt(self, handler):
        """Test handling keyboard interrupt."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = await handler.request_input("Enter:")
            assert result.cancelled is True

    async def test_eof_error(self, handler):
        """Test handling EOF error."""
        with patch("builtins.input", side_effect=EOFError):
            result = await handler.request_input("Enter:")
            assert result.cancelled is True


class TestCallbackInteractionHandler:
    """Tests for CallbackInteractionHandler."""

    async def test_sync_callback(self):
        """Test with synchronous callback."""
        callback = MagicMock(return_value="callback result")
        handler = CallbackInteractionHandler(callback)

        result = await handler.request_input("Test prompt")

        assert result.success is True
        assert result.value == "callback result"
        callback.assert_called_once()

    async def test_async_callback(self):
        """Test with asynchronous callback."""
        callback = AsyncMock(return_value="async result")
        handler = CallbackInteractionHandler(callback)

        result = await handler.request_input("Test prompt")

        assert result.success is True
        assert result.value == "async result"

    async def test_callback_returns_none(self):
        """Test callback returning None results in cancelled."""
        callback = MagicMock(return_value=None)
        handler = CallbackInteractionHandler(callback)

        result = await handler.request_input("Test")

        assert result.cancelled is True

    async def test_callback_raises_exception(self):
        """Test callback raising exception results in cancelled."""
        callback = MagicMock(side_effect=ValueError("error"))
        handler = CallbackInteractionHandler(callback)

        result = await handler.request_input("Test")

        assert result.cancelled is True


class TestNoOpInteractionHandler:
    """Tests for NoOpInteractionHandler."""

    async def test_default_returns_cancelled(self):
        """Test default handler returns cancelled."""
        handler = NoOpInteractionHandler()
        result = await handler.request_input("Any prompt")
        assert result.cancelled is True

    async def test_with_default_value(self):
        """Test handler with default value."""
        handler = NoOpInteractionHandler(default_value="default")
        result = await handler.request_input("Any prompt")
        assert result.success is True
        assert result.value == "default"

    async def test_confirm_with_no_default(self):
        """Test confirm returns False with no default."""
        handler = NoOpInteractionHandler()
        assert await handler.confirm("Confirm?") is False

    async def test_confirm_with_yes_default(self):
        """Test confirm returns True with yes default."""
        handler = NoOpInteractionHandler(default_value="y")
        assert await handler.confirm("Confirm?") is True
