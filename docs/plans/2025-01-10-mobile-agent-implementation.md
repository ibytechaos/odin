# Mobile Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate mobile phone automation capabilities from dexter_mobile to Odin framework with three execution modes (ReAct, Plan+Execute, Hierarchical).

**Architecture:** Two-layer design - Plugin layer for atomic operations (click, swipe, input) using @tool decorator, Agent layer for execution logic. Controller abstraction enables multi-platform support (ADB/HDC/iOS).

**Tech Stack:** Python 3.14+, AsyncOpenAI, Pydantic, adb shell commands, @tool decorator pattern

---

## Phase 1: Foundation (Controller Layer)

### Task 1: Create directory structure

**Files:**
- Create: `src/odin/plugins/builtin/mobile/__init__.py`
- Create: `src/odin/plugins/builtin/mobile/controllers/__init__.py`
- Create: `src/odin/agents/mobile/__init__.py`

**Step 1: Create mobile plugin directory**

```bash
mkdir -p src/odin/plugins/builtin/mobile/controllers
mkdir -p src/odin/plugins/builtin/mobile/configs
mkdir -p src/odin/agents/mobile
```

**Step 2: Create __init__.py files**

`src/odin/plugins/builtin/mobile/__init__.py`:
```python
"""Mobile automation plugin for Odin framework."""

from odin.plugins.builtin.mobile.plugin import MobilePlugin

__all__ = ["MobilePlugin"]
```

`src/odin/plugins/builtin/mobile/controllers/__init__.py`:
```python
"""Mobile device controllers."""

from odin.plugins.builtin.mobile.controllers.base import BaseController
from odin.plugins.builtin.mobile.controllers.adb import ADBController

__all__ = ["BaseController", "ADBController"]
```

`src/odin/agents/mobile/__init__.py`:
```python
"""Mobile agents for Odin framework."""

from odin.agents.mobile.base import MobileAgentBase
from odin.agents.mobile.react import MobileReActAgent

__all__ = ["MobileAgentBase", "MobileReActAgent"]
```

**Step 3: Commit**

```bash
git add src/odin/plugins/builtin/mobile src/odin/agents/mobile
git commit -m "feat(mobile): create directory structure for mobile plugin and agents"
```

---

### Task 2: Implement coordinate conversion utilities

**Files:**
- Create: `src/odin/plugins/builtin/mobile/coordinates.py`
- Create: `tests/unit/plugins/mobile/test_coordinates.py`

**Step 1: Write failing tests**

`tests/unit/plugins/mobile/test_coordinates.py`:
```python
"""Tests for coordinate conversion utilities."""

import pytest

from odin.plugins.builtin.mobile.coordinates import normalize_coordinate, CoordinateSystem


class TestNormalizeCoordinate:
    """Test normalize_coordinate function."""

    def test_normalized_0_to_1(self):
        """0.5 on 1080px screen = 540px."""
        result = normalize_coordinate(0.5, 1080)
        assert result == 540

    def test_normalized_zero(self):
        """0.0 = 0px."""
        result = normalize_coordinate(0.0, 1920)
        assert result == 0

    def test_normalized_one(self):
        """1.0 = full dimension."""
        result = normalize_coordinate(1.0, 1080)
        assert result == 1080

    def test_thousandths_500(self):
        """500 (thousandths) on 1080px = 540px."""
        result = normalize_coordinate(500, 1080)
        assert result == 540

    def test_thousandths_1000(self):
        """1000 (thousandths) on 1080px = 1080px."""
        result = normalize_coordinate(1000, 1080)
        assert result == 1080

    def test_pixel_value(self):
        """Values > 1000 are treated as pixels."""
        result = normalize_coordinate(1500, 1080)
        assert result == 1079  # Clamped to dimension - 1

    def test_pixel_exact(self):
        """Exact pixel within bounds."""
        result = normalize_coordinate(1001, 1920)
        assert result == 1001

    def test_negative_clamps_to_zero(self):
        """Negative values clamp to 0."""
        result = normalize_coordinate(-0.1, 1080)
        assert result == 0


class TestCoordinateSystem:
    """Test CoordinateSystem detection."""

    def test_detect_normalized(self):
        """Values 0-1 are normalized."""
        assert CoordinateSystem.detect(0.5) == CoordinateSystem.NORMALIZED
        assert CoordinateSystem.detect(0.0) == CoordinateSystem.NORMALIZED
        assert CoordinateSystem.detect(1.0) == CoordinateSystem.NORMALIZED

    def test_detect_thousandths(self):
        """Values 1-1000 are thousandths."""
        assert CoordinateSystem.detect(500) == CoordinateSystem.THOUSANDTHS
        assert CoordinateSystem.detect(1.1) == CoordinateSystem.THOUSANDTHS
        assert CoordinateSystem.detect(1000) == CoordinateSystem.THOUSANDTHS

    def test_detect_pixels(self):
        """Values > 1000 are pixels."""
        assert CoordinateSystem.detect(1001) == CoordinateSystem.PIXELS
        assert CoordinateSystem.detect(1920) == CoordinateSystem.PIXELS
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/plugins/mobile/test_coordinates.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'odin.plugins.builtin.mobile'"

**Step 3: Implement coordinates.py**

`src/odin/plugins/builtin/mobile/coordinates.py`:
```python
"""Coordinate conversion utilities for mobile automation.

Supports three coordinate systems:
- Normalized (0-1): Percentage of screen dimension
- Thousandths (1-1000): Per-mille of screen dimension
- Pixels (>1000): Absolute pixel values
"""

from enum import Enum


class CoordinateSystem(str, Enum):
    """Coordinate system types."""

    NORMALIZED = "normalized"  # 0.0 - 1.0
    THOUSANDTHS = "thousandths"  # 1 - 1000
    PIXELS = "pixels"  # > 1000

    @classmethod
    def detect(cls, value: float) -> "CoordinateSystem":
        """Detect coordinate system from value.

        Args:
            value: Coordinate value

        Returns:
            Detected coordinate system
        """
        if 0 <= value <= 1:
            return cls.NORMALIZED
        elif 1 < value <= 1000:
            return cls.THOUSANDTHS
        else:
            return cls.PIXELS


def normalize_coordinate(value: float, dimension: int) -> int:
    """Convert coordinate value to pixel coordinate.

    Supports three input formats:
    - 0-1: Normalized coordinate, multiply by dimension
    - 1-1000: Thousandths, divide by 1000 then multiply by dimension
    - >1000: Absolute pixel value, clamp to valid range

    Args:
        value: Input coordinate value
        dimension: Screen dimension (width or height) in pixels

    Returns:
        Pixel coordinate value (0 to dimension-1)
    """
    # Handle negative values
    if value < 0:
        return 0

    system = CoordinateSystem.detect(value)

    if system == CoordinateSystem.NORMALIZED:
        pixel = int(value * dimension)
    elif system == CoordinateSystem.THOUSANDTHS:
        pixel = int(value / 1000 * dimension)
    else:  # PIXELS
        pixel = int(value)

    # Clamp to valid range
    return max(0, min(pixel, dimension - 1))
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/plugins/mobile/test_coordinates.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/odin/plugins/builtin/mobile/coordinates.py tests/unit/plugins/mobile/
git commit -m "feat(mobile): add coordinate conversion utilities with three systems"
```

---

### Task 3: Implement BaseController abstract class

**Files:**
- Create: `src/odin/plugins/builtin/mobile/controllers/base.py`
- Create: `tests/unit/plugins/mobile/controllers/test_base.py`

**Step 1: Write failing tests**

`tests/unit/plugins/mobile/controllers/test_base.py`:
```python
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
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/plugins/mobile/controllers/test_base.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement base.py**

`src/odin/plugins/builtin/mobile/controllers/base.py`:
```python
"""Base controller interface for mobile device automation."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ControllerConfig(BaseModel):
    """Controller configuration."""

    device_id: str | None = Field(default=None, description="Device serial number")
    timeout_ms: int = Field(default=30000, description="Command timeout in milliseconds")
    retry_count: int = Field(default=3, description="Number of retries on failure")


class BaseController(ABC):
    """Abstract base class for mobile device controllers.

    Defines the standard interface for device automation operations.
    Platform-specific implementations (ADB, HDC, iOS) inherit from this.
    """

    def __init__(self, config: ControllerConfig) -> None:
        """Initialize controller.

        Args:
            config: Controller configuration
        """
        self.config = config
        self._screen_size: tuple[int, int] | None = None

    @abstractmethod
    async def tap(self, x: int, y: int) -> None:
        """Tap at specified coordinates.

        Args:
            x: X coordinate in pixels
            y: Y coordinate in pixels
        """

    @abstractmethod
    async def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        """Long press at specified coordinates.

        Args:
            x: X coordinate in pixels
            y: Y coordinate in pixels
            duration_ms: Press duration in milliseconds
        """

    @abstractmethod
    async def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300
    ) -> None:
        """Swipe from one point to another.

        Args:
            x1: Start X coordinate
            y1: Start Y coordinate
            x2: End X coordinate
            y2: End Y coordinate
            duration_ms: Swipe duration in milliseconds
        """

    @abstractmethod
    async def input_text(self, text: str) -> None:
        """Input text on device.

        Args:
            text: Text to input
        """

    @abstractmethod
    async def press_key(self, key: str) -> None:
        """Press a key.

        Args:
            key: Key name (back, home, enter, volume_up, volume_down, etc.)
        """

    @abstractmethod
    async def screenshot(self) -> bytes:
        """Take a screenshot.

        Returns:
            PNG image bytes
        """

    @abstractmethod
    async def get_screen_size(self) -> tuple[int, int]:
        """Get screen dimensions.

        Returns:
            Tuple of (width, height) in pixels
        """

    @abstractmethod
    async def open_app(self, package: str, activity: str | None = None) -> None:
        """Open an application.

        Args:
            package: Package name or bundle ID
            activity: Activity name (Android only)
        """

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if device is connected.

        Returns:
            True if device is connected and responsive
        """

    async def get_cached_screen_size(self) -> tuple[int, int]:
        """Get screen size with caching.

        Returns:
            Tuple of (width, height) in pixels
        """
        if self._screen_size is None:
            self._screen_size = await self.get_screen_size()
        return self._screen_size
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/plugins/mobile/controllers/test_base.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/odin/plugins/builtin/mobile/controllers/base.py tests/unit/plugins/mobile/controllers/
git commit -m "feat(mobile): add BaseController abstract interface"
```

---

### Task 4: Implement ADBController

**Files:**
- Create: `src/odin/plugins/builtin/mobile/controllers/adb.py`
- Create: `tests/unit/plugins/mobile/controllers/test_adb.py`

**Step 1: Write failing tests**

`tests/unit/plugins/mobile/controllers/test_adb.py`:
```python
"""Tests for ADBController."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from odin.plugins.builtin.mobile.controllers.adb import ADBController, ADBConfig


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
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/plugins/mobile/controllers/test_adb.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement adb.py**

`src/odin/plugins/builtin/mobile/controllers/adb.py`:
```python
"""ADB (Android Debug Bridge) controller implementation."""

import asyncio
import re
import shlex

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
                raise ValueError(f"Unknown key: {key}")
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
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/plugins/mobile/controllers/test_adb.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/odin/plugins/builtin/mobile/controllers/adb.py tests/unit/plugins/mobile/controllers/test_adb.py
git commit -m "feat(mobile): implement ADBController for Android device automation"
```

---

## Phase 2: Plugin Layer

### Task 5: Create app mapping configuration

**Files:**
- Create: `src/odin/plugins/builtin/mobile/configs/app_map.yaml`
- Create: `src/odin/plugins/builtin/mobile/app_registry.py`
- Create: `tests/unit/plugins/mobile/test_app_registry.py`

**Step 1: Create app_map.yaml**

`src/odin/plugins/builtin/mobile/configs/app_map.yaml`:
```yaml
# Android Apps
android:
  wechat:
    package: com.tencent.mm
    activity: .ui.LauncherUI
    aliases:
      - 微信
      - WeChat
      - weixin

  alipay:
    package: com.eg.android.AlipayGphone
    activity: .AlipayLogin
    aliases:
      - 支付宝
      - Alipay
      - zhifubao

  taobao:
    package: com.taobao.taobao
    activity: com.taobao.tao.TBMainActivity
    aliases:
      - 淘宝
      - Taobao

  douyin:
    package: com.ss.android.ugc.aweme
    activity: .splash.SplashActivity
    aliases:
      - 抖音
      - TikTok
      - Douyin

  xiaohongshu:
    package: com.xingin.xhs
    activity: .activity.SplashActivity
    aliases:
      - 小红书
      - RedNote
      - XHS

  settings:
    package: com.android.settings
    activity: .Settings
    aliases:
      - 设置
      - Settings

  chrome:
    package: com.android.chrome
    activity: com.google.android.apps.chrome.Main
    aliases:
      - Chrome
      - 浏览器

  camera:
    package: com.android.camera
    activity: .Camera
    aliases:
      - 相机
      - Camera

