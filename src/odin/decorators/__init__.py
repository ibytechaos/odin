"""Decorators for Odin framework.

Provides convenient decorators for:
- Automatic tool registration
- Metrics collection
- Tracing
- Parameter validation
"""

from odin.decorators.tool import tool
from odin.decorators.metrics import measure_latency, count_calls, track_errors

__all__ = [
    "tool",
    "measure_latency",
    "count_calls",
    "track_errors",
]
