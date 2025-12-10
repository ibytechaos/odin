"""ADB (Android Debug Bridge) controller implementation."""

import asyncio
import re

from pydantic import Field

from odin.plugins.builtin.mobile.controllers.base import BaseController, ControllerConfig


class ADBConfig(ControllerConfig):
    """ADB-specific configuration."""

    adb_path: str = Field(default="adb", description="Path to adb executable")


# Key name to Android keycode mapping
KEY_CODES: dict[str, int] = {
    "back": 4,
    "home": 3,
    "enter": 66,
    "volume_up": 24,
    "volume_down": 25,
    "power": 26,
    "menu": 82,
    "tab": 61,
    "delete": 67,
    "space": 62,
}


class ADBController(BaseController):
    """Android device controller using ADB.

    Executes shell commands via adb to control Android devices.
    """

    def __init__(self, config: ADBConfig) -> None:
        """Initialize ADB controller.

        Args:
            config: ADB configuration
        """
        super().__init__(config)
        self.adb_config = config

    def _build_command(self, *args: str) -> list[str]:
        """Build adb command with device flag if needed.

        Args:
            *args: Command arguments

        Returns:
            Complete command as list
        """
        cmd = [self.adb_config.adb_path]
        if self.config.device_id:
            cmd.extend(["-s", self.config.device_id])
        cmd.extend(args)
        return cmd

    async def _run_command(self, cmd: list[str]) -> str:
        """Execute adb command and return output.

        Args:
            cmd: Command to execute

        Returns:
            Command stdout

        Raises:
            RuntimeError: If command fails
        """
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=self.config.timeout_ms / 1000,
        )

        if process.returncode != 0:
            raise RuntimeError(f"ADB command failed: {stderr.decode()}")

        return stdout.decode()

    async def _run_shell(self, *args: str) -> str:
        """Run adb shell command.

        Args:
            *args: Shell command arguments

        Returns:
            Command output
        """
        cmd = self._build_command("shell", *args)
        return await self._run_command(cmd)

    async def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        await self._run_shell("input", "tap", str(x), str(y))

    async def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        """Long press at coordinates using swipe with same start/end."""
        await self._run_shell(
            "input", "swipe", str(x), str(y), str(x), str(y), str(duration_ms)
        )

    async def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300
    ) -> None:
        """Swipe from one point to another."""
        await self._run_shell(
            "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)
        )

    async def input_text(self, text: str) -> None:
        """Input text, escaping special characters."""
        # Escape special characters for adb shell
        escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
        await self._run_shell("input", "text", escaped)

    async def press_key(self, key: str) -> None:
        """Press a key by name or keycode."""
        keycode = KEY_CODES.get(key.lower())
        if keycode is None:
            # Try to parse as integer keycode
            try:
                keycode = int(key)
            except ValueError:
                raise ValueError(f"Unknown key: {key}") from None
        await self._run_shell("input", "keyevent", str(keycode))

    async def screenshot(self) -> bytes:
        """Take screenshot and return PNG bytes."""
        cmd = self._build_command("exec-out", "screencap", "-p")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=self.config.timeout_ms / 1000,
        )

        if process.returncode != 0:
            raise RuntimeError(f"Screenshot failed: {stderr.decode()}")

        return stdout

    async def get_screen_size(self) -> tuple[int, int]:
        """Get screen size from wm size command."""
        output = await self._run_shell("wm", "size")
        # Parse "Physical size: 1080x1920"
        match = re.search(r"(\d+)x(\d+)", output)
        if not match:
            raise RuntimeError(f"Failed to parse screen size: {output}")
        return int(match.group(1)), int(match.group(2))

    async def open_app(self, package: str, activity: str | None = None) -> None:
        """Open app by package name."""
        if activity:
            component = f"{package}/{activity}"
            await self._run_shell("am", "start", "-n", component)
        else:
            await self._run_shell(
                "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"
            )

    async def is_connected(self) -> bool:
        """Check if device is connected."""
        try:
            cmd = self._build_command("devices")
            output = await self._run_command(cmd)
            if self.config.device_id:
                return self.config.device_id in output and "device" in output
            # If no device_id specified, check if any device is connected
            lines = output.strip().split("\n")
            return len(lines) > 1 and "device" in lines[1]
        except Exception:
            return False
