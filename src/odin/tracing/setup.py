"""OpenTelemetry setup and configuration."""

from typing import Literal

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from odin.config import Settings
from odin.logging import get_logger

logger = get_logger(__name__)

_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None


def setup_tracing(
    settings: Settings,
    exporter_type: Literal["otlp", "console"] = "otlp",
) -> None:
    """Setup OpenTelemetry tracing and metrics.

    Args:
        settings: Application settings
        exporter_type: Type of exporter to use (otlp or console for development)
    """
    global _tracer_provider, _meter_provider

    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled in settings")
        return

    logger.info(
        "Setting up OpenTelemetry",
        service_name=settings.otel_service_name,
        exporter=exporter_type,
    )

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.env,
        }
    )

    # Setup tracing
    _tracer_provider = TracerProvider(resource=resource)

    if exporter_type == "otlp":
        # OTLP exporter for production
        otlp_trace_exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=True,  # Use TLS in production
        )
        _tracer_provider.add_span_processor(
            BatchSpanProcessor(otlp_trace_exporter)
        )
    else:
        # Console exporter for development
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(
            BatchSpanProcessor(console_exporter)
        )

    trace.set_tracer_provider(_tracer_provider)

    # Setup metrics
    if exporter_type == "otlp":
        otlp_metric_exporter = OTLPMetricExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=True,
        )
        metric_reader = PeriodicExportingMetricReader(
            otlp_metric_exporter,
            export_interval_millis=60000,  # Export every 60s
        )
    else:
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

        console_metric_exporter = ConsoleMetricExporter()
        metric_reader = PeriodicExportingMetricReader(
            console_metric_exporter,
            export_interval_millis=60000,
        )

    _meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )
    metrics.set_meter_provider(_meter_provider)

    logger.info("OpenTelemetry setup complete")


def shutdown_tracing() -> None:
    """Shutdown OpenTelemetry and flush remaining spans/metrics."""
    global _tracer_provider, _meter_provider

    logger.info("Shutting down OpenTelemetry")

    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None

    if _meter_provider:
        _meter_provider.shutdown()
        _meter_provider = None

    logger.info("OpenTelemetry shutdown complete")


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance.

    Args:
        name: Tracer name (usually __name__)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Get a meter instance.

    Args:
        name: Meter name (usually __name__)

    Returns:
        Meter instance
    """
    return metrics.get_meter(name)
