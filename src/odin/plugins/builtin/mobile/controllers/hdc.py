"""HDC (HarmonyOS Device Connector) controller implementation."""

import asyncio
import contextlib
import re
import tempfile
from pathlib import Path

from pydantic import Field

from odin.plugins.builtin.mobile.controllers.base import BaseController, ControllerConfig


class HDCConfig(ControllerConfig):
    """HDC-specific configuration."""

    hdc_path: str = Field(default="hdc", description="Path to hdc executable")


# Key name to HarmonyOS keycode mapping
# HarmonyOS uses similar keycodes to Android
KEY_CODES: dict[str, int] = {
    "back": 2,  # HarmonyOS Back key
    "home": 1,  # HarmonyOS Home key
    "enter": 66,
    "volume_up": 16,
    "volume_down": 17,
    "power": 18,
    "menu": 82,
    "tab": 61,
    "delete": 67,
    "space": 62,
}


class HDCController(BaseController):
    """HarmonyOS device controller using HDC.

    Executes shell commands via hdc to control HarmonyOS devices.
    HDC (HarmonyOS Device Connector) is similar to ADB but for HarmonyOS.
    """

    def __init__(self, config: HDCConfig) -> None:
        """Initialize HDC controller.

        Args:
            config: HDC configuration
        """
        super().__init__(config)
        self.hdc_config = config

    def _build_command(self, *args: str) -> list[str]:
        """Build hdc command with device flag if needed.

        Args:
            *args: Command arguments

        Returns:
            Complete command as list
        """
        cmd = [self.hdc_config.hdc_path]
        if self.config.device_id:
            cmd.extend(["-t", self.config.device_id])
        cmd.extend(args)
        return cmd

    async def _run_command(self, cmd: list[str]) -> str:
        """Execute hdc command and return output.

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
            raise RuntimeError(f"HDC command failed: {stderr.decode()}")

        return stdout.decode()

    async def _run_shell(self, *args: str) -> str:
        """Run hdc shell command.

        Args:
            *args: Shell command arguments

        Returns:
            Command output
        """
        cmd = self._build_command("shell", *args)
        return await self._run_command(cmd)

    async def tap(self, x: int, y: int) -> None:
        """Tap at coordinates using uitest."""
        # HarmonyOS uses uitest for UI automation
        await self._run_shell("uitest", "uiInput", "click", str(x), str(y))

    async def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        """Long press at coordinates."""
        # HarmonyOS uitest supports longClick
        await self._run_shell("uitest", "uiInput", "longClick", str(x), str(y), str(duration_ms))

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Swipe from one point to another."""
        # Convert duration to speed (pixels per second)
        # HarmonyOS uitest swipe uses: swipe x1 y1 x2 y2 speed
        # Default speed is 600, adjust based on duration
        speed = max(200, min(40000, 600 * 300 // max(duration_ms, 1)))
        await self._run_shell(
            "uitest", "uiInput", "swipe", str(x1), str(y1), str(x2), str(y2), str(speed)
        )

    async def input_text(self, text: str) -> None:
        """Input text using uitest."""
        # HarmonyOS uitest inputText command
        await self._run_shell("uitest", "uiInput", "inputText", text)

    async def press_key(self, key: str) -> None:
        """Press a key by name or keycode."""
        keycode = KEY_CODES.get(key.lower())
        if keycode is None:
            # Try to parse as integer keycode
            try:
                keycode = int(key)
            except ValueError:
                raise ValueError(f"Unknown key: {key}") from None
        # HarmonyOS keyEvent command
        await self._run_shell("uitest", "uiInput", "keyEvent", str(keycode))

    async def screenshot(self) -> bytes:
        """Take screenshot and return JPEG bytes.

        Note: HarmonyOS snapshot_display only supports JPEG format.
        """
        # HarmonyOS screenshot command saves to file (must be .jpeg)
        remote_path = "/data/local/tmp/screenshot.jpeg"
        await self._run_shell("snapshot_display", "-f", remote_path)

        # Pull the file to local
        with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False) as f:
            local_path = Path(f.name)

        try:
            cmd = self._build_command("file", "recv", remote_path, str(local_path))
            await self._run_command(cmd)

            # Read and return the file contents
            return local_path.read_bytes()
        finally:
            # Clean up local file
            if local_path.exists():
                local_path.unlink()
            # Clean up remote file
            with contextlib.suppress(Exception):
                await self._run_shell("rm", remote_path)

    async def get_screen_size(self) -> tuple[int, int]:
        """Get screen size from hidumper RenderService."""
        output = await self._run_shell("hidumper", "-s", "RenderService", "-a", "screen")
        # Parse screen size from hidumper output
        # Format: "physical resolution=1260x2844" or "render resolution=1260x2844"
        resolution_match = re.search(
            r"(?:physical|render)\s+resolution[=:]\s*(\d+)x(\d+)", output, re.IGNORECASE
        )
        if resolution_match:
            return int(resolution_match.group(1)), int(resolution_match.group(2))

        # Alternative pattern: "width: 1080, height: 2400"
        width_match = re.search(r"width[:\s]+(\d+)", output, re.IGNORECASE)
        height_match = re.search(r"height[:\s]+(\d+)", output, re.IGNORECASE)

        if width_match and height_match:
            return int(width_match.group(1)), int(height_match.group(1))

        raise RuntimeError(f"Failed to parse screen size from: {output}")

    async def open_app(self, package: str, activity: str | None = None) -> None:
        """Open app by bundle name (package name in HarmonyOS).

        Args:
            package: Bundle name (e.g., "com.example.app")
            activity: Ability name (optional, HarmonyOS uses abilities instead of activities)
        """
        if activity:
            # Start specific ability
            await self._run_shell("aa", "start", "-b", package, "-a", activity)
        else:
            # Start main ability of the bundle
            await self._run_shell("aa", "start", "-b", package)

    async def is_connected(self) -> bool:
        """Check if device is connected."""
        try:
            cmd = self._build_command("list", "targets")
            output = await self._run_command(cmd)
            if self.config.device_id:
                return self.config.device_id in output
            # If no device_id specified, check if any device is connected
            lines = [line.strip() for line in output.strip().split("\n") if line.strip()]
            return len(lines) > 0 and "[Empty]" not in output
        except Exception:
            return False

    async def get_current_app(self) -> str:
        """Get the current foreground app bundle name."""
        output = await self._run_shell("aa", "dump", "-a")
        # Parse the current ability info
        match = re.search(r"bundle name \[([^\]]+)\]", output)
        if match:
            return match.group(1)
        return ""

    async def go_back(self) -> None:
        """Press back button."""
        await self.press_key("back")

    async def go_home(self) -> None:
        """Press home button."""
        await self.press_key("home")
