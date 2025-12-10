"""Mobile automation plugin for Odin framework."""

import asyncio
import base64
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

from odin.decorators.tool import tool
from odin.plugins.base import DecoratorPlugin
from odin.plugins.builtin.mobile.configs.app_loader import get_app_mapper
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
    ):
        """Initialize the mobile plugin.

        Args:
            controller: Device controller instance
            interaction_handler: Handler for human interaction requests
            tool_delay_ms: Delay after each tool execution in milliseconds
        """
        super().__init__()
        self._controller = controller
        self._interaction_handler = interaction_handler or NoOpInteractionHandler()
        self._tool_delay_ms = tool_delay_ms
        self._variables: dict[str, str] = {}

    def set_controller(self, controller: BaseController) -> None:
        """Set the device controller."""
        self._controller = controller

    def set_interaction_handler(self, handler: HumanInteractionHandler) -> None:
        """Set the human interaction handler."""
        self._interaction_handler = handler

    def _ensure_controller(self) -> BaseController:
        """Ensure controller is set and return it."""
        if self._controller is None:
            raise RuntimeError("No controller configured. Call set_controller() first.")
        return self._controller

    async def _apply_delay(self) -> None:
        """Apply configured delay after tool execution."""
        if self._tool_delay_ms > 0:
            await asyncio.sleep(self._tool_delay_ms / 1000)

    @tool(description="点击屏幕指定位置")
    async def click(
        self,
        x: Annotated[float, Field(description="X坐标,支持0-1归一化/1-1000千分比/像素值")],
        y: Annotated[float, Field(description="Y坐标,支持0-1归一化/1-1000千分比/像素值")],
        count: Annotated[int, Field(description="点击次数")] = 1,
    ) -> dict[str, Any]:
        """Click at the specified screen position."""
        controller = self._ensure_controller()
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
        """Long press at the specified screen position."""
        controller = self._ensure_controller()
        width, height = await controller.get_cached_screen_size()

        px = normalize_coordinate(x, width)
        py = normalize_coordinate(y, height)

        await controller.long_press(px, py, duration_ms)
        await self._apply_delay()
        return {"success": True, "x": px, "y": py, "duration_ms": duration_ms}

    @tool(description="输入文本")
    async def input_text(
        self,
        text: Annotated[str, Field(description="要输入的文本")],
        press_enter: Annotated[bool, Field(description="输入后是否按回车")] = False,
    ) -> dict[str, Any]:
        """Input text on the device."""
        controller = self._ensure_controller()

        await controller.input_text(text)

        if press_enter:
            await controller.press_key("enter")

        await self._apply_delay()
        return {"success": True, "text": text, "press_enter": press_enter}

    @tool(description="滑动屏幕")
    async def scroll(
        self,
        x1: Annotated[float, Field(description="起点X坐标")],
        y1: Annotated[float, Field(description="起点Y坐标")],
        x2: Annotated[float, Field(description="终点X坐标")],
        y2: Annotated[float, Field(description="终点Y坐标")],
        duration_ms: Annotated[int, Field(description="滑动持续时间(毫秒)")] = 300,
    ) -> dict[str, Any]:
        """Swipe/scroll on the screen."""
        controller = self._ensure_controller()
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

    @tool(description="等待指定时间")
    async def wait(
        self,
        duration_ms: Annotated[int, Field(description="等待时间(毫秒)")],
    ) -> dict[str, Any]:
        """Wait for the specified duration."""
        await asyncio.sleep(duration_ms / 1000)
        return {"success": True, "duration_ms": duration_ms}

    @tool(description="打开应用")
    async def open_app(
        self,
        app_name: Annotated[str, Field(description="应用名称,支持别名如'微信'/'WeChat'")],
    ) -> dict[str, Any]:
        """Open an application by name or alias."""
        controller = self._ensure_controller()

        # Try to resolve app name using the mapper
        mapper = get_app_mapper()
        result = mapper.resolve(app_name, platform="android")

        if result:
            _, config = result
            package = config.package
            activity = config.activity
        else:
            # Treat as direct package name
            package = app_name
            activity = None

        await controller.open_app(package, activity)
        await self._apply_delay()
        return {"success": True, "app": app_name, "package": package}

    @tool(description="截图并返回当前屏幕状态")
    async def screenshot(self) -> dict[str, Any]:
        """Take a screenshot and return as base64."""
        controller = self._ensure_controller()

        png_bytes = await controller.screenshot()
        base64_data = base64.b64encode(png_bytes).decode("utf-8")

        width, height = await controller.get_cached_screen_size()

        return {
            "success": True,
            "image_base64": base64_data,
            "width": width,
            "height": height,
            "format": "png",
        }

    @tool(description="按键操作")
    async def press_key(
        self,
        key: Annotated[str, Field(description="按键名称: back/home/enter/volume_up/volume_down")],
    ) -> dict[str, Any]:
        """Press a hardware/software key."""
        controller = self._ensure_controller()

        await controller.press_key(key)
        await self._apply_delay()
        return {"success": True, "key": key}

    @tool(description="请求人工介入")
    async def human_interact(
        self,
        prompt: Annotated[str, Field(description="提示用户的信息")],
        input_type: Annotated[str, Field(description="输入类型: text/confirmation/choice")] = "text",
        choices: Annotated[list[str] | None, Field(description="选项列表(choice类型时)")] = None,
        timeout: Annotated[float | None, Field(description="超时时间(秒)")] = None,
    ) -> dict[str, Any]:
        """Request human intervention/input."""
        # Convert string to InputType enum
        try:
            input_type_enum = InputType(input_type)
        except ValueError:
            input_type_enum = InputType.TEXT

        result = await self._interaction_handler.request_input(
            prompt=prompt,
            input_type=input_type_enum,
            choices=choices,
            timeout=timeout,
        )

        return {
            "success": result.success,
            "value": result.value,
            "cancelled": result.cancelled,
            "timed_out": result.timed_out,
        }

    @tool(description="读写共享变量")
    async def variable_storage(
        self,
        action: Annotated[str, Field(description="操作: read/write/list/delete")],
        key: Annotated[str | None, Field(description="变量名")] = None,
        value: Annotated[str | None, Field(description="变量值(write时)")] = None,
    ) -> dict[str, Any]:
        """Read, write, list or delete shared variables."""
        if action == "read":
            if key is None:
                return {"success": False, "error": "Key required for read"}
            return {
                "success": True,
                "key": key,
                "value": self._variables.get(key),
                "exists": key in self._variables,
            }

        elif action == "write":
            if key is None:
                return {"success": False, "error": "Key required for write"}
            if value is None:
                return {"success": False, "error": "Value required for write"}
            self._variables[key] = value
            return {"success": True, "key": key, "value": value}

        elif action == "list":
            return {
                "success": True,
                "variables": list(self._variables.keys()),
                "count": len(self._variables),
            }

        elif action == "delete":
            if key is None:
                return {"success": False, "error": "Key required for delete"}
            existed = key in self._variables
            if existed:
                del self._variables[key]
            return {"success": True, "key": key, "deleted": existed}

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    @tool(description="检查设备连接状态")
    async def check_connection(self) -> dict[str, Any]:
        """Check if the device is connected."""
        controller = self._ensure_controller()

        connected = await controller.is_connected()

        result: dict[str, Any] = {"success": True, "connected": connected}

        if connected:
            width, height = await controller.get_cached_screen_size()
            result["screen_size"] = {"width": width, "height": height}

        return result
