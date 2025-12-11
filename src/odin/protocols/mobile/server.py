"""Mobile WebSocket Server for Odin framework.

Exposes Dexter mobile agent via WebSocket. The device sends task requests
with screen info, and the server responds with action directives.

Flow:
1. Device connects via WebSocket
2. Device sends TaskExecutionRequest (instruction + screen state)
3. Server processes with Dexter agent
4. Server returns TaskExecutionResponse (directives)
5. Device executes directives and sends next request
6. Repeat until task is complete
"""

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI

from odin.agents.mobile.dexter import DEXTER_TOOLS, MobileDexterAgent
from odin.logging import get_logger
from odin.protocols.mobile.models import (
    Directive,
    DirectiveHeader,
    DirectivePayload,
    TaskExecutionRequest,
    TaskExecutionResponse,
)

logger = get_logger(__name__)


# Dexter prompts (from dexter.py)
DEXTER_SYSTEM_PROMPT = """You are a GUI action planner. Your job is to finish the mainTask.
- You need to follow the rules below:
- If the webpage content hasn't loaded, please use the `wait` tool to allow time for the content to load.
- Do not use the 'variable_storage' tool repeatly.
- Repeated use 'scroll' tool too many times may indicate that you've reached the bottom of the page.
- Step back and rethink your approach if you find yourself repeating the same actions to avoid getting stuck in an infinite loop.
- Any operation carries the risk of not matching expectations. You can flexibly plan your actions based on the actual execution situation and the goal.
- Before completing the task, please make sure to carefully check if the task has been completed fully and accurately.
- Always respond in Chinese.
"""

DEXTER_HUMAN_PROMPT = """
* HUMAN INTERACT
During the task execution process, you can use the `human_interact` tool to interact with humans, please call it in the following situations:
- When performing dangerous operations such as payment, authorization, deleting files, confirmation from humans is required.
- Whenever encountering obstacles while accessing websites, such as requiring user login, providing user information, captcha verification, QR code scanning, or human verification, you have to request manual assistance.
- The `human_interact` tool does not support parallel calls.
"""

DEXTER_TASK_PROMPT_TEMPLATE = """
Current datetime: {datetime}

# User input task instructions
<root>
 <!-- Main task, completed through the collaboration of multiple Agents -->
 <mainTask>main task</mainTask>
 <!-- The tasks that the current agent needs to complete, the current agent only needs to complete the currentTask -->
 <currentTask>specific task</currentTask>
 <!-- Complete the corresponding step nodes of the task, Only for reference -->
 <nodes>
 <!-- node supports input/output variables to pass dependencies -->
 <node input="variable name" output="variable name" status="todo / done">task step node</node>
 </nodes>
</root>

"""

DEXTER_SCREENSHOT_PROMPT = (
    "This is the environmental information after the operation, including the latest browser screenshot. "
    "Please perform the next operation based on the environmental information."
)