# Harmony OS Apps
harmony:
  wechat:
    bundle: com.tencent.mm
    module: entry
    ability: MainAbility
    aliases:
      - 微信
      - WeChat

# iOS Apps
ios:
  wechat:
    bundle_id: com.tencent.xin
    aliases:
      - 微信
      - WeChat
```

**Step 2: Write failing tests for app_registry**

`tests/unit/plugins/mobile/test_app_registry.py`:
```python
"""Tests for AppRegistry."""

import pytest
from pathlib import Path

from odin.plugins.builtin.mobile.app_registry import AppRegistry, AppInfo


class TestAppInfo:
    """Test AppInfo model."""

    def test_android_app(self):
        """Android app has package and optional activity."""
        app = AppInfo(
            name="wechat",
            platform="android",
            package="com.tencent.mm",
            activity=".ui.LauncherUI",
            aliases=["微信", "WeChat"],
        )
        assert app.package == "com.tencent.mm"
        assert app.activity == ".ui.LauncherUI"

    def test_ios_app(self):
        """iOS app has bundle_id."""
        app = AppInfo(
            name="wechat",
            platform="ios",
            bundle_id="com.tencent.xin",
            aliases=["微信"],
        )
        assert app.bundle_id == "com.tencent.xin"


class TestAppRegistry:
    """Test AppRegistry."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create registry with test config."""
        config_file = tmp_path / "app_map.yaml"
        config_file.write_text("""
android:
  wechat:
    package: com.tencent.mm
    activity: .ui.LauncherUI
    aliases:
      - 微信
      - WeChat
  alipay:
    package: com.eg.android.AlipayGphone
    aliases:
      - 支付宝
""")
        return AppRegistry(config_file)

    def test_lookup_by_name(self, registry):
        """Lookup app by exact name."""
        app = registry.lookup("wechat", platform="android")
        assert app is not None
        assert app.package == "com.tencent.mm"

    def test_lookup_by_alias_chinese(self, registry):
        """Lookup app by Chinese alias."""
        app = registry.lookup("微信", platform="android")
        assert app is not None
        assert app.name == "wechat"

    def test_lookup_by_alias_english(self, registry):
        """Lookup app by English alias."""
        app = registry.lookup("WeChat", platform="android")
        assert app is not None
        assert app.name == "wechat"

    def test_lookup_case_insensitive(self, registry):
        """Lookup is case insensitive."""
        app = registry.lookup("WECHAT", platform="android")
        assert app is not None
        assert app.name == "wechat"

    def test_lookup_not_found(self, registry):
        """Lookup returns None for unknown app."""
        app = registry.lookup("unknown_app", platform="android")
        assert app is None

    def test_list_apps(self, registry):
        """List all apps for a platform."""
        apps = registry.list_apps(platform="android")
        assert len(apps) == 2
        names = [a.name for a in apps]
        assert "wechat" in names
        assert "alipay" in names
```

**Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/unit/plugins/mobile/test_app_registry.py -v
```

Expected: FAIL

**Step 4: Implement app_registry.py**

`src/odin/plugins/builtin/mobile/app_registry.py`:
```python
"""App registry for mobile automation.

Provides app lookup by name or alias across platforms.
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


Platform = Literal["android", "harmony", "ios"]


class AppInfo(BaseModel):
    """Application information."""

    name: str = Field(..., description="App identifier name")
    platform: Platform = Field(..., description="Target platform")
    package: str | None = Field(default=None, description="Android package name")
    activity: str | None = Field(default=None, description="Android activity")
    bundle: str | None = Field(default=None, description="Harmony bundle name")
    module: str | None = Field(default=None, description="Harmony module")
    ability: str | None = Field(default=None, description="Harmony ability")
    bundle_id: str | None = Field(default=None, description="iOS bundle ID")
    aliases: list[str] = Field(default_factory=list, description="App name aliases")


class AppRegistry:
    """Registry for looking up app information.

    Loads app configurations from YAML file and provides
    lookup by name or alias.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize registry.

        Args:
            config_path: Path to app_map.yaml. If None, uses default.
        """
        if config_path is None:
            config_path = Path(__file__).parent / "configs" / "app_map.yaml"

        self._apps: dict[Platform, dict[str, AppInfo]] = {
            "android": {},
            "harmony": {},
            "ios": {},
        }
        self._alias_map: dict[Platform, dict[str, str]] = {
            "android": {},
            "harmony": {},
            "ios": {},
        }

        if config_path.exists():
            self._load_config(config_path)

    def _load_config(self, config_path: Path) -> None:
        """Load app configuration from YAML."""
        with open(config_path) as f:
            data = yaml.safe_load(f)

        for platform in ["android", "harmony", "ios"]:
            platform_data = data.get(platform, {})
            for name, app_data in platform_data.items():
                aliases = app_data.pop("aliases", [])
                app = AppInfo(
                    name=name,
                    platform=platform,  # type: ignore
                    aliases=aliases,
                    **app_data,
                )
                self._apps[platform][name] = app  # type: ignore

                # Build alias map
                self._alias_map[platform][name.lower()] = name  # type: ignore
                for alias in aliases:
                    self._alias_map[platform][alias.lower()] = name  # type: ignore

    def lookup(self, name_or_alias: str, platform: Platform) -> AppInfo | None:
        """Look up app by name or alias.

        Args:
            name_or_alias: App name or alias (case insensitive)
            platform: Target platform

        Returns:
            AppInfo if found, None otherwise
        """
        normalized = name_or_alias.lower()
        app_name = self._alias_map.get(platform, {}).get(normalized)
        if app_name:
            return self._apps[platform].get(app_name)
        return None

    def list_apps(self, platform: Platform) -> list[AppInfo]:
        """List all apps for a platform.

        Args:
            platform: Target platform

        Returns:
            List of AppInfo objects
        """
        return list(self._apps[platform].values())
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/unit/plugins/mobile/test_app_registry.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/odin/plugins/builtin/mobile/configs/ src/odin/plugins/builtin/mobile/app_registry.py tests/unit/plugins/mobile/test_app_registry.py
git commit -m "feat(mobile): add app registry with YAML config for multi-platform app lookup"
```

---

### Task 6: Implement HumanInteractionHandler

**Files:**
- Create: `src/odin/plugins/builtin/mobile/interaction.py`
- Create: `tests/unit/plugins/mobile/test_interaction.py`

**Step 1: Write failing tests**

`tests/unit/plugins/mobile/test_interaction.py`:
```python
"""Tests for HumanInteractionHandler."""

import pytest
from unittest.mock import patch, MagicMock

from odin.plugins.builtin.mobile.interaction import (
    HumanInteractionHandler,
    CLIInteractionHandler,
    InteractionType,
)


class TestInteractionType:
    """Test InteractionType enum."""

    def test_values(self):
        """Enum has expected values."""
        assert InteractionType.TEXT == "text"
        assert InteractionType.CONFIRMATION == "confirmation"
        assert InteractionType.CHOICE == "choice"


class TestCLIInteractionHandler:
    """Test CLIInteractionHandler."""

    @pytest.fixture
    def handler(self):
        """Create CLI handler."""
        return CLIInteractionHandler()

    @pytest.mark.asyncio
    async def test_request_text_input(self, handler):
        """Request text input from user."""
        with patch("builtins.input", return_value="test response"):
            result = await handler.request_input(
                "Enter something:",
                input_type=InteractionType.TEXT,
            )
            assert result == "test response"

    @pytest.mark.asyncio
    async def test_request_confirmation_yes(self, handler):
        """Confirmation returns 'yes' for y input."""
        with patch("builtins.input", return_value="y"):
            result = await handler.request_input(
                "Continue?",
                input_type=InteractionType.CONFIRMATION,
            )
            assert result == "yes"

    @pytest.mark.asyncio
    async def test_request_confirmation_no(self, handler):
        """Confirmation returns 'no' for n input."""
        with patch("builtins.input", return_value="n"):
            result = await handler.request_input(
                "Continue?",
                input_type=InteractionType.CONFIRMATION,
            )
            assert result == "no"

    @pytest.mark.asyncio
    async def test_request_choice(self, handler):
        """Choice returns selected option."""
        with patch("builtins.input", return_value="2"):
            result = await handler.request_input(
                "Select option:",
                input_type=InteractionType.CHOICE,
                choices=["Option A", "Option B", "Option C"],
            )
            assert result == "Option B"

    @pytest.mark.asyncio
    async def test_request_choice_invalid_defaults_first(self, handler):
        """Invalid choice defaults to first option."""
        with patch("builtins.input", return_value="invalid"):
            result = await handler.request_input(
                "Select option:",
                input_type=InteractionType.CHOICE,
                choices=["Option A", "Option B"],
            )
            assert result == "Option A"
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/plugins/mobile/test_interaction.py -v
```

Expected: FAIL

**Step 3: Implement interaction.py**

`src/odin/plugins/builtin/mobile/interaction.py`:
```python
"""Human interaction handlers for mobile automation.

Provides abstraction for requesting human input during automation.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Protocol


class InteractionType(str, Enum):
    """Types of human interaction."""

    TEXT = "text"
    CONFIRMATION = "confirmation"
    CHOICE = "choice"


class HumanInteractionHandler(Protocol):
    """Protocol for human interaction handlers.

    Implementations can be CLI, GUI, WebSocket, etc.
    """

    async def request_input(
        self,
        prompt: str,
        input_type: InteractionType = InteractionType.TEXT,
        timeout: int | None = None,
        choices: list[str] | None = None,
    ) -> str | None:
        """Request input from human.

        Args:
            prompt: Message to display to user
            input_type: Type of input expected
            timeout: Timeout in seconds (None = no timeout)
            choices: List of choices for CHOICE type

        Returns:
            User response or None if cancelled/timeout
        """
        ...


class CLIInteractionHandler:
    """Command-line interaction handler.

    Uses stdin/stdout for human interaction.
    """

    async def request_input(
        self,
        prompt: str,
        input_type: InteractionType = InteractionType.TEXT,
        timeout: int | None = None,
        choices: list[str] | None = None,
    ) -> str | None:
        """Request input via CLI.

        Args:
            prompt: Message to display
            input_type: Type of input
            timeout: Not implemented for CLI
            choices: Choices for CHOICE type

        Returns:
            User response
        """
        print(f"\n[Human Input Required] {prompt}")

        if input_type == InteractionType.TEXT:
            return input("> ")

        elif input_type == InteractionType.CONFIRMATION:
            print("(y/n)")
            response = input("> ").strip().lower()
            return "yes" if response in ("y", "yes", "是", "确认") else "no"

        elif input_type == InteractionType.CHOICE:
            if not choices:
                return input("> ")

            for i, choice in enumerate(choices, 1):
                print(f"  {i}. {choice}")

            response = input("> ").strip()
            try:
                index = int(response) - 1
                if 0 <= index < len(choices):
                    return choices[index]
            except ValueError:
                pass
            # Default to first choice
            return choices[0]

        return input("> ")


class GUIInteractionHandler:
    """GUI interaction handler using Tkinter.

    Displays dialog boxes for human interaction.
    """

    async def request_input(
        self,
        prompt: str,
        input_type: InteractionType = InteractionType.TEXT,
        timeout: int | None = None,
        choices: list[str] | None = None,
    ) -> str | None:
        """Request input via GUI dialog.

        Args:
            prompt: Message to display
            input_type: Type of input
            timeout: Not implemented for GUI
            choices: Choices for CHOICE type

        Returns:
            User response or None if cancelled
        """
        import tkinter as tk
        from tkinter import simpledialog, messagebox

        root = tk.Tk()
        root.withdraw()

        try:
            if input_type == InteractionType.TEXT:
                return simpledialog.askstring("Human Input", prompt)

            elif input_type == InteractionType.CONFIRMATION:
                result = messagebox.askyesno("Confirmation", prompt)
                return "yes" if result else "no"

            elif input_type == InteractionType.CHOICE:
                if not choices:
                    return simpledialog.askstring("Human Input", prompt)

                # Simple choice dialog
                choice_prompt = f"{prompt}\n\n" + "\n".join(
                    f"{i}. {c}" for i, c in enumerate(choices, 1)
                )
                response = simpledialog.askstring("Select Option", choice_prompt)
                if response:
                    try:
                        index = int(response) - 1
                        if 0 <= index < len(choices):
                            return choices[index]
                    except ValueError:
                        pass
                return choices[0] if choices else None

            return simpledialog.askstring("Human Input", prompt)
        finally:
            root.destroy()
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/plugins/mobile/test_interaction.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/odin/plugins/builtin/mobile/interaction.py tests/unit/plugins/mobile/test_interaction.py
git commit -m "feat(mobile): add human interaction handlers (CLI and GUI)"
```

