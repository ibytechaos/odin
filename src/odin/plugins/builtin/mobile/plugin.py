"""Mobile automation plugin for Odin framework.

Tool definitions are designed to match dexter_mobile project for compatibility.
"""

import asyncio
import base64
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import Field

from odin.decorators.tool import tool
from odin.plugins.base import DecoratorPlugin
from odin.plugins.builtin.mobile.configs.app_loader import AndroidAppConfig, HarmonyAppConfig, get_app_mapper
from odin.plugins.builtin.mobile.coordinates import normalize_coordinate
from odin.plugins.builtin.mobile.interaction import (
    HumanInteractionHandler,
    InputType,
    NoOpInteractionHandler,
)

if TYPE_CHECKING:
    from odin.plugins.builtin.mobile.controllers.base import BaseController


class MobilePlugin(DecoratorPlugin):
    """Mobile device automation plugin.

    Provides tools for controlling mobile devices through various
    controllers (ADB, HDC, iOS). Supports screen interaction,
    app management, and human-in-the-loop operations.

    Tool definitions match dexter_mobile project for compatibility.
    """

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
        return "Mobile device automation tools"

    def __init__(
        self,
        controller: BaseController | None = None,
        interaction_handler: HumanInteractionHandler | None = None,
        tool_delay_ms: int = 400,
        auto_init: bool = True,
    ):
        """Initialize the mobile plugin.

        Args:
            controller: Device controller instance
            interaction_handler: Handler for human interaction requests
            tool_delay_ms: Delay after each tool execution in milliseconds
            auto_init: If True, auto-initialize controller from settings when not provided
        """
        super().__init__()
        self._controller = controller
        self._interaction_handler = interaction_handler or NoOpInteractionHandler()
        self._tool_delay_ms = tool_delay_ms
        self._variables: dict[str, str] = {}
        self._auto_init = auto_init
        self._last_screen_size: tuple[int, int] | None = None

    def _init_controller_from_settings(self) -> BaseController | None:
        """Initialize controller from Odin settings."""
        try:
            from odin.config.settings import get_settings
            from odin.plugins.builtin.mobile.controllers.adb import ADBConfig, ADBController
            from odin.plugins.builtin.mobile.controllers.hdc import HDCConfig, HDCController

            settings = get_settings()

            if settings.mobile_controller == "adb":
                adb_config = ADBConfig(
                    device_id=settings.mobile_device_id,
                    adb_path=settings.mobile_adb_path,
                )
                return ADBController(adb_config)
            elif settings.mobile_controller == "hdc":
                hdc_config = HDCConfig(
                    device_id=settings.mobile_device_id,
                    hdc_path=settings.mobile_hdc_path,
                )
                return HDCController(hdc_config)
            else:
                return None
        except Exception:
            return None

    def set_controller(self, controller: BaseController) -> None:
        """Set the device controller."""
        self._controller = controller

    def set_interaction_handler(self, handler: HumanInteractionHandler) -> None:
        """Set the human interaction handler."""
        self._interaction_handler = handler

    def _ensure_controller(self) -> BaseController:
        """Ensure controller is set and return it.

        If no controller is set and auto_init is enabled, attempts to
        initialize controller from Odin settings.
        """
        if self._controller is None and self._auto_init:
            self._controller = self._init_controller_from_settings()

        if self._controller is None:
            raise RuntimeError(
                "No controller configured. Set ODIN_MOBILE_CONTROLLER and "
                "ODIN_MOBILE_DEVICE_ID in .env, or call set_controller() manually."
            )
        return self._controller

    async def _apply_delay(self) -> None:
        """Apply configured delay after tool execution."""
        if self._tool_delay_ms > 0:
            await asyncio.sleep(self._tool_delay_ms / 1000)

    def _map_point_to_pixels(self, point: list[float]) -> tuple[int, int]:
        """Map normalized coordinates [x, y] to pixel coordinates.

        Supports:
        - 0-1 range: normalized coordinates
        - 1-1000 range: per-mille coordinates
        - >1000: pixel coordinates
        """
        if not self._last_screen_size:
            raise ValueError("No screen size available for coordinate mapping")

        width, height = self._last_screen_size
        x, y = point[0], point[1]

        px = normalize_coordinate(x, width)
        py = normalize_coordinate(y, height)

        return int(px), int(py)

    # =========================================================================
    # Tools matching dexter_mobile format
    # =========================================================================

    @tool(description="Click at given page coordinates.")
    async def click(
        self,
        point_2d: Annotated[list[float], Field(description="Coordinate as [x, y]", json_schema_extra={"minItems": 2, "maxItems": 2})],
        userSidePrompt: Annotated[str, Field(description="The user-side prompt, showing what you are doing")],  # noqa: ARG002
        num_clicks: Annotated[int, Field(description="number of times to click the element")] = 1,
        button: Annotated[Literal["left", "right", "middle"], Field(description="Mouse button type")] = "left",  # noqa: ARG002
    ) -> dict[str, Any]:
        """Click at the specified screen position."""
        controller = self._ensure_controller()

        # Update screen size cache
        self._last_screen_size = await controller.get_cached_screen_size()

        px, py = self._map_point_to_pixels(point_2d)
        num_clicks = max(1, num_clicks)

        for i in range(num_clicks):
            await controller.tap(px, py)
            if i + 1 < num_clicks:
                await asyncio.sleep(0.1)

        await self._apply_delay()
        return {
            "success": True,
            "message": f"click executed at ({px}, {py}) num_clicks={num_clicks}",
        }

    @tool(description="Input text given page coordinates.")
    async def input(
        self,
        text: Annotated[str, Field(description="Text to input")],
        point_2d: Annotated[list[float], Field(description="Coordinate as [x, y] to focus before input", json_schema_extra={"minItems": 2, "maxItems": 2})],
        userSidePrompt: Annotated[str, Field(description="The user-side prompt, showing what you are doing")],  # noqa: ARG002
        enter: Annotated[bool, Field(description="Press enter after input")] = False,
    ) -> dict[str, Any]:
        """Input text at the specified position."""
        controller = self._ensure_controller()

        # Update screen size cache
        self._last_screen_size = await controller.get_cached_screen_size()

        # Click at position first if provided
        if point_2d:
            px, py = self._map_point_to_pixels(point_2d)
            await controller.tap(px, py)
            await asyncio.sleep(0.2)

        # Input text
        await controller.input_text(text)

        if enter:
            await controller.press_key("enter")

        await self._apply_delay()
        return {
            "success": True,
            "message": f"input executed text='{text}' enter={enter}"
            + (f" at ({px}, {py})" if point_2d else ""),
        }

    @tool(
        description="Wait/pause execution for a specified duration. "
        "Use this tool when you need to wait for data loading, page rendering, "
        "or introduce delays between operations."
    )
    async def wait(
        self,
        userSidePrompt: Annotated[str, Field(description="The user-side prompt, showing what you are doing")],  # noqa: ARG002
        duration: Annotated[int, Field(description="Wait duration in milliseconds")] = 500,
    ) -> dict[str, Any]:
        """Wait for the specified duration."""
        duration = max(200, min(10000, duration))
        await asyncio.sleep(duration / 1000)
        return {"success": True, "message": f"wait executed for {duration} ms"}

    @tool(description="Open an app by name (app name will be mapped to package/activity).")
    async def open_app(
        self,
        appname: Annotated[str, Field(description="Logical app name (mapped to package/activity by the agent).")],
        userSidePrompt: Annotated[str, Field(description="The user-side prompt, showing what you are doing")],  # noqa: ARG002
    ) -> dict[str, Any]:
        """Open an application by name or alias."""
        controller = self._ensure_controller()

        # Detect platform from controller type
        from odin.plugins.builtin.mobile.controllers.hdc import HDCController

        platform = "harmony" if isinstance(controller, HDCController) else "android"

        # Try to resolve app name using the mapper
        mapper = get_app_mapper()
        result = mapper.resolve(appname, platform=platform)

        if result:
            _, config = result
            if isinstance(config, AndroidAppConfig):
                package = config.package
                activity = config.activity
            elif isinstance(config, HarmonyAppConfig):
                # For Harmony, construct "module/ability" format for activity
                package = config.bundle
                activity = f"{config.module}/{config.ability}"
            else:
                # For other platforms, treat app_name as package name
                package = appname
                activity = None
        else:
            # Treat as direct package name
            package = appname
            activity = None

        await controller.open_app(package, activity)
        await self._apply_delay()
        return {
            "success": True,
            "message": f"open_app executed appname='{appname}' package='{package}' activity='{activity or ''}'",
        }

    @tool(
        description="Ask the human user for help or input via CLI; "
        "the text will be added as a user message and the loop continues."
    )
    async def human_interact(
        self,
        userSidePrompt: Annotated[str, Field(description="The user-side prompt, showing what you are doing")],  # noqa: ARG002
        prompt: Annotated[str, Field(description="Display prompts to users")],
    ) -> dict[str, Any]:
        """Request human intervention/input."""
        result = await self._interaction_handler.request_input(
            prompt=prompt,
            input_type=InputType.TEXT,
        )

        error_detail = ""
        if not result.success:
            if result.cancelled:
                error_detail = "cancelled"
            elif result.timed_out:
                error_detail = "timed_out"
            else:
                error_detail = "unknown_error"

        return {
            "success": result.success,
            "value": result.value,
            "cancelled": result.cancelled,
            "timed_out": result.timed_out,
            "message": f"human_interact prompt='{prompt}'"
            + (f" error='{error_detail}'" if error_detail else ""),
        }

    @tool(
        description="Store/read/list shared variables across agents. "
        "Use when nodes contain input/output attributes."
    )
    async def variable_storage(
        self,
        operation: Annotated[
            Literal["read_variable", "write_variable", "list_all_variable"],
            Field(description="read_variable: get value(s); write_variable: set value; list_all_variable: list keys."),
        ],
        name: Annotated[str | None, Field(description="Variable name(s). For read, supports comma-separated list.")] = None,
        value: Annotated[str | None, Field(description="Value to store when operation is write_variable.")] = None,
        userSidePrompt: Annotated[str | None, Field(description="The user-side prompt")] = None,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Read, write or list shared variables."""
        if operation == "read_variable":
            if not name:
                return {"value": None}
            keys = [k.strip() for k in name.split(",") if k.strip()]
            if len(keys) == 1:
                return {"value": self._variables.get(keys[0])}
            else:
                return {"value": {k: self._variables.get(k) for k in keys}}

        elif operation == "write_variable":
            if not name:
                return {"error": "write_variable missing name"}
            self._variables[name] = value or ""
            return {"message": f"write_variable {name} completed, please continue"}

        elif operation == "list_all_variable":
            return {"variables": list(self._variables.keys())}

        else:
            return {"error": f"unsupported operation {operation}"}

    @tool(
        description="Scroll from start to end coordinates. "
        "Only scroll down(right) when the content at the bottom(rightmost) exceeds the visible area."
    )
    async def scroll(
        self,
        point_2d_start: Annotated[list[float], Field(description="Scroll start coordinate as [x, y]", json_schema_extra={"minItems": 2, "maxItems": 2})],
        point_2d_end: Annotated[list[float], Field(description="Scroll end coordinate as [x, y]", json_schema_extra={"minItems": 2, "maxItems": 2})],
        userSidePrompt: Annotated[str, Field(description="The user-side prompt, showing what you are doing")],  # noqa: ARG002
    ) -> dict[str, Any]:
        """Swipe/scroll on the screen."""
        controller = self._ensure_controller()

        # Update screen size cache
        self._last_screen_size = await controller.get_cached_screen_size()

        sx, sy = self._map_point_to_pixels(point_2d_start)
        ex, ey = self._map_point_to_pixels(point_2d_end)

        await controller.swipe(sx, sy, ex, ey, duration_ms=100)

        # Post-scroll wait to allow content to settle
        await asyncio.sleep(1.5)

        return {
            "success": True,
            "message": f"scroll executed from ({sx},{sy}) to ({ex},{ey})",
        }

    # =========================================================================
    # Additional utility tools (not in dexter_mobile)
    # =========================================================================

    @tool(description="Long press at screen position")
    async def long_press(
        self,
        point_2d: Annotated[list[float], Field(description="Coordinate as [x, y]", json_schema_extra={"minItems": 2, "maxItems": 2})],
        userSidePrompt: Annotated[str, Field(description="The user-side prompt, showing what you are doing")],  # noqa: ARG002
        duration_ms: Annotated[int, Field(description="Long press duration in milliseconds")] = 1000,
    ) -> dict[str, Any]:
        """Long press at the specified screen position."""
        controller = self._ensure_controller()

        # Update screen size cache
        self._last_screen_size = await controller.get_cached_screen_size()

        px, py = self._map_point_to_pixels(point_2d)

        await controller.long_press(px, py, duration_ms)
        await self._apply_delay()
        return {
            "success": True,
            "message": f"long_press executed at ({px}, {py}) duration={duration_ms}ms",
        }

    @tool(description="Take screenshot and return current screen state")
    async def screenshot(self) -> dict[str, Any]:
        """Take a screenshot and return as base64."""
        controller = self._ensure_controller()

        png_bytes = await controller.screenshot()
        base64_data = base64.b64encode(png_bytes).decode("utf-8")

        width, height = await controller.get_cached_screen_size()
        self._last_screen_size = (width, height)

        return {
            "success": True,
            "image_base64": base64_data,
            "width": width,
            "height": height,
            "format": "png",
        }

    @tool(description="Press hardware/software key")
    async def press_key(
        self,
        key: Annotated[str, Field(description="Key name: back/home/enter/volume_up/volume_down")],
        userSidePrompt: Annotated[str, Field(description="The user-side prompt, showing what you are doing")],  # noqa: ARG002
    ) -> dict[str, Any]:
        """Press a hardware/software key."""
        controller = self._ensure_controller()

        await controller.press_key(key)
        await self._apply_delay()
        return {"success": True, "message": f"press_key executed key={key}"}

    @tool(description="Check device connection status")
    async def check_connection(self) -> dict[str, Any]:
        """Check if the device is connected."""
        controller = self._ensure_controller()

        connected = await controller.is_connected()

        result: dict[str, Any] = {"success": True, "connected": connected}

        if connected:
            width, height = await controller.get_cached_screen_size()
            result["screen_size"] = {"width": width, "height": height}
            self._last_screen_size = (width, height)

        return result
