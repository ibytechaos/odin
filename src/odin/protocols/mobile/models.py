"""Data models for Mobile WebSocket protocol.

Based on docs/openapi.yaml specification.
"""

from typing import Any

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """Device information."""

    deviceType: str = Field(default="ohos", description="Device type (ohos, android, ios)")
    deviceName: str = Field(default="phone", description="Device name")
    manufacturer: str = Field(default="", description="Device manufacturer")
    sysVersion: str = Field(default="", description="System version")


class DialogueTurn(BaseModel):
    """A single turn in dialogue history."""

    role: str = Field(..., description="Role: user, assistant, or tool")
    content: str = Field(..., description="Content of the turn")


class TaskExecutionRequest(BaseModel):
    """Request model for task execution.

    Sent from device to server via WebSocket.
    """

    uid: str | None = Field(None, description="User ID")
    appName: str | None = Field(None, description="Current app name")
    availableAppList: list[str] | None = Field(None, description="Available app list")
    instruction: str = Field(..., description="Task instruction")
    screen: dict[str, Any] | None = Field(None, description="Screen info including widget tree")
    deviceId: str | None = Field(None, description="Device ID")
    sessionId: str | None = Field(None, description="Session ID")
    interactionId: str | None = Field(None, description="Interaction session ID")
    deviceInfo: DeviceInfo | None = Field(None, description="Device information")
    dialogue: list[DialogueTurn] | None = Field(None, description="Dialogue history")


class DirectiveHeader(BaseModel):
    """Directive header."""

    namespace: str = Field(default="mobile", description="Directive namespace")
    name: str = Field(..., description="Directive name (click, input, scroll, etc.)")
    messageId: str | None = Field(None, description="Message ID for tracking")


class DirectivePayload(BaseModel):
    """Directive payload - action parameters."""

    # Common fields
    userSidePrompt: str | None = Field(None, description="User-facing prompt")

    # click action
    point_2d: list[float] | None = Field(None, description="Click coordinates [x, y] (0-1)")
    num_clicks: int | None = Field(None, description="Number of clicks")

    # input action
    text: str | None = Field(None, description="Text to input")
    enter: bool | None = Field(None, description="Press enter after input")

    # scroll action
    point_2d_start: list[float] | None = Field(None, description="Scroll start [x, y]")
    point_2d_end: list[float] | None = Field(None, description="Scroll end [x, y]")

    # open_app action
    appname: str | None = Field(None, description="App name to open")

    # wait action
    duration: int | None = Field(None, description="Wait duration in ms")

    # human_interact action
    prompt: str | None = Field(None, description="Prompt for human interaction")

    # variable_storage action
    operation: str | None = Field(None, description="Variable operation")
    name: str | None = Field(None, description="Variable name")
    value: str | None = Field(None, description="Variable value")


class Directive(BaseModel):
    """A single directive to send to device."""

    header: DirectiveHeader
    payload: DirectivePayload


class TaskExecutionResponse(BaseModel):
    """Response model for task execution.

    Sent from server to device via WebSocket.
    """

    directives: list[Directive] = Field(default_factory=list, description="Directives for device")
    finish: bool = Field(default=False, description="Whether task is finished")
    errorCode: str = Field(default="0", description="Error code (0 = success)")
    errorMessage: str = Field(default="", description="Error message if any")
    assistantMessage: str | None = Field(None, description="Assistant thinking/message")
