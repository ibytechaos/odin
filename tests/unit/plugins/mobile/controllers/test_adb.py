"""Tests for ADBController."""

from unittest.mock import AsyncMock, patch

import pytest

from odin.plugins.builtin.mobile.controllers.adb import ADBConfig, ADBController


class TestADBConfig:
    """Test ADBConfig model."""

    def test_default_adb_path(self):
        """Default adb path is 'adb'."""
        config = ADBConfig()
        assert config.adb_path == "adb"

    def test_custom_adb_path(self):
        """Custom adb path can be set."""
        config = ADBConfig(adb_path="/usr/local/bin/adb")
        assert config.adb_path == "/usr/local/bin/adb"


class TestADBController:
    """Test ADBController implementation."""

    @pytest.fixture
    def controller(self):
        """Create controller with mocked subprocess."""
        config = ADBConfig(device_id="emulator-5554")
        return ADBController(config)

    @pytest.mark.asyncio
    async def test_build_command_with_device(self, controller):
        """Command includes device flag when device_id is set."""
        cmd = controller._build_command("shell", "input", "tap", "100", "200")
        assert cmd == ["adb", "-s", "emulator-5554", "shell", "input", "tap", "100", "200"]

    @pytest.mark.asyncio
    async def test_build_command_without_device(self):
        """Command excludes device flag when device_id is None."""
        config = ADBConfig(device_id=None)
        controller = ADBController(config)
        cmd = controller._build_command("shell", "input", "tap", "100", "200")
        assert cmd == ["adb", "shell", "input", "tap", "100", "200"]

    @pytest.mark.asyncio
    async def test_tap_executes_correct_command(self, controller):
        """tap() executes correct adb command."""
        with patch.object(controller, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ""
            await controller.tap(100, 200)
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "input" in call_args
            assert "tap" in call_args
            assert "100" in call_args
            assert "200" in call_args

    @pytest.mark.asyncio
    async def test_swipe_executes_correct_command(self, controller):
        """swipe() executes correct adb command."""
        with patch.object(controller, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ""
            await controller.swipe(100, 200, 300, 400, 500)
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "swipe" in call_args
            assert "500" in call_args  # duration

    @pytest.mark.asyncio
    async def test_input_text_escapes_special_chars(self, controller):
        """input_text() escapes special characters."""
        with patch.object(controller, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ""
            await controller.input_text("hello world")
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            # Space should be escaped
            assert "hello%sworld" in " ".join(call_args) or "hello\\ world" in " ".join(call_args)

    @pytest.mark.asyncio
    async def test_press_key_maps_common_keys(self, controller):
        """press_key() maps common key names to keycodes."""
        with patch.object(controller, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ""
            await controller.press_key("back")
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "keyevent" in call_args
            assert "4" in call_args  # KEYCODE_BACK = 4

    @pytest.mark.asyncio
    async def test_get_screen_size_parses_output(self, controller):
        """get_screen_size() parses wm size output."""
        with patch.object(controller, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Physical size: 1080x1920"
            width, height = await controller.get_screen_size()
            assert width == 1080
            assert height == 1920

    @pytest.mark.asyncio
    async def test_is_connected_returns_true(self, controller):
        """is_connected() returns True when device responds."""
        with patch.object(controller, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "emulator-5554\tdevice"
            result = await controller.is_connected()
            assert result is True

    @pytest.mark.asyncio
    async def test_is_connected_returns_false_on_error(self, controller):
        """is_connected() returns False on error."""
        with patch.object(controller, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("Device not found")
            result = await controller.is_connected()
            assert result is False
