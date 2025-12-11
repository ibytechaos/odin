"""Mobile WebSocket Client for testing cloud-based mobile automation.

This client simulates a mobile device connecting to the Mobile WebSocket Server.
It sends task requests, receives directives, executes them locally via HDC/ADB,
and sends back results in a ReAct loop.

Usage:
    # As CLI
    odin mobile-client --task "打开设置" --server ws://localhost:8080/ws

    # Or directly
    python -m odin.protocols.mobile.client --task "打开设置"
"""

import asyncio
import base64
import json
import uuid
from typing import Any

import click
import websockets
from websockets.client import WebSocketClientProtocol

from odin.logging import get_logger
from odin.plugins.builtin.mobile import MobilePlugin
from odin.plugins.builtin.mobile.controllers.base import BaseController
from odin.protocols.mobile.models import (
    Directive,
    TaskExecutionRequest,
    TaskExecutionResponse,
)

logger = get_logger(__name__)


class MobileClient:
    """Mobile WebSocket client that executes server directives locally.

    Simulates a mobile device in cloud-testing scenario:
    1. Connect to server
    2. Send task request with screenshot
    3. Receive directives
    4. Execute directives locally
    5. Send execution result and new screenshot
    6. Repeat until task complete
    """

    def __init__(
        self,
        controller: BaseController,
        server_url: str = "ws://localhost:8080/ws",
        session_id: str | None = None,
    ):
        """Initialize the mobile client.

        Args:
            controller: Device controller (HDC/ADB) for local execution
            server_url: WebSocket server URL
            session_id: Optional session ID for continuity
        """
        self.controller = controller
        self.server_url = server_url
        self.session_id = session_id or str(uuid.uuid4())
        self.plugin = MobilePlugin(controller=controller)
        self._screen_size: tuple[int, int] | None = None

    async def _take_screenshot(self) -> str:
        """Take screenshot and return base64 encoded string."""
        img_bytes = await self.controller.screenshot()
        return base64.b64encode(img_bytes).decode("utf-8")

    async def _get_screen_info(self) -> dict[str, Any]:
        """Get current screen info including screenshot."""
        screenshot_b64 = await self._take_screenshot()

        if self._screen_size is None:
            self._screen_size = await self.controller.get_screen_size()

        return {
            "screenshot": screenshot_b64,
            "width": self._screen_size[0],
            "height": self._screen_size[1],
        }

    async def _execute_directive(self, directive: Directive) -> dict[str, Any]:
        """Execute a single directive locally.

        Args:
            directive: Directive from server

        Returns:
            Execution result dict
        """
        action = directive.header.name
        payload = directive.payload

        logger.info(f"Executing directive: {action}")

        try:
            # Map directive to plugin tool call
            if action == "click":
                result = await self.plugin.click(
                    point_2d=payload.point_2d or [0.5, 0.5],
                    userSidePrompt=payload.userSidePrompt or "",
                    num_clicks=payload.num_clicks or 1,
                )
            elif action == "input":
                result = await self.plugin.input(
                    text=payload.text or "",
                    point_2d=payload.point_2d or [0.5, 0.5],
                    userSidePrompt=payload.userSidePrompt or "",
                    enter=payload.enter or False,
                )
            elif action == "scroll":
                result = await self.plugin.scroll(
                    point_2d_start=payload.point_2d_start or [0.5, 0.7],
                    point_2d_end=payload.point_2d_end or [0.5, 0.3],
                    userSidePrompt=payload.userSidePrompt or "",
                )
            elif action == "wait":
                result = await self.plugin.wait(
                    userSidePrompt=payload.userSidePrompt or "",
                    duration=payload.duration or 500,
                )
            elif action == "open_app":
                result = await self.plugin.open_app(
                    appname=payload.appname or "",
                    userSidePrompt=payload.userSidePrompt or "",
                )
            elif action == "human_interact":
                # For human_interact, we prompt the user in CLI
                click.echo(f"\n[Human Interaction Required]: {payload.prompt}")
                user_input = click.prompt("Your response", default="")
                result = {
                    "success": True,
                    "value": user_input,
                    "cancelled": False,
                    "timed_out": False,
                }
            elif action == "variable_storage":
                result = await self.plugin.variable_storage(
                    operation=payload.operation or "list_all_variable",
                    name=payload.name,
                    value=payload.value,
                )
            else:
                logger.warning(f"Unknown action: {action}")
                result = {"success": False, "error": f"Unknown action: {action}"}

            return result

        except Exception as e:
            logger.error(f"Directive execution error: {e}")
            return {"success": False, "error": str(e)}

    async def run_task(self, instruction: str, max_rounds: int = 50) -> dict[str, Any]:
        """Run a task through the server.

        Args:
            instruction: Task instruction
            max_rounds: Maximum interaction rounds

        Returns:
            Final result dict
        """
        click.echo(f"Connecting to server: {self.server_url}")
        click.echo(f"Session ID: {self.session_id}")
        click.echo(f"Task: {instruction}")
        click.echo()

        # Initialize screen size
        self._screen_size = await self.controller.get_screen_size()
        self.plugin._last_screen_size = self._screen_size
        click.echo(f"Screen size: {self._screen_size[0]}x{self._screen_size[1]}")

        async with websockets.connect(self.server_url) as ws:
            round_num = 0

            while round_num < max_rounds:
                round_num += 1
                click.echo(f"\n{'='*50}")
                click.echo(f"Round {round_num}")
                click.echo(f"{'='*50}")

                # Get current screen state
                click.echo("Taking screenshot...")
                screen_info = await self._get_screen_info()

                # Build request
                request = TaskExecutionRequest(
                    instruction=instruction,
                    sessionId=self.session_id,
                    screen=screen_info,
                )

                # Send request
                request_json = request.model_dump_json()
                click.echo("Sending request to server...")

                # Print request (truncate screenshot for readability)
                request_for_print = request.model_dump()
                if request_for_print.get("screen") and request_for_print["screen"].get("screenshot"):
                    screenshot_len = len(request_for_print["screen"]["screenshot"])
                    request_for_print["screen"]["screenshot"] = f"[BASE64_IMAGE: {screenshot_len} chars]"
                click.echo(click.style("\n>>> REQUEST:", fg="cyan", bold=True))
                click.echo(json.dumps(request_for_print, indent=2, ensure_ascii=False))

                await ws.send(request_json)

                # Receive response
                click.echo("\nWaiting for server response...")
                response_data = await ws.recv()
                response = TaskExecutionResponse.model_validate_json(response_data)

                # Print response
                click.echo(click.style("\n<<< RESPONSE:", fg="green", bold=True))
                click.echo(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))

                # Display response info
                if response.assistantMessage:
                    click.echo(f"Assistant: {response.assistantMessage[:200]}...")

                if response.errorCode != "0":
                    click.echo(click.style(f"Error: {response.errorMessage}", fg="red"))

                # Check if finished
                if response.finish:
                    click.echo(click.style("\nTask Completed!", fg="green", bold=True))
                    return {
                        "success": response.errorCode == "0",
                        "message": response.assistantMessage or "Task completed",
                        "rounds": round_num,
                    }

                # Execute directives
                if not response.directives:
                    click.echo("No directives received, waiting...")
                    await asyncio.sleep(1)
                    continue

                click.echo(f"\nReceived {len(response.directives)} directive(s):")

                for i, directive in enumerate(response.directives):
                    action = directive.header.name
                    prompt = directive.payload.userSidePrompt or ""
                    click.echo(f"  [{i+1}] {action}: {prompt}")

                # Execute each directive
                for directive in response.directives:
                    result = await self._execute_directive(directive)
                    status = "✓" if result.get("success") else "✗"
                    click.echo(f"  {status} {directive.header.name}: {result.get('message', result)}")

                # Small delay before next round
                await asyncio.sleep(0.5)

            click.echo(click.style(f"\nMax rounds ({max_rounds}) reached", fg="yellow"))
            return {
                "success": False,
                "message": f"Max rounds ({max_rounds}) reached",
                "rounds": round_num,
            }

    async def run_task_http(self, instruction: str, max_rounds: int = 50) -> dict[str, Any]:
        """Run a task using HTTP endpoint instead of WebSocket.

        Args:
            instruction: Task instruction
            max_rounds: Maximum interaction rounds

        Returns:
            Final result dict
        """
        import httpx

        # Convert ws:// to http://
        http_url = self.server_url.replace("ws://", "http://").replace("/ws", "/operate")

        click.echo(f"Using HTTP endpoint: {http_url}")
        click.echo(f"Session ID: {self.session_id}")
        click.echo(f"Task: {instruction}")
        click.echo()

        # Initialize screen size
        self._screen_size = await self.controller.get_screen_size()
        self.plugin._last_screen_size = self._screen_size
        click.echo(f"Screen size: {self._screen_size[0]}x{self._screen_size[1]}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            round_num = 0

            while round_num < max_rounds:
                round_num += 1
                click.echo(f"\n{'='*50}")
                click.echo(f"Round {round_num}")
                click.echo(f"{'='*50}")

                # Get current screen state
                click.echo("Taking screenshot...")
                screen_info = await self._get_screen_info()

                # Build request
                request = TaskExecutionRequest(
                    instruction=instruction,
                    sessionId=self.session_id,
                    screen=screen_info,
                )

                # Send request
                click.echo("Sending request to server...")

                # Print request (truncate screenshot for readability)
                request_for_print = request.model_dump()
                if request_for_print.get("screen") and request_for_print["screen"].get("screenshot"):
                    screenshot_len = len(request_for_print["screen"]["screenshot"])
                    request_for_print["screen"]["screenshot"] = f"[BASE64_IMAGE: {screenshot_len} chars]"
                click.echo(click.style("\n>>> REQUEST:", fg="cyan", bold=True))
                click.echo(json.dumps(request_for_print, indent=2, ensure_ascii=False))

                resp = await client.post(http_url, json=request.model_dump())
                resp.raise_for_status()

                response = TaskExecutionResponse.model_validate(resp.json())

                # Print response
                click.echo(click.style("\n<<< RESPONSE:", fg="green", bold=True))
                click.echo(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))

                # Display response info
                if response.assistantMessage:
                    click.echo(f"Assistant: {response.assistantMessage[:200]}...")

                if response.errorCode != "0":
                    click.echo(click.style(f"Error: {response.errorMessage}", fg="red"))

                # Check if finished
                if response.finish:
                    click.echo(click.style("\nTask Completed!", fg="green", bold=True))
                    return {
                        "success": response.errorCode == "0",
                        "message": response.assistantMessage or "Task completed",
                        "rounds": round_num,
                    }

                # Execute directives
                if not response.directives:
                    click.echo("No directives received, waiting...")
                    await asyncio.sleep(1)
                    continue

                click.echo(f"\nReceived {len(response.directives)} directive(s):")

                for i, directive in enumerate(response.directives):
                    action = directive.header.name
                    prompt = directive.payload.userSidePrompt or ""
                    click.echo(f"  [{i+1}] {action}: {prompt}")

                # Execute each directive
                for directive in response.directives:
                    result = await self._execute_directive(directive)
                    status = "✓" if result.get("success") else "✗"
                    click.echo(f"  {status} {directive.header.name}: {result.get('message', result)}")

                # Small delay before next round
                await asyncio.sleep(0.5)

            click.echo(click.style(f"\nMax rounds ({max_rounds}) reached", fg="yellow"))
            return {
                "success": False,
                "message": f"Max rounds ({max_rounds}) reached",
                "rounds": round_num,
            }


