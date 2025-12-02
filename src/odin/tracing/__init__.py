"""OpenTelemetry tracing and metrics for Odin framework."""

from odin.tracing.decorators import timed, traced
from odin.tracing.metrics import MetricsCollector, get_metrics_collector
from odin.tracing.setup import setup_tracing, shutdown_tracing

__all__ = [
    "MetricsCollector",
    "get_metrics_collector",
    "setup_tracing",
    "shutdown_tracing",
    "timed",
    "traced",
]