---

### Task 7: Implement MobilePlugin with tools

**Files:**
- Create: `src/odin/plugins/builtin/mobile/plugin.py`
- Create: `tests/unit/plugins/mobile/test_plugin.py`

**Step 1: Write failing tests**

`tests/unit/plugins/mobile/test_plugin.py`:
```python
"""Tests for MobilePlugin."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from odin.plugins.builtin.mobile.plugin import MobilePlugin, MobilePluginConfig
from odin.plugins.builtin.mobile.controllers.base import ControllerConfig
from odin.plugins.builtin.mobile.controllers.adb import ADBController, ADBConfig


class TestMobilePluginConfig:
    """Test MobilePluginConfig."""

    def test_default_values(self):
        """Default config uses adb controller."""
        config = MobilePluginConfig()
        assert config.controller_type == "adb"
        assert config.tool_delay_ms == 400

    def test_custom_values(self):
        """Custom config values."""
        config = MobilePluginConfig(
            controller_type="hdc",
            tool_delay_ms=200,
            device_id="test-device",
        )
        assert config.controller_type == "hdc"
        assert config.tool_delay_ms == 200
        assert config.device_id == "test-device"


class TestMobilePlugin:
    """Test MobilePlugin."""

    @pytest.fixture
    def mock_controller(self):
        """Create mock controller."""
        controller = AsyncMock()
        controller.get_cached_screen_size = AsyncMock(return_value=(1080, 1920))
        controller.tap = AsyncMock()
        controller.swipe = AsyncMock()
        controller.input_text = AsyncMock()
        controller.press_key = AsyncMock()
        controller.screenshot = AsyncMock(return_value=b"fake_png_data")
        controller.open_app = AsyncMock()
        return controller

    @pytest.fixture
    def plugin(self, mock_controller):
        """Create plugin with mock controller."""
        config = MobilePluginConfig(device_id="test-device")
        plugin = MobilePlugin(config)
        plugin._controller = mock_controller
        return plugin

    def test_name(self, plugin):
        """Plugin has correct name."""
        assert plugin.name == "mobile"

    def test_version(self, plugin):
        """Plugin has version."""
        assert plugin.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_tools(self, plugin):
        """Plugin provides expected tools."""
        tools = await plugin.get_tools()
        tool_names = [t.name for t in tools]
        assert "click" in tool_names
        assert "input_text" in tool_names
        assert "scroll" in tool_names
        assert "screenshot" in tool_names
        assert "open_app" in tool_names
        assert "press_key" in tool_names
        assert "wait" in tool_names
        assert "human_interact" in tool_names

    @pytest.mark.asyncio
    async def test_click_normalizes_coordinates(self, plugin, mock_controller):
        """click() normalizes coordinates before calling controller."""
        result = await plugin.click(x=0.5, y=0.5)
        mock_controller.tap.assert_called_once_with(540, 960)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_click_pixel_coordinates(self, plugin, mock_controller):
        """click() handles pixel coordinates."""
        result = await plugin.click(x=1080, y=1920)
        # Should be clamped to screen bounds
        mock_controller.tap.assert_called_once()

    @pytest.mark.asyncio
    async def test_scroll_calls_swipe(self, plugin, mock_controller):
        """scroll() calls controller.swipe()."""
        result = await plugin.scroll(x1=0.5, y1=0.7, x2=0.5, y2=0.3, duration_ms=500)
        mock_controller.swipe.assert_called_once()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_input_text_calls_controller(self, plugin, mock_controller):
        """input_text() calls controller.input_text()."""
        result = await plugin.input_text(text="hello world", press_enter=False)
        mock_controller.input_text.assert_called_once_with("hello world")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_input_text_with_enter(self, plugin, mock_controller):
        """input_text() with press_enter calls press_key."""
        result = await plugin.input_text(text="hello", press_enter=True)
        mock_controller.input_text.assert_called_once_with("hello")
        mock_controller.press_key.assert_called_once_with("enter")

    @pytest.mark.asyncio
    async def test_screenshot_returns_base64(self, plugin, mock_controller):
        """screenshot() returns base64 encoded image."""
        result = await plugin.screenshot()
        assert result["success"] is True
        assert "image_base64" in result
        assert result["width"] == 1080
        assert result["height"] == 1920

    @pytest.mark.asyncio
    async def test_open_app_uses_registry(self, plugin, mock_controller):
        """open_app() looks up app in registry."""
        with patch.object(plugin, "_app_registry") as mock_registry:
            mock_app = MagicMock()
            mock_app.package = "com.tencent.mm"
            mock_app.activity = ".ui.LauncherUI"
            mock_registry.lookup.return_value = mock_app

            result = await plugin.open_app(app_name="微信")
            mock_registry.lookup.assert_called_once()
            mock_controller.open_app.assert_called_once_with(
                "com.tencent.mm", ".ui.LauncherUI"
            )

    @pytest.mark.asyncio
    async def test_press_key_calls_controller(self, plugin, mock_controller):
        """press_key() calls controller.press_key()."""
        result = await plugin.press_key(key="back")
        mock_controller.press_key.assert_called_once_with("back")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_wait_delays_execution(self, plugin):
        """wait() delays for specified duration."""
        import time
        start = time.time()
        result = await plugin.wait(duration_ms=100)
        elapsed = time.time() - start
        assert elapsed >= 0.1
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_variable_storage_write_read(self, plugin):
        """variable_storage() can write and read values."""
        # Write
        result = await plugin.variable_storage(action="write", key="test_key", value="test_value")
        assert result["success"] is True

        # Read
        result = await plugin.variable_storage(action="read", key="test_key")
        assert result["success"] is True
        assert result["value"] == "test_value"

    @pytest.mark.asyncio
    async def test_variable_storage_list(self, plugin):
        """variable_storage() can list all variables."""
        await plugin.variable_storage(action="write", key="key1", value="val1")
        await plugin.variable_storage(action="write", key="key2", value="val2")

        result = await plugin.variable_storage(action="list")
        assert result["success"] is True
        assert "key1" in result["variables"]
        assert "key2" in result["variables"]
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/plugins/mobile/test_plugin.py -v
```

Expected: FAIL

**Step 3: Implement plugin.py**

`src/odin/plugins/builtin/mobile/plugin.py`:
```python
"""Mobile automation plugin for Odin framework.

Provides tools for automating mobile device interactions.
"""

import asyncio
import base64
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from odin.decorators import tool
from odin.plugins.base import DecoratorPlugin, PluginConfig

from odin.plugins.builtin.mobile.app_registry import AppRegistry
from odin.plugins.builtin.mobile.controllers.adb import ADBController, ADBConfig
from odin.plugins.builtin.mobile.controllers.base import BaseController
from odin.plugins.builtin.mobile.coordinates import normalize_coordinate
from odin.plugins.builtin.mobile.interaction import (
    CLIInteractionHandler,
    GUIInteractionHandler,
    HumanInteractionHandler,
    InteractionType,
)


class MobilePluginConfig(BaseModel):
    """Mobile plugin configuration."""

    controller_type: Literal["adb", "hdc", "ios"] = Field(
        default="adb", description="Controller type"
    )
    device_id: str | None = Field(default=None, description="Device serial number")
    adb_path: str = Field(default="adb", description="Path to adb executable")
    tool_delay_ms: int = Field(
        default=400, description="Delay after each tool execution (ms)"
    )
    interaction_type: Literal["cli", "gui"] = Field(
        default="cli", description="Human interaction handler type"
    )


class MobilePlugin(DecoratorPlugin):
    """Mobile device automation plugin.

    Provides tools for:
    - Screen interactions (click, scroll, input)
    - App management (open_app)
    - Device control (screenshot, press_key)
    - Human interaction (human_interact)
    - State management (variable_storage)
    """

    def __init__(self, config: MobilePluginConfig | None = None) -> None:
        """Initialize mobile plugin.

        Args:
            config: Plugin configuration
        """
        super().__init__(PluginConfig())
        self._config = config or MobilePluginConfig()
        self._controller: BaseController | None = None
        self._app_registry = AppRegistry()
        self._variables: dict[str, str] = {}
        self._interaction_handler: HumanInteractionHandler | None = None

    @property
    def name(self) -> str:
        """Plugin name."""
        return "mobile"

    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """Plugin description."""
        return "Mobile device automation tools for Android, Harmony, and iOS"

    async def initialize(self) -> None:
        """Initialize plugin resources."""
        await super().initialize()
        self._controller = await self._create_controller()
        self._interaction_handler = self._create_interaction_handler()

    async def _create_controller(self) -> BaseController:
        """Create device controller based on config."""
        if self._config.controller_type == "adb":
            config = ADBConfig(
                device_id=self._config.device_id,
                adb_path=self._config.adb_path,
            )
            return ADBController(config)
        # TODO: Add HDC and iOS controllers
        raise ValueError(f"Unknown controller type: {self._config.controller_type}")

    def _create_interaction_handler(self) -> HumanInteractionHandler:
        """Create interaction handler based on config."""
        if self._config.interaction_type == "gui":
            return GUIInteractionHandler()
        return CLIInteractionHandler()

    async def _get_controller(self) -> BaseController:
        """Get controller, initializing if needed."""
        if self._controller is None:
            self._controller = await self._create_controller()
        return self._controller

    async def _apply_delay(self) -> None:
        """Apply configured delay after tool execution."""
        if self._config.tool_delay_ms > 0:
            await asyncio.sleep(self._config.tool_delay_ms / 1000)

    @tool(description="点击屏幕指定位置")
    async def click(
        self,
        x: Annotated[float, Field(description="X坐标，支持0-1归一化/0-1000千分比/像素值")],
        y: Annotated[float, Field(description="Y坐标，支持0-1归一化/0-1000千分比/像素值")],
        count: Annotated[int, Field(description="点击次数")] = 1,
    ) -> dict[str, Any]:
        """Click at specified screen position."""
        controller = await self._get_controller()
        width, height = await controller.get_cached_screen_size()

        px = normalize_coordinate(x, width)
        py = normalize_coordinate(y, height)

        for _ in range(count):
            await controller.tap(px, py)
            if count > 1:
                await asyncio.sleep(0.1)

        await self._apply_delay()
        return {"success": True, "x": px, "y": py, "count": count}

    @tool(description="长按屏幕指定位置")
    async def long_press(
        self,
        x: Annotated[float, Field(description="X坐标")],
        y: Annotated[float, Field(description="Y坐标")],
        duration_ms: Annotated[int, Field(description="长按持续时间(毫秒)")] = 1000,
    ) -> dict[str, Any]:
        """Long press at specified position."""
        controller = await self._get_controller()
        width, height = await controller.get_cached_screen_size()

        px = normalize_coordinate(x, width)
        py = normalize_coordinate(y, height)

        await controller.long_press(px, py, duration_ms)
        await self._apply_delay()
        return {"success": True, "x": px, "y": py, "duration_ms": duration_ms}

    @tool(description="滑动屏幕")
    async def scroll(
        self,
        x1: Annotated[float, Field(description="起点X坐标")],
        y1: Annotated[float, Field(description="起点Y坐标")],
        x2: Annotated[float, Field(description="终点X坐标")],
        y2: Annotated[float, Field(description="终点Y坐标")],
        duration_ms: Annotated[int, Field(description="滑动持续时间(毫秒)")] = 300,
    ) -> dict[str, Any]:
        """Swipe/scroll from one point to another."""
        controller = await self._get_controller()
        width, height = await controller.get_cached_screen_size()

        px1 = normalize_coordinate(x1, width)
        py1 = normalize_coordinate(y1, height)
        px2 = normalize_coordinate(x2, width)
        py2 = normalize_coordinate(y2, height)

        await controller.swipe(px1, py1, px2, py2, duration_ms)
        await self._apply_delay()
        return {
            "success": True,
            "from": {"x": px1, "y": py1},
            "to": {"x": px2, "y": py2},
            "duration_ms": duration_ms,
        }

    @tool(description="输入文本")
    async def input_text(
        self,
        text: Annotated[str, Field(description="要输入的文本")],
        press_enter: Annotated[bool, Field(description="输入后是否按回车")] = False,
    ) -> dict[str, Any]:
        """Input text on device."""
        controller = await self._get_controller()
        await controller.input_text(text)

        if press_enter:
            await controller.press_key("enter")

        await self._apply_delay()
        return {"success": True, "text": text, "press_enter": press_enter}

    @tool(description="截图并返回当前屏幕状态")
    async def screenshot(self) -> dict[str, Any]:
        """Take screenshot and return base64 encoded image."""
        controller = await self._get_controller()
        image_bytes = await controller.screenshot()
        width, height = await controller.get_cached_screen_size()

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        return {
            "success": True,
            "image_base64": image_base64,
            "width": width,
            "height": height,
            "format": "png",
        }

    @tool(description="打开应用")
    async def open_app(
        self,
        app_name: Annotated[str, Field(description="应用名称，支持别名如'微信'/'WeChat'")],
    ) -> dict[str, Any]:
        """Open an application by name or alias."""
        controller = await self._get_controller()

        # Determine platform from controller type
        platform = "android"  # TODO: Get from controller
        if self._config.controller_type == "hdc":
            platform = "harmony"
        elif self._config.controller_type == "ios":
            platform = "ios"

        app = self._app_registry.lookup(app_name, platform=platform)  # type: ignore
        if app is None:
            return {
                "success": False,
                "error": f"App not found: {app_name}",
            }

        if platform == "android":
            await controller.open_app(app.package, app.activity)  # type: ignore
        # TODO: Handle other platforms

        await self._apply_delay()
        return {
            "success": True,
            "app_name": app.name,
            "package": app.package,
        }

    @tool(description="按键操作")
    async def press_key(
        self,
        key: Annotated[
            str,
            Field(description="按键名称: back/home/enter/volume_up/volume_down"),
        ],
    ) -> dict[str, Any]:
        """Press a device key."""
        controller = await self._get_controller()
        await controller.press_key(key)
        await self._apply_delay()
        return {"success": True, "key": key}

    @tool(description="等待指定时间")
    async def wait(
        self,
        duration_ms: Annotated[int, Field(description="等待时间(毫秒)")],
    ) -> dict[str, Any]:
        """Wait for specified duration."""
        await asyncio.sleep(duration_ms / 1000)
        return {"success": True, "duration_ms": duration_ms}

    @tool(description="请求人工介入")
    async def human_interact(
        self,
        prompt: Annotated[str, Field(description="提示用户的信息")],
        input_type: Annotated[
            str, Field(description="输入类型: text/confirmation/choice")
        ] = "text",
        choices: Annotated[
            list[str] | None, Field(description="选项列表(choice类型时)")
        ] = None,
    ) -> dict[str, Any]:
        """Request human input."""
        if self._interaction_handler is None:
            self._interaction_handler = self._create_interaction_handler()

        interaction_type = InteractionType(input_type)
        response = await self._interaction_handler.request_input(
            prompt=prompt,
            input_type=interaction_type,
            choices=choices,
        )

        return {
            "success": True,
            "response": response,
            "input_type": input_type,
        }

    @tool(description="读写共享变量")
    async def variable_storage(
        self,
        action: Annotated[str, Field(description="操作: read/write/list")],
        key: Annotated[str | None, Field(description="变量名")] = None,
        value: Annotated[str | None, Field(description="变量值(write时)")] = None,
    ) -> dict[str, Any]:
        """Read, write, or list shared variables."""
        if action == "write":
            if key is None or value is None:
                return {"success": False, "error": "key and value required for write"}
            self._variables[key] = value
            return {"success": True, "key": key, "value": value}

        elif action == "read":
            if key is None:
                return {"success": False, "error": "key required for read"}
            value = self._variables.get(key)
            if value is None:
                return {"success": False, "error": f"Variable not found: {key}"}
            return {"success": True, "key": key, "value": value}

        elif action == "list":
            return {"success": True, "variables": dict(self._variables)}

        return {"success": False, "error": f"Unknown action: {action}"}
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/plugins/mobile/test_plugin.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/odin/plugins/builtin/mobile/plugin.py tests/unit/plugins/mobile/test_plugin.py
git commit -m "feat(mobile): implement MobilePlugin with all automation tools"
```

