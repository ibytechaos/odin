"""Structured logging configuration using structlog."""

import logging
import sys
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from structlog.typing import EventDict, Processor


def add_trace_id(
    _logger: Any, _method_name: str, event_dict: EventDict
) -> EventDict:
    """Add trace ID to log records if available.

    Args:
        _logger: Logger instance (unused, required by structlog API)
        _method_name: Method name being called (unused, required by structlog API)
        event_dict: Event dictionary

    Returns:
        Updated event dictionary
    """
    # Try to get trace ID from OpenTelemetry context
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
    except Exception:
        # OpenTelemetry not available or no active span
        pass

    return event_dict


def setup_logging(
    log_level: str = "INFO",
    json_format: bool = False,
    enable_colors: bool = True,
) -> None:
    """Setup structured logging for Odin.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, output JSON logs; otherwise human-readable
        enable_colors: Enable colored output (only for non-JSON format)
    """
    # Configure processors based on format
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_trace_id,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_format:
        # JSON output for production
        processors.extend(
            [
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ]
        )
    else:
        # Human-readable output for development
        processors.extend(
            [
                structlog.processors.ExceptionRenderer(),
                structlog.dev.ConsoleRenderer(colors=enable_colors),
            ]
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)
