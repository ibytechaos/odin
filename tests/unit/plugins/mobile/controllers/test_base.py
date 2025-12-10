"""Tests for BaseController abstract class."""

import pytest

from odin.plugins.builtin.mobile.controllers.base import BaseController, ControllerConfig


class TestControllerConfig:
    """Test ControllerConfig model."""

    def test_default_values(self):
        """Config has sensible defaults."""
        config = ControllerConfig()
        assert config.device_id is None
        assert config.timeout_ms == 30000
        assert config.retry_count == 3

    def test_custom_values(self):
        """Config accepts custom values."""
        config = ControllerConfig(
            device_id="emulator-5554",
            timeout_ms=60000,
            retry_count=5,
        )
        assert config.device_id == "emulator-5554"
        assert config.timeout_ms == 60000
        assert config.retry_count == 5


class TestBaseController:
    """Test BaseController abstract class."""

    def test_cannot_instantiate(self):
        """BaseController cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseController(ControllerConfig())

    def test_subclass_must_implement_methods(self):
        """Subclass must implement all abstract methods."""

        class IncompleteController(BaseController):
            async def tap(self, x: int, y: int) -> None:
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteController(ControllerConfig())