---

### Task 8: Register MobilePlugin in builtin plugins

**Files:**
- Modify: `src/odin/plugins/builtin/__init__.py`

**Step 1: Update __init__.py to include MobilePlugin**

Add to `src/odin/plugins/builtin/__init__.py`:

```python
# Add import at top
from odin.plugins.builtin.mobile import MobilePlugin

# Add to __all__
__all__ = [
    # ... existing exports
    "MobilePlugin",
]

# Add to BUILTIN_PLUGINS dict
BUILTIN_PLUGINS = {
    # ... existing plugins
    "mobile": MobilePlugin,
}
```

**Step 2: Commit**

```bash
git add src/odin/plugins/builtin/__init__.py
git commit -m "feat(mobile): register MobilePlugin in builtin plugins"
```

---

## Phase 3: Agent Layer

### Task 9: Implement MobileAgentBase

**Files:**
- Create: `src/odin/agents/mobile/base.py`
- Create: `tests/unit/agents/mobile/test_base.py`

**Step 1: Write failing tests**

`tests/unit/agents/mobile/test_base.py`:
```python
"""Tests for MobileAgentBase."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import base64

from odin.agents.mobile.base import (
    MobileAgentBase,
    MobileAgentConfig,
    AgentResult,
    VisionAnalysis,
)


class TestMobileAgentConfig:
    """Test MobileAgentConfig."""

    def test_default_values(self):
        """Default config values."""
        config = MobileAgentConfig()
        assert config.max_rounds == 50
        assert config.llm_model == "gpt-4o"
        assert config.vlm_model == "gpt-4o"

    def test_separate_models(self):
        """LLM and VLM can use different models."""
        config = MobileAgentConfig(
            llm_model="deepseek-v3",
            llm_base_url="https://api.deepseek.com/v1",
            vlm_model="qwen-vl-max",
            vlm_base_url="https://dashscope.aliyuncs.com/v1",
        )
        assert config.llm_model == "deepseek-v3"
        assert config.vlm_model == "qwen-vl-max"


class TestAgentResult:
    """Test AgentResult model."""

    def test_success_result(self):
        """Create success result."""
        result = AgentResult(
            success=True,
            message="Task completed",
            steps_taken=5,
        )
        assert result.success is True
        assert result.steps_taken == 5

    def test_failure_result(self):
        """Create failure result."""
        result = AgentResult(
            success=False,
            message="Task failed",
            error="Timeout",
        )
        assert result.success is False
        assert result.error == "Timeout"


class ConcreteAgent(MobileAgentBase):
    """Concrete implementation for testing."""

    async def execute(self, task: str) -> AgentResult:
        return AgentResult(success=True, message="Done")


class TestMobileAgentBase:
    """Test MobileAgentBase."""

    @pytest.fixture
    def mock_plugin(self):
        """Create mock plugin."""
        plugin = AsyncMock()
        plugin.screenshot = AsyncMock(return_value={
            "success": True,
            "image_base64": base64.b64encode(b"fake_image").decode(),
            "width": 1080,
            "height": 1920,
        })
        return plugin

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock()
        return client

    @pytest.fixture
    def mock_vlm_client(self):
        """Create mock VLM client."""
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock()
        return client

    @pytest.fixture
    def agent(self, mock_plugin, mock_llm_client, mock_vlm_client):
        """Create test agent."""
        config = MobileAgentConfig()
        return ConcreteAgent(
            config=config,
            plugin=mock_plugin,
            llm_client=mock_llm_client,
            vlm_client=mock_vlm_client,
        )

    @pytest.mark.asyncio
    async def test_analyze_screen(self, agent, mock_vlm_client):
        """analyze_screen() calls VLM with image."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"elements": [], "description": "Home screen"}'
        mock_vlm_client.chat.completions.create.return_value = mock_response

        result = await agent.analyze_screen(
            screenshot_base64="fake_base64",
            context="Find the settings button",
        )

        mock_vlm_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_vlm_client.chat.completions.create.call_args[1]
        assert "messages" in call_kwargs

    @pytest.mark.asyncio
    async def test_get_tools(self, agent, mock_plugin):
        """get_tools() returns plugin tools in OpenAI format."""
        mock_tool = MagicMock()
        mock_tool.to_openai_format.return_value = {
            "type": "function",
            "function": {"name": "click", "description": "Click"},
        }
        mock_plugin.get_tools = AsyncMock(return_value=[mock_tool])

        tools = await agent.get_tools()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "click"

    @pytest.mark.asyncio
    async def test_execute_tool(self, agent, mock_plugin):
        """execute_tool() calls plugin method."""
        mock_plugin.execute_tool = AsyncMock(return_value={"success": True})

        result = await agent.execute_tool("click", x=0.5, y=0.5)
        mock_plugin.execute_tool.assert_called_once_with("click", x=0.5, y=0.5)
        assert result["success"] is True
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/agents/mobile/test_base.py -v
```

Expected: FAIL

**Step 3: Implement base.py**

`src/odin/agents/mobile/base.py`:
```python
"""Base class for mobile automation agents."""

import json
from abc import ABC, abstractmethod
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from odin.plugins.builtin.mobile.plugin import MobilePlugin


class MobileAgentConfig(BaseModel):
    """Mobile agent configuration."""

    max_rounds: int = Field(default=50, description="Maximum execution rounds")

    # LLM config (for planning/reasoning)
    llm_model: str = Field(default="gpt-4o", description="LLM model name")
    llm_base_url: str | None = Field(default=None, description="LLM API base URL")
    llm_api_key: str | None = Field(default=None, description="LLM API key")

    # VLM config (for vision)
    vlm_model: str = Field(default="gpt-4o", description="VLM model name")
    vlm_base_url: str | None = Field(default=None, description="VLM API base URL")
    vlm_api_key: str | None = Field(default=None, description="VLM API key")

    # System prompts
    system_prompt: str = Field(
        default="You are a mobile automation assistant.",
        description="System prompt for the agent",
    )


class AgentResult(BaseModel):
    """Result of agent execution."""

    success: bool = Field(..., description="Whether task completed successfully")
    message: str = Field(default="", description="Result message")
    error: str | None = Field(default=None, description="Error message if failed")
    steps_taken: int = Field(default=0, description="Number of steps executed")
    final_state: dict[str, Any] = Field(
        default_factory=dict, description="Final state variables"
    )


class VisionAnalysis(BaseModel):
    """Result of vision analysis."""

    description: str = Field(default="", description="Screen description")
    elements: list[dict[str, Any]] = Field(
        default_factory=list, description="Detected UI elements"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Suggested actions"
    )
    raw_response: str = Field(default="", description="Raw VLM response")


class MobileAgentBase(ABC):
    """Abstract base class for mobile automation agents.

    Provides common functionality for:
    - Screen analysis with VLM
    - Tool execution via plugin
    - LLM-based reasoning
    """

    def __init__(
        self,
        config: MobileAgentConfig,
        plugin: MobilePlugin,
        llm_client: AsyncOpenAI | None = None,
        vlm_client: AsyncOpenAI | None = None,
    ) -> None:
        """Initialize mobile agent.

        Args:
            config: Agent configuration
            plugin: Mobile plugin instance
            llm_client: OpenAI client for LLM (planning/reasoning)
            vlm_client: OpenAI client for VLM (vision)
        """
        self.config = config
        self.plugin = plugin
        self.llm_client = llm_client or self._create_llm_client()
        self.vlm_client = vlm_client or self._create_vlm_client()
        self._history: list[dict[str, Any]] = []

    def _create_llm_client(self) -> AsyncOpenAI:
        """Create LLM client from config."""
        return AsyncOpenAI(
            api_key=self.config.llm_api_key,
            base_url=self.config.llm_base_url,
        )

    def _create_vlm_client(self) -> AsyncOpenAI:
        """Create VLM client from config."""
        return AsyncOpenAI(
            api_key=self.config.vlm_api_key,
            base_url=self.config.vlm_base_url,
        )

    @abstractmethod
    async def execute(self, task: str) -> AgentResult:
        """Execute a task.

        Args:
            task: Task description in natural language

        Returns:
            Execution result
        """

    async def analyze_screen(
        self,
        screenshot_base64: str,
        context: str = "",
    ) -> VisionAnalysis:
        """Analyze screenshot with VLM.

        Args:
            screenshot_base64: Base64 encoded screenshot
            context: Additional context for analysis

        Returns:
            Vision analysis result
        """
        messages = [
            {
                "role": "system",
                "content": """You are a mobile UI analyzer. Analyze the screenshot and return JSON:
{
    "description": "Brief description of what's on screen",
    "elements": [{"type": "button/text/input/...", "text": "...", "location": "top/center/bottom"}],
    "suggestions": ["Possible actions based on context"]
}""",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Analyze this screen. Context: {context}" if context else "Analyze this screen.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_base64}",
                        },
                    },
                ],
            },
        ]

        response = await self.vlm_client.chat.completions.create(
            model=self.config.vlm_model,
            messages=messages,  # type: ignore
            max_tokens=1000,
        )

        raw_content = response.choices[0].message.content or ""

        # Try to parse as JSON
        try:
            # Extract JSON from response (may be wrapped in markdown)
            json_str = raw_content
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str)
            return VisionAnalysis(
                description=data.get("description", ""),
                elements=data.get("elements", []),
                suggestions=data.get("suggestions", []),
                raw_response=raw_content,
            )
        except json.JSONDecodeError:
            return VisionAnalysis(
                description=raw_content,
                raw_response=raw_content,
            )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Get available tools in OpenAI format.

        Returns:
            List of tool definitions
        """
        tools = await self.plugin.get_tools()
        return [tool.to_openai_format() for tool in tools]

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a tool via plugin.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        return await self.plugin.execute_tool(tool_name, **kwargs)

    async def take_screenshot(self) -> dict[str, Any]:
        """Take screenshot via plugin.

        Returns:
            Screenshot result with image_base64
        """
        return await self.plugin.screenshot()

    def add_to_history(self, entry: dict[str, Any]) -> None:
        """Add entry to execution history.

        Args:
            entry: History entry
        """
        self._history.append(entry)

    def get_history(self) -> list[dict[str, Any]]:
        """Get execution history.

        Returns:
            List of history entries
        """
        return self._history.copy()

    def clear_history(self) -> None:
        """Clear execution history."""
        self._history.clear()
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/agents/mobile/test_base.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/odin/agents/mobile/base.py tests/unit/agents/mobile/test_base.py
git commit -m "feat(mobile): implement MobileAgentBase with VLM analysis"
```

