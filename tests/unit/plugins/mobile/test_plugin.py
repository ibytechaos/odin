"""Tests for MobilePlugin."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from odin.plugins.builtin.mobile.interaction import (
    InputType,
    InteractionResult,
    NoOpInteractionHandler,
)
from odin.plugins.builtin.mobile.plugin import MobilePlugin


class MockController:
    """Mock controller for testing."""

    def __init__(self):
        self.tap = AsyncMock()
        self.long_press = AsyncMock()
        self.swipe = AsyncMock()
        self.input_text = AsyncMock()
        self.press_key = AsyncMock()
        self.screenshot = AsyncMock(return_value=b"PNG_DATA")
        self.open_app = AsyncMock()
        self.is_connected = AsyncMock(return_value=True)
        self.get_cached_screen_size = AsyncMock(return_value=(1080, 2340))


class TestMobilePlugin:
    """Tests for MobilePlugin class."""

    @pytest.fixture
    def controller(self):
        """Create a mock controller."""
        return MockController()

    @pytest.fixture
    def plugin(self, controller):
        """Create a plugin with mock controller."""
        plugin = MobilePlugin(controller=controller, tool_delay_ms=0)
        return plugin

    async def test_click_normalizes_coordinates(self, plugin, controller):
        """Test click converts normalized coordinates to pixels."""
        result = await plugin.click(x=0.5, y=0.5)

        assert result["success"] is True
        assert result["x"] == 540  # 0.5 * 1080
        assert result["y"] == 1170  # 0.5 * 2340
        controller.tap.assert_called_once_with(540, 1170)

    async def test_click_multiple_times(self, plugin, controller):
        """Test click with count > 1."""
        result = await plugin.click(x=100, y=200, count=3)

        assert result["count"] == 3
        assert controller.tap.call_count == 3

    async def test_long_press(self, plugin, controller):
        """Test long press."""
        result = await plugin.long_press(x=0.5, y=0.5, duration_ms=2000)

        assert result["success"] is True
        assert result["duration_ms"] == 2000
        controller.long_press.assert_called_once_with(540, 1170, 2000)

    async def test_input_text_without_enter(self, plugin, controller):
        """Test text input without pressing enter."""
        result = await plugin.input_text(text="hello")

        assert result["success"] is True
        assert result["text"] == "hello"
        controller.input_text.assert_called_once_with("hello")
        controller.press_key.assert_not_called()

    async def test_input_text_with_enter(self, plugin, controller):
        """Test text input with pressing enter."""
        result = await plugin.input_text(text="hello", press_enter=True)

        assert result["press_enter"] is True
        controller.input_text.assert_called_once_with("hello")
        controller.press_key.assert_called_once_with("enter")

    async def test_scroll(self, plugin, controller):
        """Test scroll/swipe."""
        result = await plugin.scroll(x1=0.5, y1=0.8, x2=0.5, y2=0.2, duration_ms=500)

        assert result["success"] is True
        assert result["from"] == {"x": 540, "y": 1872}
        assert result["to"] == {"x": 540, "y": 468}
        controller.swipe.assert_called_once()

    async def test_wait(self, plugin):
        """Test wait."""
        result = await plugin.wait(duration_ms=100)

        assert result["success"] is True
        assert result["duration_ms"] == 100

    async def test_open_app_with_alias(self, plugin, controller):
        """Test opening app by alias."""
        with patch("odin.plugins.builtin.mobile.plugin.get_app_mapper") as mock_mapper:
            mock_mapper.return_value.resolve.return_value = (
                "android",
                MagicMock(package="com.tencent.mm", activity=".ui.LauncherUI"),
            )

            result = await plugin.open_app(app_name="微信")

            assert result["success"] is True
            assert result["package"] == "com.tencent.mm"
            controller.open_app.assert_called_once_with("com.tencent.mm", ".ui.LauncherUI")

    async def test_open_app_with_package_name(self, plugin, controller):
        """Test opening app by direct package name."""
        with patch("odin.plugins.builtin.mobile.plugin.get_app_mapper") as mock_mapper:
            mock_mapper.return_value.resolve.return_value = None

            result = await plugin.open_app(app_name="com.example.app")

            assert result["success"] is True
            assert result["package"] == "com.example.app"
            controller.open_app.assert_called_once_with("com.example.app", None)

    async def test_screenshot(self, plugin, controller):
        """Test screenshot returns base64."""
        result = await plugin.screenshot()

        assert result["success"] is True
        assert result["format"] == "png"
        assert result["width"] == 1080
        assert result["height"] == 2340
        # Verify base64 encoding
        decoded = base64.b64decode(result["image_base64"])
        assert decoded == b"PNG_DATA"

    async def test_press_key(self, plugin, controller):
        """Test pressing a key."""
        result = await plugin.press_key(key="back")

        assert result["success"] is True
        assert result["key"] == "back"
        controller.press_key.assert_called_once_with("back")

    async def test_human_interact(self, plugin):
        """Test human interaction."""
        mock_handler = MagicMock()
        mock_handler.request_input = AsyncMock(
            return_value=InteractionResult(value="user input")
        )
        plugin.set_interaction_handler(mock_handler)

        result = await plugin.human_interact(prompt="Enter value:")

        assert result["success"] is True
        assert result["value"] == "user input"

    async def test_variable_storage_write_and_read(self, plugin):
        """Test variable storage write and read."""
        # Write
        result = await plugin.variable_storage(action="write", key="test_key", value="test_value")
        assert result["success"] is True

        # Read
        result = await plugin.variable_storage(action="read", key="test_key")
        assert result["success"] is True
        assert result["value"] == "test_value"
        assert result["exists"] is True

    async def test_variable_storage_list(self, plugin):
        """Test variable storage list."""
        await plugin.variable_storage(action="write", key="key1", value="v1")
        await plugin.variable_storage(action="write", key="key2", value="v2")

        result = await plugin.variable_storage(action="list")

        assert result["success"] is True
        assert result["count"] == 2
        assert "key1" in result["variables"]
        assert "key2" in result["variables"]

    async def test_variable_storage_delete(self, plugin):
        """Test variable storage delete."""
        await plugin.variable_storage(action="write", key="to_delete", value="v")

        result = await plugin.variable_storage(action="delete", key="to_delete")
        assert result["deleted"] is True

        result = await plugin.variable_storage(action="read", key="to_delete")
        assert result["exists"] is False

    async def test_check_connection(self, plugin, controller):
        """Test connection check."""
        result = await plugin.check_connection()

        assert result["success"] is True
        assert result["connected"] is True
        assert result["screen_size"] == {"width": 1080, "height": 2340}

    async def test_no_controller_raises_error(self):
        """Test that operations without controller raise error."""
        plugin = MobilePlugin()

        with pytest.raises(RuntimeError, match="No controller configured"):
            await plugin.click(x=0.5, y=0.5)

    async def test_plugin_has_tools(self, plugin):
        """Test that plugin has expected tools."""
        tools = await plugin.get_tools()
        tool_names = [t.name for t in tools]

        assert "click" in tool_names
        assert "long_press" in tool_names
        assert "input_text" in tool_names
        assert "scroll" in tool_names
        assert "wait" in tool_names
        assert "open_app" in tool_names
        assert "screenshot" in tool_names
        assert "press_key" in tool_names
        assert "human_interact" in tool_names
        assert "variable_storage" in tool_names
        assert "check_connection" in tool_names
