"""Decorators for Odin framework.

Provides convenient decorators for:
- Automatic tool registration
- Metrics collection
- Tracing
- Parameter validation
"""

from odin.decorators.metrics import count_calls, measure_latency, track_errors
from odin.decorators.tool import tool

__all__ = [
    "count_calls",
    "measure_latency",
    "tool",
    "track_errors",
]