---

### Task 10: Implement MobileReActAgent

**Files:**
- Create: `src/odin/agents/mobile/react.py`
- Create: `tests/unit/agents/mobile/test_react.py`

**Step 1: Write failing tests**

`tests/unit/agents/mobile/test_react.py`:
```python
"""Tests for MobileReActAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import base64
import json

from odin.agents.mobile.react import MobileReActAgent
from odin.agents.mobile.base import MobileAgentConfig, AgentResult


class TestMobileReActAgent:
    """Test MobileReActAgent."""

    @pytest.fixture
    def mock_plugin(self):
        """Create mock plugin."""
        plugin = AsyncMock()
        plugin.screenshot = AsyncMock(return_value={
            "success": True,
            "image_base64": base64.b64encode(b"fake_image").decode(),
            "width": 1080,
            "height": 1920,
        })
        plugin.get_tools = AsyncMock(return_value=[])
        plugin.execute_tool = AsyncMock(return_value={"success": True})
        return plugin

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock()
        return client

    @pytest.fixture
    def mock_vlm_client(self):
        """Create mock VLM client."""
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock()
        return client

    @pytest.fixture
    def agent(self, mock_plugin, mock_llm_client, mock_vlm_client):
        """Create test agent."""
        config = MobileAgentConfig(max_rounds=5)
        return MobileReActAgent(
            config=config,
            plugin=mock_plugin,
            llm_client=mock_llm_client,
            vlm_client=mock_vlm_client,
        )

    @pytest.mark.asyncio
    async def test_execute_simple_task(self, agent, mock_llm_client, mock_vlm_client):
        """Execute completes when LLM returns TASK_COMPLETE."""
        # VLM response
        vlm_response = MagicMock()
        vlm_response.choices = [MagicMock()]
        vlm_response.choices[0].message.content = '{"description": "Home screen"}'
        mock_vlm_client.chat.completions.create.return_value = vlm_response

        # LLM response - complete task
        llm_response = MagicMock()
        llm_response.choices = [MagicMock()]
        llm_response.choices[0].message.content = "TASK_COMPLETE: Task finished"
        llm_response.choices[0].message.tool_calls = None
        mock_llm_client.chat.completions.create.return_value = llm_response

        result = await agent.execute("Test task")

        assert result.success is True
        assert result.steps_taken >= 1

    @pytest.mark.asyncio
    async def test_execute_with_tool_call(self, agent, mock_plugin, mock_llm_client, mock_vlm_client):
        """Execute handles tool calls from LLM."""
        # VLM response
        vlm_response = MagicMock()
        vlm_response.choices = [MagicMock()]
        vlm_response.choices[0].message.content = '{"description": "App screen"}'
        mock_vlm_client.chat.completions.create.return_value = vlm_response

        # First LLM response - tool call
        tool_call = MagicMock()
        tool_call.id = "call_123"
        tool_call.function.name = "click"
        tool_call.function.arguments = '{"x": 0.5, "y": 0.5}'

        first_response = MagicMock()
        first_response.choices = [MagicMock()]
        first_response.choices[0].message.content = "I'll click the button"
        first_response.choices[0].message.tool_calls = [tool_call]

        # Second LLM response - complete
        second_response = MagicMock()
        second_response.choices = [MagicMock()]
        second_response.choices[0].message.content = "TASK_COMPLETE: Clicked successfully"
        second_response.choices[0].message.tool_calls = None

        mock_llm_client.chat.completions.create.side_effect = [
            first_response,
            second_response,
        ]

        result = await agent.execute("Click the button")

        assert mock_plugin.execute_tool.called
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_max_rounds(self, agent, mock_llm_client, mock_vlm_client):
        """Execute stops at max_rounds."""
        # VLM response
        vlm_response = MagicMock()
        vlm_response.choices = [MagicMock()]
        vlm_response.choices[0].message.content = '{"description": "Screen"}'
        mock_vlm_client.chat.completions.create.return_value = vlm_response

        # LLM never completes
        llm_response = MagicMock()
        llm_response.choices = [MagicMock()]
        llm_response.choices[0].message.content = "Still working..."
        llm_response.choices[0].message.tool_calls = None
        mock_llm_client.chat.completions.create.return_value = llm_response

        result = await agent.execute("Impossible task")

        assert result.success is False
        assert "max rounds" in result.error.lower()
        assert result.steps_taken == 5  # max_rounds

    @pytest.mark.asyncio
    async def test_execute_handles_tool_error(self, agent, mock_plugin, mock_llm_client, mock_vlm_client):
        """Execute handles tool execution errors."""
        # VLM response
        vlm_response = MagicMock()
        vlm_response.choices = [MagicMock()]
        vlm_response.choices[0].message.content = '{"description": "Screen"}'
        mock_vlm_client.chat.completions.create.return_value = vlm_response

        # Tool call
        tool_call = MagicMock()
        tool_call.id = "call_123"
        tool_call.function.name = "click"
        tool_call.function.arguments = '{"x": 0.5, "y": 0.5}'

        first_response = MagicMock()
        first_response.choices = [MagicMock()]
        first_response.choices[0].message.content = "Clicking"
        first_response.choices[0].message.tool_calls = [tool_call]

        # Tool fails
        mock_plugin.execute_tool.return_value = {"success": False, "error": "Device disconnected"}

        # LLM handles error
        second_response = MagicMock()
        second_response.choices = [MagicMock()]
        second_response.choices[0].message.content = "TASK_COMPLETE: Failed due to device error"
        second_response.choices[0].message.tool_calls = None

        mock_llm_client.chat.completions.create.side_effect = [
            first_response,
            second_response,
        ]

        result = await agent.execute("Click something")

        # Agent should continue and handle the error
        assert mock_plugin.execute_tool.called
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/agents/mobile/test_react.py -v
```

Expected: FAIL

**Step 3: Implement react.py**

`src/odin/agents/mobile/react.py`:
```python
"""ReAct agent for mobile automation.

Implements the ReAct (Reasoning + Acting) loop:
1. Take screenshot
2. Analyze with VLM
3. Reason and decide action with LLM
4. Execute action
5. Observe result
6. Repeat until task complete or max rounds
"""

import json
from typing import Any

from odin.agents.mobile.base import (
    AgentResult,
    MobileAgentBase,
    MobileAgentConfig,
)
from odin.plugins.builtin.mobile.plugin import MobilePlugin
from openai import AsyncOpenAI


REACT_SYSTEM_PROMPT = """You are a mobile automation agent. Your goal is to complete tasks by interacting with the mobile device.

For each step:
1. Observe the current screen state
2. Think about what action to take next
3. Execute the appropriate tool

When the task is complete, respond with: TASK_COMPLETE: <summary of what was done>
If the task cannot be completed, respond with: TASK_FAILED: <reason>

Available information:
- Screen analysis from vision model
- Previous actions and their results
- Current task goal

Be precise with coordinates. Use the tools provided to interact with the device."""


class MobileReActAgent(MobileAgentBase):
    """ReAct agent for mobile automation.

    Uses a Think → Act → Observe loop to complete tasks.
    """

    def __init__(
        self,
        config: MobileAgentConfig,
        plugin: MobilePlugin,
        llm_client: AsyncOpenAI | None = None,
        vlm_client: AsyncOpenAI | None = None,
    ) -> None:
        """Initialize ReAct agent."""
        super().__init__(config, plugin, llm_client, vlm_client)
        self._messages: list[dict[str, Any]] = []

    async def execute(self, task: str) -> AgentResult:
        """Execute task using ReAct loop.

        Args:
            task: Task description

        Returns:
            Execution result
        """
        self.clear_history()
        self._messages = [
            {"role": "system", "content": REACT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {task}"},
        ]

        tools = await self.get_tools()
        steps_taken = 0

        for round_num in range(self.config.max_rounds):
            steps_taken = round_num + 1

            # 1. Take screenshot and analyze
            screenshot_result = await self.take_screenshot()
            if not screenshot_result.get("success"):
                return AgentResult(
                    success=False,
                    message="Failed to take screenshot",
                    error=screenshot_result.get("error", "Unknown error"),
                    steps_taken=steps_taken,
                )

            screen_analysis = await self.analyze_screen(
                screenshot_base64=screenshot_result["image_base64"],
                context=task,
            )

            # Add screen observation to messages
            observation = f"""
Screen Analysis:
{screen_analysis.description}

Elements: {json.dumps(screen_analysis.elements, ensure_ascii=False)}
Suggestions: {screen_analysis.suggestions}
"""
            self._messages.append({
                "role": "user",
                "content": f"[Observation - Round {round_num + 1}]\n{observation}",
            })

            # 2. Get LLM decision
            response = await self.llm_client.chat.completions.create(
                model=self.config.llm_model,
                messages=self._messages,  # type: ignore
                tools=tools if tools else None,  # type: ignore
                tool_choice="auto" if tools else None,
            )

            assistant_message = response.choices[0].message
            content = assistant_message.content or ""

            # Record in history
            self.add_to_history({
                "round": round_num + 1,
                "screen_analysis": screen_analysis.model_dump(),
                "llm_response": content,
                "tool_calls": [
                    {"name": tc.function.name, "args": tc.function.arguments}
                    for tc in (assistant_message.tool_calls or [])
                ],
            })

            # 3. Check for task completion
            if "TASK_COMPLETE:" in content:
                summary = content.split("TASK_COMPLETE:")[1].strip()
                return AgentResult(
                    success=True,
                    message=summary,
                    steps_taken=steps_taken,
                    final_state=await self._get_variables(),
                )

            if "TASK_FAILED:" in content:
                reason = content.split("TASK_FAILED:")[1].strip()
                return AgentResult(
                    success=False,
                    message=reason,
                    error=reason,
                    steps_taken=steps_taken,
                )

            # 4. Execute tool calls if any
            if assistant_message.tool_calls:
                self._messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                })

                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    # Execute tool
                    try:
                        tool_result = await self.execute_tool(tool_name, **tool_args)
                    except Exception as e:
                        tool_result = {"success": False, "error": str(e)}

                    # Add tool result to messages
                    self._messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False),
                    })
            else:
                # No tool calls, add assistant message
                self._messages.append({
                    "role": "assistant",
                    "content": content,
                })

        # Max rounds reached
        return AgentResult(
            success=False,
            message="Task did not complete within max rounds",
            error=f"Reached max rounds ({self.config.max_rounds})",
            steps_taken=steps_taken,
        )

    async def _get_variables(self) -> dict[str, Any]:
        """Get current variable storage state."""
        try:
            result = await self.plugin.variable_storage(action="list")
            return result.get("variables", {})
        except Exception:
            return {}
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/agents/mobile/test_react.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/odin/agents/mobile/react.py tests/unit/agents/mobile/test_react.py
git commit -m "feat(mobile): implement MobileReActAgent with Think-Act-Observe loop"
```

---

### Task 11: Implement MobilePlanExecuteAgent

**Files:**
- Create: `src/odin/agents/mobile/plan_execute.py`
- Create: `tests/unit/agents/mobile/test_plan_execute.py`

**Step 1: Write failing tests**