def create_controller_from_settings() -> BaseController:
    """Create controller from Odin settings."""
    from odin.config.settings import get_settings
    from odin.plugins.builtin.mobile.controllers.adb import ADBConfig, ADBController
    from odin.plugins.builtin.mobile.controllers.hdc import HDCConfig, HDCController

    settings = get_settings()

    if settings.mobile_controller == "hdc":
        config = HDCConfig(
            device_id=settings.mobile_device_id,
            hdc_path=settings.mobile_hdc_path,
        )
        return HDCController(config)
    else:
        # Default to ADB
        config = ADBConfig(
            device_id=settings.mobile_device_id,
            adb_path=settings.mobile_adb_path,
        )
        return ADBController(config)


@click.command("mobile-client")
@click.option("--task", "-t", required=True, help="Task instruction to execute")
@click.option("--server", "-s", default="ws://localhost:8080/ws", help="Server WebSocket URL")
@click.option("--http", is_flag=True, help="Use HTTP endpoint instead of WebSocket")
@click.option("--session-id", default=None, help="Session ID (auto-generated if not provided)")
@click.option("--max-rounds", default=50, type=int, help="Maximum interaction rounds")
@click.option("--controller", "-c", type=click.Choice(["adb", "hdc"]), default=None,
              help="Controller type (overrides settings)")
