"""AG-UI (Agent-User Interaction Protocol) support for Odin framework.

Implements the AG-UI protocol for generative UI and real-time agent interactions.
Reference: https://docs.ag-ui.com/
"""

from odin.protocols.agui.adapter import AGUIAdapter
from odin.protocols.agui.models import (
    AGUIEvent,
    EventType,
    Message,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageChunkEvent,
    ToolCallChunkEvent,
)
from odin.protocols.agui.server import AGUIServer

__all__ = [
    "AGUIServer",
    "AGUIAdapter",
    "RunAgentInput",
    "Message",
    "AGUIEvent",
    "EventType",
    "RunStartedEvent",
    "RunFinishedEvent",
    "RunErrorEvent",
    "TextMessageChunkEvent",
    "ToolCallChunkEvent",
]