`tests/unit/agents/mobile/test_plan_execute.py`:
```python
"""Tests for MobilePlanExecuteAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import base64
import json

from odin.agents.mobile.plan_execute import MobilePlanExecuteAgent, TaskPlan, PlanStep
from odin.agents.mobile.base import MobileAgentConfig


class TestTaskPlan:
    """Test TaskPlan model."""

    def test_create_plan(self):
        """Create a task plan."""
        plan = TaskPlan(
            goal="Open WeChat and send message",
            steps=[
                PlanStep(description="Open WeChat app", expected_outcome="WeChat home screen"),
                PlanStep(description="Find contact", expected_outcome="Contact chat screen"),
            ],
        )
        assert len(plan.steps) == 2
        assert plan.current_step == 0

    def test_get_current_step(self):
        """Get current step from plan."""
        plan = TaskPlan(
            goal="Test",
            steps=[
                PlanStep(description="Step 1"),
                PlanStep(description="Step 2"),
            ],
        )
        assert plan.get_current_step().description == "Step 1"
        plan.current_step = 1
        assert plan.get_current_step().description == "Step 2"

    def test_is_complete(self):
        """Check if plan is complete."""
        plan = TaskPlan(
            goal="Test",
            steps=[PlanStep(description="Only step")],
        )
        assert plan.is_complete() is False
        plan.current_step = 1
        assert plan.is_complete() is True


class TestMobilePlanExecuteAgent:
    """Test MobilePlanExecuteAgent."""

    @pytest.fixture
    def mock_plugin(self):
        """Create mock plugin."""
        plugin = AsyncMock()
        plugin.screenshot = AsyncMock(return_value={
            "success": True,
            "image_base64": base64.b64encode(b"fake").decode(),
            "width": 1080,
            "height": 1920,
        })
        plugin.get_tools = AsyncMock(return_value=[])
        plugin.execute_tool = AsyncMock(return_value={"success": True})
        return plugin

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock()
        return client

    @pytest.fixture
    def mock_vlm_client(self):
        """Create mock VLM client."""
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock()
        return client

    @pytest.fixture
    def agent(self, mock_plugin, mock_llm_client, mock_vlm_client):
        """Create test agent."""
        config = MobileAgentConfig(max_rounds=10)
        return MobilePlanExecuteAgent(
            config=config,
            plugin=mock_plugin,
            llm_client=mock_llm_client,
            vlm_client=mock_vlm_client,
        )

    @pytest.mark.asyncio
    async def test_create_plan(self, agent, mock_llm_client):
        """create_plan() generates task plan from LLM."""
        plan_json = json.dumps({
            "goal": "Open settings",
            "steps": [
                {"description": "Find settings icon", "expected_outcome": "Settings visible"},
                {"description": "Click settings", "expected_outcome": "Settings screen"},
            ],
        })

        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = plan_json
        mock_llm_client.chat.completions.create.return_value = response

        plan = await agent.create_plan("Open settings")

        assert plan.goal == "Open settings"
        assert len(plan.steps) == 2

    @pytest.mark.asyncio
    async def test_execute_with_plan(self, agent, mock_llm_client, mock_vlm_client):
        """execute() creates plan and executes steps."""
        # Plan creation response
        plan_response = MagicMock()
        plan_response.choices = [MagicMock()]
        plan_response.choices[0].message.content = json.dumps({
            "goal": "Test task",
            "steps": [{"description": "Do something"}],
        })

        # VLM response
        vlm_response = MagicMock()
        vlm_response.choices = [MagicMock()]
        vlm_response.choices[0].message.content = '{"description": "Screen"}'

        # Step execution response - complete
        exec_response = MagicMock()
        exec_response.choices = [MagicMock()]
        exec_response.choices[0].message.content = "STEP_COMPLETE"
        exec_response.choices[0].message.tool_calls = None

        mock_llm_client.chat.completions.create.side_effect = [
            plan_response,
            exec_response,
        ]
        mock_vlm_client.chat.completions.create.return_value = vlm_response

        result = await agent.execute("Test task")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_adaptive_replanning(self, agent, mock_llm_client, mock_vlm_client):
        """Agent replans when step fails multiple times."""
        # Initial plan
        plan_response = MagicMock()
        plan_response.choices = [MagicMock()]
        plan_response.choices[0].message.content = json.dumps({
            "goal": "Test",
            "steps": [{"description": "Step 1"}],
        })

        # VLM response
        vlm_response = MagicMock()
        vlm_response.choices = [MagicMock()]
        vlm_response.choices[0].message.content = '{"description": "Unexpected screen"}'

        # Step fails, needs replan
        fail_response = MagicMock()
        fail_response.choices = [MagicMock()]
        fail_response.choices[0].message.content = "STEP_FAILED: Unexpected state"
        fail_response.choices[0].message.tool_calls = None

        # Replan response
        replan_response = MagicMock()
        replan_response.choices = [MagicMock()]
        replan_response.choices[0].message.content = json.dumps({
            "goal": "Test",
            "steps": [{"description": "Alternative step"}],
        })

        # Success after replan
        success_response = MagicMock()
        success_response.choices = [MagicMock()]
        success_response.choices[0].message.content = "STEP_COMPLETE"
        success_response.choices[0].message.tool_calls = None

        mock_llm_client.chat.completions.create.side_effect = [
            plan_response,
            fail_response,
            replan_response,
            success_response,
        ]
        mock_vlm_client.chat.completions.create.return_value = vlm_response

        result = await agent.execute("Test")

        # Should have replanned
        assert mock_llm_client.chat.completions.create.call_count >= 3
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/agents/mobile/test_plan_execute.py -v
```

Expected: FAIL

**Step 3: Implement plan_execute.py**

`src/odin/agents/mobile/plan_execute.py`:
```python
"""Plan and Execute agent for mobile automation.

Two-phase approach:
1. Planning: LLM creates a step-by-step plan
2. Execution: Execute each step, adapting plan if needed
"""

import json
from typing import Any

from pydantic import BaseModel, Field
from openai import AsyncOpenAI

from odin.agents.mobile.base import (
    AgentResult,
    MobileAgentBase,
    MobileAgentConfig,
)
from odin.plugins.builtin.mobile.plugin import MobilePlugin


class PlanStep(BaseModel):
    """A single step in the execution plan."""

    description: str = Field(..., description="What to do in this step")
    expected_outcome: str = Field(
        default="", description="Expected screen state after step"
    )
    completed: bool = Field(default=False, description="Whether step is done")
    attempts: int = Field(default=0, description="Number of execution attempts")


class TaskPlan(BaseModel):
    """Execution plan for a task."""

    goal: str = Field(..., description="Overall task goal")
    steps: list[PlanStep] = Field(default_factory=list, description="Planned steps")
    current_step: int = Field(default=0, description="Current step index")

    def get_current_step(self) -> PlanStep:
        """Get current step."""
        return self.steps[self.current_step]

    def is_complete(self) -> bool:
        """Check if all steps are done."""
        return self.current_step >= len(self.steps)

    def advance(self) -> None:
        """Move to next step."""
        if self.current_step < len(self.steps):
            self.steps[self.current_step].completed = True
            self.current_step += 1


PLANNING_PROMPT = """You are a mobile automation planner. Create a step-by-step plan to complete the task.

Return JSON only:
{
    "goal": "Overall task goal",
    "steps": [
        {"description": "Step description", "expected_outcome": "Expected screen state"}
    ]
}

Keep steps atomic and actionable. Each step should be one interaction."""


EXECUTION_PROMPT = """You are executing step {step_num} of a mobile automation plan.

Current Step: {step_description}
Expected Outcome: {expected_outcome}

Based on the screen analysis, decide:
- If step can be completed: execute the appropriate tool, then respond STEP_COMPLETE
- If step cannot be done from current screen: respond STEP_FAILED: <reason>
- If task is already done: respond TASK_COMPLETE: <summary>"""


class MobilePlanExecuteAgent(MobileAgentBase):
    """Plan and Execute agent.

    Creates a plan first, then executes adaptively.
    """

    def __init__(
        self,
        config: MobileAgentConfig,
        plugin: MobilePlugin,
        llm_client: AsyncOpenAI | None = None,
        vlm_client: AsyncOpenAI | None = None,
    ) -> None:
        """Initialize Plan+Execute agent."""
        super().__init__(config, plugin, llm_client, vlm_client)
        self._plan: TaskPlan | None = None
        self._max_step_attempts = 3

    async def create_plan(self, task: str) -> TaskPlan:
        """Create execution plan for task.

        Args:
            task: Task description

        Returns:
            Task plan
        """
        # Take initial screenshot for context
        screenshot = await self.take_screenshot()
        screen_context = ""
        if screenshot.get("success"):
            analysis = await self.analyze_screen(
                screenshot["image_base64"],
                context=f"Planning for: {task}",
            )
            screen_context = f"\n\nCurrent screen: {analysis.description}"

        response = await self.llm_client.chat.completions.create(
            model=self.config.llm_model,
            messages=[
                {"role": "system", "content": PLANNING_PROMPT},
                {"role": "user", "content": f"Task: {task}{screen_context}"},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"

        try:
            data = json.loads(content)
            return TaskPlan(
                goal=data.get("goal", task),
                steps=[PlanStep(**s) for s in data.get("steps", [])],
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback: single step plan
            return TaskPlan(
                goal=task,
                steps=[PlanStep(description=task)],
            )

    async def execute(self, task: str) -> AgentResult:
        """Execute task with planning.

        Args:
            task: Task description

        Returns:
            Execution result
        """
        self.clear_history()

        # Phase 1: Create plan
        self._plan = await self.create_plan(task)
        self.add_to_history({
            "phase": "planning",
            "plan": self._plan.model_dump(),
        })

        tools = await self.get_tools()
        total_steps = 0

        # Phase 2: Execute steps
        while not self._plan.is_complete() and total_steps < self.config.max_rounds:
            current_step = self._plan.get_current_step()
            current_step.attempts += 1
            total_steps += 1

            # Take screenshot
            screenshot = await self.take_screenshot()
            if not screenshot.get("success"):
                return AgentResult(
                    success=False,
                    error="Screenshot failed",
                    steps_taken=total_steps,
                )

            # Analyze screen
            analysis = await self.analyze_screen(
                screenshot["image_base64"],
                context=current_step.description,
            )

            # Build execution prompt
            exec_prompt = EXECUTION_PROMPT.format(
                step_num=self._plan.current_step + 1,
                step_description=current_step.description,
                expected_outcome=current_step.expected_outcome,
            )

            messages = [
                {"role": "system", "content": exec_prompt},
                {
                    "role": "user",
                    "content": f"Screen: {analysis.description}\nElements: {json.dumps(analysis.elements, ensure_ascii=False)}",
                },
            ]

            # Get LLM decision
            response = await self.llm_client.chat.completions.create(
                model=self.config.llm_model,
                messages=messages,  # type: ignore
                tools=tools if tools else None,  # type: ignore
            )

            assistant_msg = response.choices[0].message
            content = assistant_msg.content or ""

            self.add_to_history({
                "phase": "execution",
                "step": self._plan.current_step + 1,
                "attempt": current_step.attempts,
                "screen": analysis.description,
                "response": content,
            })

            # Handle tool calls
            if assistant_msg.tool_calls:
                for tool_call in assistant_msg.tool_calls:
                    try:
                        args = json.loads(tool_call.function.arguments)
                        await self.execute_tool(tool_call.function.name, **args)
                    except Exception as e:
                        self.add_to_history({"error": str(e)})

            # Check step result
            if "TASK_COMPLETE:" in content:
                summary = content.split("TASK_COMPLETE:")[1].strip()
                return AgentResult(
                    success=True,
                    message=summary,
                    steps_taken=total_steps,
                )

            if "STEP_COMPLETE" in content:
                self._plan.advance()
                continue

            if "STEP_FAILED:" in content:
                if current_step.attempts >= self._max_step_attempts:
                    # Replan from current state
                    remaining_goal = f"Continue: {self._plan.goal} (failed at: {current_step.description})"
                    new_plan = await self.create_plan(remaining_goal)
                    self._plan = new_plan
                    self.add_to_history({
                        "phase": "replanning",
                        "reason": content,
                        "new_plan": new_plan.model_dump(),
                    })

        if self._plan.is_complete():
            return AgentResult(
                success=True,
                message=f"Completed all {len(self._plan.steps)} steps",
                steps_taken=total_steps,
            )

        return AgentResult(
            success=False,
            error=f"Max rounds ({self.config.max_rounds}) reached",
            steps_taken=total_steps,
        )
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/agents/mobile/test_plan_execute.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/odin/agents/mobile/plan_execute.py tests/unit/agents/mobile/test_plan_execute.py
git commit -m "feat(mobile): implement MobilePlanExecuteAgent with adaptive replanning"
```

---

### Task 12: Implement MobileHierarchicalAgent

**Files:**
- Create: `src/odin/agents/mobile/hierarchical.py`
- Create: `tests/unit/agents/mobile/test_hierarchical.py`

