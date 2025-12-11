"""Mobile WebSocket protocol for Odin framework.

Exposes Dexter mobile agent via WebSocket for device-side integration.
"""

from odin.protocols.mobile.client import MobileClient
from odin.protocols.mobile.server import MobileWebSocketServer

__all__ = ["MobileClient", "MobileWebSocketServer"]
