"""A2A (Agent-to-Agent) Protocol support for Odin framework.

Implements the Agent2Agent protocol specification for agent interoperability.
References: https://a2a-protocol.org/latest/specification/
"""

from odin.protocols.a2a.adapter import A2AAdapter
from odin.protocols.a2a.models import (
    AgentCard,
    Message,
    MessagePart,
    Task,
    TaskStatus,
    TaskState,
)
from odin.protocols.a2a.server import A2AServer

__all__ = [
    "A2AServer",
    "A2AAdapter",
    "AgentCard",
    "Message",
    "MessagePart",
    "Task",
    "TaskStatus",
    "TaskState",
]
