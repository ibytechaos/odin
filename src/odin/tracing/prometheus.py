"""Prometheus metrics exporter for Odin framework.

This module provides Prometheus-compatible metrics endpoint.
"""

from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from prometheus_client import REGISTRY, start_http_server

from odin.config import Settings
from odin.logging import get_logger

logger = get_logger(__name__)


def setup_prometheus_exporter(
    settings: Settings,
    port: int = 9090,
) -> None:
    """Setup Prometheus metrics exporter.

    This creates an HTTP endpoint at http://localhost:{port}/metrics
    that Prometheus can scrape.

    Args:
        settings: Application settings
        port: HTTP port for metrics endpoint (default: 9090)
    """
    logger.info("Setting up Prometheus exporter", port=port)

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.env,
        }
    )

    # Create Prometheus metric reader
    prometheus_reader = PrometheusMetricReader()

    # Create meter provider with Prometheus reader
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[prometheus_reader],
    )

    # Set global meter provider
    from opentelemetry import metrics

    metrics.set_meter_provider(meter_provider)

    # Start HTTP server for Prometheus to scrape
    try:
        start_http_server(port=port, registry=REGISTRY)
        logger.info(
            "Prometheus metrics endpoint started",
            url=f"http://localhost:{port}/metrics",
        )
    except OSError as e:
        logger.error(
            "Failed to start Prometheus HTTP server",
            port=port,
            error=str(e),
        )
        raise


def get_prometheus_metrics_text() -> str:
    """Get current metrics in Prometheus text format.

    Returns:
        Metrics in Prometheus exposition format
    """
    from prometheus_client import generate_latest

    return generate_latest(REGISTRY).decode("utf-8")
