"""HTTP/REST API for Odin framework."""

from odin.protocols.http.adapter import HTTPAdapter
from odin.protocols.http.server import HTTPServer

__all__ = ["HTTPAdapter", "HTTPServer"]