@click.option("--device-id", "-d", default=None, help="Device ID (overrides settings)")
def mobile_client_cli(
    task: str,
    server: str,
    http: bool,
    session_id: str | None,
    max_rounds: int,
    controller: str | None,
    device_id: str | None,
) -> None:
    """Mobile automation client for cloud testing.

    Connects to Mobile WebSocket Server, sends task requests,
    receives directives, executes them locally, and sends results back.

    Examples:

        odin mobile-client -t "打开设置"

        odin mobile-client -t "搜索天气" --server ws://192.168.1.100:8080/ws

        odin mobile-client -t "打开微信" --http

        odin mobile-client -t "打开设置" -c hdc -d <device_id>
    """
    async def _run():
        # Create controller
        if controller:
            from odin.plugins.builtin.mobile.controllers.adb import ADBConfig, ADBController
            from odin.plugins.builtin.mobile.controllers.hdc import HDCConfig, HDCController

            if controller == "hdc":
                config = HDCConfig(device_id=device_id)
                ctrl = HDCController(config)
            else:
                config = ADBConfig(device_id=device_id)
                ctrl = ADBController(config)
        else:
            ctrl = create_controller_from_settings()

        # Check connection
        click.echo("Checking device connection...")
        connected = await ctrl.is_connected()
        if not connected:
            click.echo(click.style("Device not connected!", fg="red"))
            raise SystemExit(1)
        click.echo(click.style("Device connected", fg="green"))

        # Create client
        client = MobileClient(
            controller=ctrl,
            server_url=server,
            session_id=session_id,
        )

        # Run task
        if http:
            result = await client.run_task_http(task, max_rounds)
        else:
            result = await client.run_task(task, max_rounds)

        # Print final result
        click.echo(f"\n{'='*50}")
        click.echo("Final Result:")
        click.echo(f"  Success: {result['success']}")
        click.echo(f"  Rounds: {result['rounds']}")
        click.echo(f"  Message: {result['message']}")

    asyncio.run(_run())


if __name__ == "__main__":
    mobile_client_cli()