class MobileSession:
    """A mobile automation session."""

    def __init__(
        self,
        session_id: str,
        llm_client: AsyncOpenAI,
        llm_model: str = "gpt-4o",
        temperature: float = 0.1,
    ):
        self.session_id = session_id
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.temperature = temperature
        self.messages: list[dict[str, Any]] = []
        self.variables: dict[str, str] = {}
        self.step_count = 0
        self.max_steps = 50
        self.task_finished = False
        self.current_task: str | None = None

    def _build_system_prompt(self) -> str:
        """Build system prompt."""
        dt_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        return DEXTER_SYSTEM_PROMPT + DEXTER_HUMAN_PROMPT + DEXTER_TASK_PROMPT_TEMPLATE.format(datetime=dt_str)

    def start_task(self, instruction: str) -> None:
        """Start a new task."""
        self.messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": [{"type": "text", "text": f"<root><mainTask>{instruction}</mainTask><currentTask>{instruction}</currentTask><nodes></nodes></root>"}]},
        ]
        self.step_count = 0
        self.task_finished = False
        self.current_task = instruction
        logger.info(f"[Session {self.session_id}] Started task: {instruction}")

    def add_screenshot(self, screen_data: dict[str, Any] | None, screenshot_b64: str | None = None) -> None:
        """Add screenshot to messages.

        Args:
            screen_data: Screen info dict (may contain screenshot)
            screenshot_b64: Base64 encoded screenshot image
        """
        # Try to get screenshot from screen_data if not provided directly
        img_b64 = screenshot_b64
        if img_b64 is None and screen_data:
            img_b64 = screen_data.get("screenshot") or screen_data.get("image")

        if not img_b64:
            logger.warning(f"[Session {self.session_id}] No screenshot provided")
            return

        # Remove old screenshot messages
        self.messages = [m for m in self.messages if not self._is_screenshot_message(m)]

        # Add new screenshot
        self.messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": DEXTER_SCREENSHOT_PROMPT},
            ],
        })

    def add_tool_result(self, tool_call_id: str, result: str) -> None:
        """Add tool execution result."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result,
        })

    def _is_screenshot_message(self, msg: dict[str, Any]) -> bool:
        """Check if message is a screenshot message."""
        if msg.get("role") != "user":
            return False
        content = msg.get("content")
        if not isinstance(content, list):
            return False
        return any(
            isinstance(part, dict) and part.get("type") == "image_url"
            for part in content
        )

    async def get_next_action(self) -> tuple[list[dict[str, Any]], str | None, bool]:
        """Call LLM to get next action.

        Returns:
            Tuple of (tool_calls, assistant_message, is_finished)
        """
        self.step_count += 1

        if self.step_count > self.max_steps:
            logger.warning(f"[Session {self.session_id}] Max steps reached")
            return [], "Max steps reached", True

        # Debug log
        logger.info(f"[Session {self.session_id}] Step {self.step_count}, calling LLM...")

        response = await self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=self.messages,  # type: ignore
            tools=DEXTER_TOOLS,  # type: ignore
            temperature=self.temperature,
        )

        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        # Add assistant message to history
        assistant_msg: dict[str, Any] = {"role": "assistant"}
        if msg.content:
            assistant_msg["content"] = msg.content
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        self.messages.append(assistant_msg)

        # Check if done
        if not msg.tool_calls or finish_reason != "tool_calls":
            self.task_finished = True
            logger.info(f"[Session {self.session_id}] Task finished")
            return [], msg.content, True

        # Extract tool calls
        tool_calls = []
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "arguments": args,
            })
            logger.info(f"[Session {self.session_id}] Tool call: {tc.function.name}")

        return tool_calls, msg.content, False


class MobileWebSocketServer:
    """WebSocket server for mobile automation.

    Provides WebSocket endpoint for devices to interact with Dexter agent.
    """

    def __init__(
        self,
        llm_client: AsyncOpenAI | None = None,
        llm_model: str = "gpt-4o",
        name: str = "Odin Mobile WebSocket API",
    ):
        """Initialize WebSocket server.

        Args:
            llm_client: OpenAI-compatible client
            llm_model: Model name
            name: API name
        """
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.sessions: dict[str, MobileSession] = {}

        # Create FastAPI app
        self.app = FastAPI(
            title=name,
            description="WebSocket API for mobile automation with Dexter agent",
            version="1.0.0",
        )

        self._setup_routes()

    def _get_or_create_session(self, session_id: str | None) -> MobileSession:
        """Get existing session or create new one."""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]

        new_id = session_id or str(uuid.uuid4())
        session = MobileSession(
            session_id=new_id,
            llm_client=self.llm_client,  # type: ignore
            llm_model=self.llm_model,
        )
        self.sessions[new_id] = session
        logger.info(f"Created new session: {new_id}")
        return session

    def _tool_call_to_directive(self, tool_call: dict[str, Any]) -> Directive:
        """Convert tool call to directive."""
        name = tool_call["name"]
        args = tool_call["arguments"]

        header = DirectiveHeader(
            namespace="mobile",
            name=name,
            messageId=tool_call.get("id"),
        )

        payload = DirectivePayload(
            userSidePrompt=args.get("userSidePrompt"),
            point_2d=args.get("point_2d"),
            num_clicks=args.get("num_clicks"),
            text=args.get("text"),
            enter=args.get("enter"),
            point_2d_start=args.get("point_2d_start"),
            point_2d_end=args.get("point_2d_end"),
            appname=args.get("appname"),
            duration=args.get("duration"),
            prompt=args.get("prompt"),
            operation=args.get("operation"),
            name=args.get("name"),
            value=args.get("value"),
        )

        return Directive(header=header, payload=payload)

    def _setup_routes(self):
        """Setup FastAPI routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "name": "Odin Mobile WebSocket API",
                "version": "1.0.0",
                "endpoints": {
                    "websocket": "/ws",
                    "http_operate": "/operate",
                    "health": "/health",
                },
            }

        @self.app.get("/health")
        async def health():
            """Health check."""
            return {
                "status": "healthy",
                "sessions": len(self.sessions),
            }

        @self.app.post("/operate")
        async def http_operate(request: TaskExecutionRequest) -> TaskExecutionResponse:
            """HTTP endpoint for task execution (alternative to WebSocket)."""
            return await self._handle_request(request)

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for mobile automation."""
            await websocket.accept()
            logger.info("WebSocket client connected")

            try:
                while True:
                    # Receive request
                    data = await websocket.receive_json()
                    request = TaskExecutionRequest(**data)

                    # Process request
                    response = await self._handle_request(request)

                    # Send response
                    await websocket.send_json(response.model_dump())

            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                try:
                    error_response = TaskExecutionResponse(
                        directives=[],
                        finish=True,
                        errorCode="500",
                        errorMessage=str(e),
                    )
                    await websocket.send_json(error_response.model_dump())
                except Exception:
                    pass

    async def _handle_request(self, request: TaskExecutionRequest) -> TaskExecutionResponse:
        """Handle task execution request.

        Args:
            request: Task execution request from device

        Returns:
            Task execution response with directives
        """
        try:
            # Get or create session
            session = self._get_or_create_session(request.sessionId)

            # Check if this is a new task or continuation
            if session.current_task != request.instruction or session.task_finished:
                # New task
                session.start_task(request.instruction)

            # Add screenshot if provided
            if request.screen:
                session.add_screenshot(request.screen)

            # Get next action from LLM
            tool_calls, assistant_message, is_finished = await session.get_next_action()

            if is_finished:
                return TaskExecutionResponse(
                    directives=[],
                    finish=True,
                    errorCode="0",
                    errorMessage="",
                    assistantMessage=assistant_message,
                )

            # Convert tool calls to directives
            directives = [self._tool_call_to_directive(tc) for tc in tool_calls]

            # Pre-add tool results (device will execute and confirm)
            for tc in tool_calls:
                session.add_tool_result(tc["id"], json.dumps({"success": True}))

            return TaskExecutionResponse(
                directives=directives,
                finish=False,
                errorCode="0",
                errorMessage="",
                assistantMessage=assistant_message,
            )

        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return TaskExecutionResponse(
                directives=[],
                finish=True,
                errorCode="500",
                errorMessage=str(e),
            )

    async def run(self, host: str = "0.0.0.0", port: int = 8080):
        """Run WebSocket server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        import uvicorn

        if self.llm_client is None:
            raise ValueError("llm_client is required. Set it before running.")

        logger.info(f"Starting Mobile WebSocket server on {host}:{port}")

        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        try:
            await server.serve()
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