**Step 1: Write failing tests**

`tests/unit/agents/mobile/test_hierarchical.py`:
```python
"""Tests for MobileHierarchicalAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import base64
import json

from odin.agents.mobile.hierarchical import (
    MobileHierarchicalAgent,
    AppTask,
    HighLevelPlan,
)
from odin.agents.mobile.base import MobileAgentConfig


class TestAppTask:
    """Test AppTask model."""

    def test_create_task(self):
        """Create app task."""
        task = AppTask(
            app_name="WeChat",
            description="Send a message to contact",
            input_variables={"contact": "John"},
            output_variables=["message_sent"],
        )
        assert task.app_name == "WeChat"
        assert task.input_variables == {"contact": "John"}


class TestHighLevelPlan:
    """Test HighLevelPlan model."""

    def test_create_plan(self):
        """Create high-level plan."""
        plan = HighLevelPlan(
            goal="Take photo and share to WeChat",
            tasks=[
                AppTask(app_name="Camera", description="Take photo"),
                AppTask(app_name="WeChat", description="Share photo"),
            ],
        )
        assert len(plan.tasks) == 2
        assert plan.current_task == 0

    def test_get_current_task(self):
        """Get current task."""
        plan = HighLevelPlan(
            goal="Test",
            tasks=[
                AppTask(app_name="App1", description="Task 1"),
                AppTask(app_name="App2", description="Task 2"),
            ],
        )
        assert plan.get_current_task().app_name == "App1"
        plan.current_task = 1
        assert plan.get_current_task().app_name == "App2"


class TestMobileHierarchicalAgent:
    """Test MobileHierarchicalAgent."""

    @pytest.fixture
    def mock_plugin(self):
        """Create mock plugin."""
        plugin = AsyncMock()
        plugin.screenshot = AsyncMock(return_value={
            "success": True,
            "image_base64": base64.b64encode(b"fake").decode(),
            "width": 1080,
            "height": 1920,
        })
        plugin.get_tools = AsyncMock(return_value=[])
        plugin.execute_tool = AsyncMock(return_value={"success": True})
        plugin.variable_storage = AsyncMock(return_value={"success": True, "variables": {}})
        return plugin

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock()
        return client

    @pytest.fixture
    def mock_vlm_client(self):
        """Create mock VLM client."""
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock()
        return client

    @pytest.fixture
    def agent(self, mock_plugin, mock_llm_client, mock_vlm_client):
        """Create test agent."""
        config = MobileAgentConfig(max_rounds=10)
        return MobileHierarchicalAgent(
            config=config,
            plugin=mock_plugin,
            llm_client=mock_llm_client,
            vlm_client=mock_vlm_client,
        )

    @pytest.mark.asyncio
    async def test_create_high_level_plan(self, agent, mock_llm_client):
        """create_high_level_plan() generates app-level plan."""
        plan_json = json.dumps({
            "goal": "Share photo on WeChat",
            "tasks": [
                {"app_name": "Camera", "description": "Take photo", "output_variables": ["photo_path"]},
                {"app_name": "WeChat", "description": "Share photo", "input_variables": {"photo": "photo_path"}},
            ],
        })

        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = plan_json
        mock_llm_client.chat.completions.create.return_value = response

        plan = await agent.create_high_level_plan("Take photo and share on WeChat")

        assert plan.goal == "Share photo on WeChat"
        assert len(plan.tasks) == 2
        assert plan.tasks[0].app_name == "Camera"

    @pytest.mark.asyncio
    async def test_execute_multi_app_task(self, agent, mock_llm_client, mock_vlm_client, mock_plugin):
        """Execute task spanning multiple apps."""
        # High-level plan
        plan_response = MagicMock()
        plan_response.choices = [MagicMock()]
        plan_response.choices[0].message.content = json.dumps({
            "goal": "Test",
            "tasks": [
                {"app_name": "App1", "description": "Do task 1"},
            ],
        })

        # VLM response
        vlm_response = MagicMock()
        vlm_response.choices = [MagicMock()]
        vlm_response.choices[0].message.content = '{"description": "Screen"}'

        # Low-level ReAct response - complete
        react_response = MagicMock()
        react_response.choices = [MagicMock()]
        react_response.choices[0].message.content = "TASK_COMPLETE: Done"
        react_response.choices[0].message.tool_calls = None

        mock_llm_client.chat.completions.create.side_effect = [
            plan_response,
            react_response,
        ]
        mock_vlm_client.chat.completions.create.return_value = vlm_response

        result = await agent.execute("Test task")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_variable_passing_between_apps(self, agent, mock_llm_client, mock_vlm_client, mock_plugin):
        """Variables are passed between app tasks."""
        # High-level plan with variable passing
        plan_response = MagicMock()
        plan_response.choices = [MagicMock()]
        plan_response.choices[0].message.content = json.dumps({
            "goal": "Get data and process",
            "tasks": [
                {"app_name": "App1", "description": "Get data", "output_variables": ["data"]},
                {"app_name": "App2", "description": "Process data", "input_variables": {"input": "data"}},
            ],
        })

        # VLM response
        vlm_response = MagicMock()
        vlm_response.choices = [MagicMock()]
        vlm_response.choices[0].message.content = '{"description": "Screen"}'

        # First app completes
        first_response = MagicMock()
        first_response.choices = [MagicMock()]
        first_response.choices[0].message.content = "TASK_COMPLETE: Got data"
        first_response.choices[0].message.tool_calls = None

        # Second app completes
        second_response = MagicMock()
        second_response.choices = [MagicMock()]
        second_response.choices[0].message.content = "TASK_COMPLETE: Processed"
        second_response.choices[0].message.tool_calls = None

        mock_llm_client.chat.completions.create.side_effect = [
            plan_response,
            first_response,
            second_response,
        ]
        mock_vlm_client.chat.completions.create.return_value = vlm_response

        # Simulate variable storage
        mock_plugin.variable_storage.return_value = {
            "success": True,
            "variables": {"data": "test_value"},
        }

        result = await agent.execute("Get and process data")

        assert result.success is True
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/agents/mobile/test_hierarchical.py -v
```

Expected: FAIL

**Step 3: Implement hierarchical.py**

`src/odin/agents/mobile/hierarchical.py`:
```python
"""Hierarchical ReAct agent for mobile automation.

Two-level architecture:
1. High-level planner: Decomposes task into app-level subtasks
2. Low-level ReAct: Executes each app subtask with Think-Act-Observe loop

Supports variable passing between apps and backtracking on failure.
"""

import json
from typing import Any

from pydantic import BaseModel, Field
from openai import AsyncOpenAI

from odin.agents.mobile.base import (
    AgentResult,
    MobileAgentBase,
    MobileAgentConfig,
)
from odin.plugins.builtin.mobile.plugin import MobilePlugin


class AppTask(BaseModel):
    """A task to be executed within a specific app."""

    app_name: str = Field(..., description="Target application name")
    description: str = Field(..., description="What to do in this app")
    input_variables: dict[str, str] = Field(
        default_factory=dict, description="Variables to read before execution"
    )
    output_variables: list[str] = Field(
        default_factory=list, description="Variables to write after execution"
    )
    completed: bool = Field(default=False, description="Whether task is done")
    attempts: int = Field(default=0, description="Execution attempts")


class HighLevelPlan(BaseModel):
    """High-level plan decomposing task into app-level subtasks."""

    goal: str = Field(..., description="Overall task goal")
    tasks: list[AppTask] = Field(default_factory=list, description="App-level tasks")
    current_task: int = Field(default=0, description="Current task index")

    def get_current_task(self) -> AppTask:
        """Get current task."""
        return self.tasks[self.current_task]

    def is_complete(self) -> bool:
        """Check if all tasks are done."""
        return self.current_task >= len(self.tasks)

    def advance(self) -> None:
        """Move to next task."""
        if self.current_task < len(self.tasks):
            self.tasks[self.current_task].completed = True
            self.current_task += 1

    def backtrack(self, steps: int = 1) -> None:
        """Go back to previous task(s)."""
        self.current_task = max(0, self.current_task - steps)


HIGH_LEVEL_PLANNING_PROMPT = """You are a mobile automation planner. Decompose the task into app-level subtasks.

Return JSON only:
{
    "goal": "Overall task goal",
    "tasks": [
        {
            "app_name": "App name (e.g., WeChat, Camera, Settings)",
            "description": "What to do in this app",
            "input_variables": {"var_name": "source_var"},
            "output_variables": ["var_to_save"]
        }
    ]
}

Rules:
- Each task should be in ONE app
- Use input_variables to reference data from previous tasks
- Use output_variables to save data for later tasks
- Keep tasks atomic and focused"""


LOW_LEVEL_REACT_PROMPT = """You are executing a subtask in the {app_name} app.

Task: {description}
Input variables: {input_vars}
Required outputs: {output_vars}

For each step:
1. Observe the screen
2. Decide the next action
3. Execute the tool

When done, respond: TASK_COMPLETE: <summary>
If blocked, respond: TASK_BLOCKED: <reason>
If failed, respond: TASK_FAILED: <reason>

Save any required output variables using variable_storage tool before completing."""


class MobileHierarchicalAgent(MobileAgentBase):
    """Hierarchical agent with high-level planning and low-level ReAct.

    Decomposes complex tasks into app-level subtasks and executes
    each with a ReAct loop. Supports variable passing and backtracking.
    """

    def __init__(
        self,
        config: MobileAgentConfig,
        plugin: MobilePlugin,
        llm_client: AsyncOpenAI | None = None,
        vlm_client: AsyncOpenAI | None = None,
    ) -> None:
        """Initialize hierarchical agent."""
        super().__init__(config, plugin, llm_client, vlm_client)
        self._plan: HighLevelPlan | None = None
        self._max_task_attempts = 3
        self._max_react_steps = 15

    async def create_high_level_plan(self, task: str) -> HighLevelPlan:
        """Create high-level plan decomposing task into app subtasks.

        Args:
            task: Task description

        Returns:
            High-level plan
        """
        response = await self.llm_client.chat.completions.create(
            model=self.config.llm_model,
            messages=[
                {"role": "system", "content": HIGH_LEVEL_PLANNING_PROMPT},
                {"role": "user", "content": f"Task: {task}"},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"

        try:
            data = json.loads(content)
            return HighLevelPlan(
                goal=data.get("goal", task),
                tasks=[AppTask(**t) for t in data.get("tasks", [])],
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback: single task
            return HighLevelPlan(
                goal=task,
                tasks=[AppTask(app_name="Unknown", description=task)],
            )

    async def execute(self, task: str) -> AgentResult:
        """Execute task with hierarchical planning.

        Args:
            task: Task description

        Returns:
            Execution result
        """
        self.clear_history()

        # Phase 1: Create high-level plan
        self._plan = await self.create_high_level_plan(task)
        self.add_to_history({
            "phase": "high_level_planning",
            "plan": self._plan.model_dump(),
        })

        total_steps = 0
        tools = await self.get_tools()

        # Phase 2: Execute each app task
        while not self._plan.is_complete() and total_steps < self.config.max_rounds:
            current_task = self._plan.get_current_task()
            current_task.attempts += 1

            self.add_to_history({
                "phase": "starting_app_task",
                "task_index": self._plan.current_task,
                "app": current_task.app_name,
                "description": current_task.description,
            })

            # Load input variables
            input_values = {}
            for var_name, source in current_task.input_variables.items():
                result = await self.plugin.variable_storage(action="read", key=source)
                if result.get("success"):
                    input_values[var_name] = result.get("value")

            # Execute low-level ReAct for this app task
            task_result = await self._execute_app_task(
                current_task,
                input_values,
                tools,
            )

            total_steps += task_result.get("steps", 1)

            if task_result.get("success"):
                self._plan.advance()
            elif task_result.get("blocked"):
                # Try backtracking
                if current_task.attempts >= self._max_task_attempts:
                    self._plan.backtrack()
                    self.add_to_history({
                        "phase": "backtracking",
                        "reason": task_result.get("reason"),
                    })
            else:
                # Task failed
                if current_task.attempts >= self._max_task_attempts:
                    return AgentResult(
                        success=False,
                        message=f"Failed at {current_task.app_name}",
                        error=task_result.get("reason", "Unknown error"),
                        steps_taken=total_steps,
                    )

        if self._plan.is_complete():
            final_vars = await self._get_all_variables()
            return AgentResult(
                success=True,
                message=f"Completed {len(self._plan.tasks)} app tasks",
                steps_taken=total_steps,
                final_state=final_vars,
            )

        return AgentResult(
            success=False,
            error=f"Max rounds ({self.config.max_rounds}) reached",
            steps_taken=total_steps,
        )

    async def _execute_app_task(
        self,
        task: AppTask,
        input_values: dict[str, Any],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Execute a single app task using ReAct loop.

        Args:
            task: App task to execute
            input_values: Input variable values
            tools: Available tools

        Returns:
            Execution result dict
        """
        prompt = LOW_LEVEL_REACT_PROMPT.format(
            app_name=task.app_name,
            description=task.description,
            input_vars=json.dumps(input_values, ensure_ascii=False),
            output_vars=task.output_variables,
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": prompt},
        ]

        steps = 0
        for _ in range(self._max_react_steps):
            steps += 1

            # Take screenshot and analyze
            screenshot = await self.take_screenshot()
            if not screenshot.get("success"):
                return {"success": False, "reason": "Screenshot failed", "steps": steps}

            analysis = await self.analyze_screen(
                screenshot["image_base64"],
                context=task.description,
            )

            messages.append({
                "role": "user",
                "content": f"Screen: {analysis.description}\nElements: {json.dumps(analysis.elements, ensure_ascii=False)}",
            })

            # Get LLM decision
            response = await self.llm_client.chat.completions.create(
                model=self.config.llm_model,
                messages=messages,  # type: ignore
                tools=tools if tools else None,  # type: ignore
            )

            assistant_msg = response.choices[0].message
            content = assistant_msg.content or ""

            # Check completion
            if "TASK_COMPLETE:" in content:
                return {
                    "success": True,
                    "summary": content.split("TASK_COMPLETE:")[1].strip(),
                    "steps": steps,
                }

            if "TASK_BLOCKED:" in content:
                return {
                    "success": False,
                    "blocked": True,
                    "reason": content.split("TASK_BLOCKED:")[1].strip(),
                    "steps": steps,
                }

            if "TASK_FAILED:" in content:
                return {
                    "success": False,
                    "reason": content.split("TASK_FAILED:")[1].strip(),
                    "steps": steps,
                }

            # Execute tool calls
            if assistant_msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_msg.tool_calls
                    ],
                })

                for tool_call in assistant_msg.tool_calls:
                    try:
                        args = json.loads(tool_call.function.arguments)
                        result = await self.execute_tool(tool_call.function.name, **args)
                    except Exception as e:
                        result = {"success": False, "error": str(e)}

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
            else:
                messages.append({"role": "assistant", "content": content})

        return {
            "success": False,
            "reason": f"Max ReAct steps ({self._max_react_steps}) reached",
            "steps": steps,
        }

    async def _get_all_variables(self) -> dict[str, Any]:
        """Get all stored variables."""
        try:
            result = await self.plugin.variable_storage(action="list")
            return result.get("variables", {})
        except Exception:
            return {}
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/agents/mobile/test_hierarchical.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/odin/agents/mobile/hierarchical.py tests/unit/agents/mobile/test_hierarchical.py
git commit -m "feat(mobile): implement MobileHierarchicalAgent with app-level decomposition"
```

