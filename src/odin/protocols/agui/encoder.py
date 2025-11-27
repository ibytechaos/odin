"""AG-UI Event Encoder for SSE streaming."""

import json

from odin.protocols.agui.models import AGUIEvent


class EventEncoder:
    """Encodes AG-UI events to Server-Sent Events format.

    Handles content negotiation based on Accept header and formats
    events for SSE streaming.
    """

    def __init__(self, accept: str | None = None):
        """Initialize event encoder.

        Args:
            accept: HTTP Accept header value
        """
        self.accept = accept or "text/event-stream"
        self._content_type = "text/event-stream"

    def get_content_type(self) -> str:
        """Get the content type for this encoder.

        Returns:
            Content-Type header value
        """
        return self._content_type

    def encode(self, event: AGUIEvent) -> str:
        """Encode an AG-UI event to SSE format.

        Args:
            event: Event to encode

        Returns:
            SSE-formatted string
        """
        # Convert event to dict
        event_dict = event.model_dump(exclude_none=True)

        # Format as SSE
        # SSE format: data: {json}\n\n
        json_str = json.dumps(event_dict, ensure_ascii=False)
        return f"data: {json_str}\n\n"