---

### Task 13: Update agents/__init__.py exports

**Files:**
- Modify: `src/odin/agents/mobile/__init__.py`

**Step 1: Update exports**

`src/odin/agents/mobile/__init__.py`:
```python
"""Mobile agents for Odin framework."""

from odin.agents.mobile.base import (
    MobileAgentBase,
    MobileAgentConfig,
    AgentResult,
    VisionAnalysis,
)
from odin.agents.mobile.react import MobileReActAgent
from odin.agents.mobile.plan_execute import MobilePlanExecuteAgent, TaskPlan, PlanStep
from odin.agents.mobile.hierarchical import MobileHierarchicalAgent, HighLevelPlan, AppTask

__all__ = [
    "MobileAgentBase",
    "MobileAgentConfig",
    "AgentResult",
    "VisionAnalysis",
    "MobileReActAgent",
    "MobilePlanExecuteAgent",
    "TaskPlan",
    "PlanStep",
    "MobileHierarchicalAgent",
    "HighLevelPlan",
    "AppTask",
]
```

**Step 2: Commit**

```bash
git add src/odin/agents/mobile/__init__.py
git commit -m "feat(mobile): export all agent classes from mobile agents module"
```

---

## Phase 4: Configuration and Integration

### Task 14: Add MobileSettings to config

**Files:**
- Modify: `src/odin/config/settings.py`

**Step 1: Add mobile configuration to settings**

Add the following to `src/odin/config/settings.py`:

```python
class MobileSettings(BaseModel):
    """Mobile automation settings."""

    # Controller
    controller_type: Literal["adb", "hdc", "ios"] = Field(
        default="adb",
        description="Device controller type",
    )
    device_id: str | None = Field(
        default=None,
        description="Device serial number",
    )
    adb_path: str = Field(
        default="adb",
        description="Path to adb executable",
    )
    hdc_path: str = Field(
        default="hdc",
        description="Path to hdc executable",
    )
    tool_delay_ms: int = Field(
        default=400,
        description="Delay after each tool execution (ms)",
    )

    # Agent
    agent_mode: Literal["react", "plan_execute", "hierarchical"] = Field(
        default="react",
        description="Agent execution mode",
    )
    max_rounds: int = Field(
        default=50,
        description="Maximum execution rounds",
    )

    # LLM (for planning/reasoning)
    llm_model: str = Field(
        default="gpt-4o",
        description="LLM model for planning",
    )
    llm_base_url: str | None = Field(
        default=None,
        description="LLM API base URL",
    )
    llm_api_key: str | None = Field(
        default=None,
        description="LLM API key",
    )

    # VLM (for vision)
    vlm_model: str = Field(
        default="gpt-4o",
        description="VLM model for screen analysis",
    )
    vlm_base_url: str | None = Field(
        default=None,
        description="VLM API base URL",
    )
    vlm_api_key: str | None = Field(
        default=None,
        description="VLM API key",
    )

    # Interaction
    interaction_type: Literal["cli", "gui"] = Field(
        default="cli",
        description="Human interaction handler type",
    )

    model_config = SettingsConfigDict(
        env_prefix="ODIN_MOBILE_",
    )


# Add to main Settings class
class Settings(BaseSettings):
    # ... existing fields ...
    mobile: MobileSettings = Field(default_factory=MobileSettings)
```

**Step 2: Commit**

```bash
git add src/odin/config/settings.py
git commit -m "feat(mobile): add MobileSettings configuration"
```

---

### Task 15: Create mobile agent factory

**Files:**
- Create: `src/odin/agents/mobile/factory.py`
- Create: `tests/unit/agents/mobile/test_factory.py`

**Step 1: Write failing tests**

`tests/unit/agents/mobile/test_factory.py`:
```python
"""Tests for mobile agent factory."""

import pytest
from unittest.mock import MagicMock, patch

from odin.agents.mobile.factory import create_mobile_agent, MobileAgentType
from odin.agents.mobile.react import MobileReActAgent
from odin.agents.mobile.plan_execute import MobilePlanExecuteAgent
from odin.agents.mobile.hierarchical import MobileHierarchicalAgent


class TestMobileAgentFactory:
    """Test mobile agent factory."""

    @pytest.fixture
    def mock_plugin(self):
        """Create mock plugin."""
        return MagicMock()

    def test_create_react_agent(self, mock_plugin):
        """Factory creates ReAct agent."""
        agent = create_mobile_agent(
            agent_type=MobileAgentType.REACT,
            plugin=mock_plugin,
        )
        assert isinstance(agent, MobileReActAgent)

    def test_create_plan_execute_agent(self, mock_plugin):
        """Factory creates Plan+Execute agent."""
        agent = create_mobile_agent(
            agent_type=MobileAgentType.PLAN_EXECUTE,
            plugin=mock_plugin,
        )
        assert isinstance(agent, MobilePlanExecuteAgent)

    def test_create_hierarchical_agent(self, mock_plugin):
        """Factory creates Hierarchical agent."""
        agent = create_mobile_agent(
            agent_type=MobileAgentType.HIERARCHICAL,
            plugin=mock_plugin,
        )
        assert isinstance(agent, MobileHierarchicalAgent)

    def test_create_from_string(self, mock_plugin):
        """Factory accepts string agent type."""
        agent = create_mobile_agent(
            agent_type="react",
            plugin=mock_plugin,
        )
        assert isinstance(agent, MobileReActAgent)

    def test_create_with_custom_config(self, mock_plugin):
        """Factory accepts custom configuration."""
        agent = create_mobile_agent(
            agent_type=MobileAgentType.REACT,
            plugin=mock_plugin,
            max_rounds=100,
            llm_model="deepseek-v3",
        )
        assert agent.config.max_rounds == 100
        assert agent.config.llm_model == "deepseek-v3"

    def test_invalid_agent_type(self, mock_plugin):
        """Factory raises error for invalid type."""
        with pytest.raises(ValueError, match="Unknown agent type"):
            create_mobile_agent(
                agent_type="invalid",
                plugin=mock_plugin,
            )
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/agents/mobile/test_factory.py -v
```

Expected: FAIL

**Step 3: Implement factory.py**

`src/odin/agents/mobile/factory.py`:
```python
"""Factory for creating mobile agents."""

from enum import Enum
from typing import Any

from openai import AsyncOpenAI

from odin.agents.mobile.base import MobileAgentBase, MobileAgentConfig
from odin.agents.mobile.react import MobileReActAgent
from odin.agents.mobile.plan_execute import MobilePlanExecuteAgent
from odin.agents.mobile.hierarchical import MobileHierarchicalAgent
from odin.plugins.builtin.mobile.plugin import MobilePlugin


class MobileAgentType(str, Enum):
    """Mobile agent types."""

    REACT = "react"
    PLAN_EXECUTE = "plan_execute"
    HIERARCHICAL = "hierarchical"


AGENT_CLASSES: dict[MobileAgentType, type[MobileAgentBase]] = {
    MobileAgentType.REACT: MobileReActAgent,
    MobileAgentType.PLAN_EXECUTE: MobilePlanExecuteAgent,
    MobileAgentType.HIERARCHICAL: MobileHierarchicalAgent,
}


def create_mobile_agent(
    agent_type: MobileAgentType | str,
    plugin: MobilePlugin,
    llm_client: AsyncOpenAI | None = None,
    vlm_client: AsyncOpenAI | None = None,
    **config_kwargs: Any,
) -> MobileAgentBase:
    """Create a mobile agent of the specified type.

    Args:
        agent_type: Type of agent to create
        plugin: Mobile plugin instance
        llm_client: Optional LLM client
        vlm_client: Optional VLM client
        **config_kwargs: Configuration overrides

    Returns:
        Mobile agent instance

    Raises:
        ValueError: If agent type is unknown
    """
    # Convert string to enum if needed
    if isinstance(agent_type, str):
        try:
            agent_type = MobileAgentType(agent_type.lower())
        except ValueError:
            raise ValueError(f"Unknown agent type: {agent_type}")

    agent_class = AGENT_CLASSES.get(agent_type)
    if agent_class is None:
        raise ValueError(f"Unknown agent type: {agent_type}")

    config = MobileAgentConfig(**config_kwargs)

    return agent_class(
        config=config,
        plugin=plugin,
        llm_client=llm_client,
        vlm_client=vlm_client,
    )
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/agents/mobile/test_factory.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/odin/agents/mobile/factory.py tests/unit/agents/mobile/test_factory.py
git commit -m "feat(mobile): add mobile agent factory"
```

---

### Task 16: Run all mobile tests

**Step 1: Run complete test suite for mobile module**

```bash
uv run pytest tests/unit/plugins/mobile/ tests/unit/agents/mobile/ -v
```

Expected: All tests PASS

**Step 2: Run type checking**

```bash
uv run mypy src/odin/plugins/builtin/mobile src/odin/agents/mobile
```

Expected: No errors

**Step 3: Run linting**

```bash
uv run ruff check src/odin/plugins/builtin/mobile src/odin/agents/mobile
```

Expected: No errors

**Step 4: Final commit**

```bash
git add .
git commit -m "feat(mobile): complete mobile automation module with tests"
```

---

## Summary

Implementation complete! The mobile automation module includes:

**Plugin Layer:**
- `BaseController` - Abstract device controller interface
- `ADBController` - Android device control via ADB
- `MobilePlugin` - All automation tools (click, scroll, input, screenshot, etc.)
- `AppRegistry` - App name/alias lookup
- `HumanInteractionHandler` - CLI/GUI interaction abstraction

**Agent Layer:**
- `MobileAgentBase` - Common agent functionality with VLM analysis
- `MobileReActAgent` - Think → Act → Observe loop
- `MobilePlanExecuteAgent` - Plan first, execute adaptively
- `MobileHierarchicalAgent` - App-level decomposition with variable passing

**Configuration:**
- `MobileSettings` - Environment-based configuration
- `MobileAgentType` - Enum for agent selection
- `create_mobile_agent()` - Factory function

Total: 16 tasks with TDD approach (test first, implement, verify)
