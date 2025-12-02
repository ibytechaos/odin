"""Tests for the logging module."""

import pytest
import logging
from unittest.mock import patch, MagicMock

import structlog

from odin.logging import get_logger, setup_logging
from odin.logging.logger import add_trace_id


class TestAddTraceId:
    """Test add_trace_id processor."""

    def test_add_trace_id_without_otel(self):
        """Test trace ID processor without OpenTelemetry."""
        event_dict = {"event": "test", "level": "info"}

        # When OpenTelemetry is not active, should not add trace_id
        result = add_trace_id(None, "info", event_dict)

        assert result == event_dict
        assert "trace_id" not in result

    def test_add_trace_id_with_otel_span(self):
        """Test trace ID processor with active OpenTelemetry span."""
        from opentelemetry import trace as otel_trace
        from opentelemetry.sdk.trace import TracerProvider

        # Setup tracing
        provider = TracerProvider()
        otel_trace.set_tracer_provider(provider)
        tracer = otel_trace.get_tracer(__name__)

        event_dict = {"event": "test", "level": "info"}

        with tracer.start_as_current_span("test_span") as span:
            result = add_trace_id(None, "info", event_dict.copy())

            # Should have trace_id and span_id
            assert "trace_id" in result
            assert "span_id" in result
            assert len(result["trace_id"]) == 32  # 128-bit trace ID as hex
            assert len(result["span_id"]) == 16  # 64-bit span ID as hex

    def test_add_trace_id_exception_handling(self):
        """Test that exceptions are handled gracefully."""
        event_dict = {"event": "test"}

        # Patch the import inside the function to simulate OpenTelemetry error
        with patch.dict("sys.modules", {"opentelemetry": MagicMock()}):
            import sys
            mock_otel = sys.modules["opentelemetry"]
            mock_otel.trace.get_current_span.side_effect = Exception("OTEL Error")

            # Should not raise, just return original event_dict
            result = add_trace_id(None, "info", event_dict.copy())
            # Result should still be a dict (no crash)
            assert isinstance(result, dict)


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_default(self):
        """Test default logging setup."""
        setup_logging()

        # Should create a working logger
        logger = get_logger("test")
        assert logger is not None

    def test_setup_logging_debug_level(self):
        """Test logging setup with DEBUG level."""
        # Force reset logging configuration
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.NOTSET)

        setup_logging(log_level="DEBUG")

        # Root logger should be at DEBUG level after setup
        # Note: basicConfig sets level on root logger
        assert root_logger.level == logging.DEBUG or root_logger.getEffectiveLevel() == logging.DEBUG

    def test_setup_logging_json_format(self):
        """Test logging setup with JSON format."""
        setup_logging(log_level="INFO", json_format=True)

        logger = get_logger("test")
        assert logger is not None

    def test_setup_logging_no_colors(self):
        """Test logging setup without colors."""
        setup_logging(log_level="INFO", json_format=False, enable_colors=False)

        logger = get_logger("test")
        assert logger is not None

    def test_setup_logging_silences_noisy_loggers(self):
        """Test that noisy loggers are silenced."""
        setup_logging()

        # These should be at WARNING level or higher
        assert logging.getLogger("httpx").level >= logging.WARNING
        assert logging.getLogger("httpcore").level >= logging.WARNING
        assert logging.getLogger("openai").level >= logging.WARNING
        assert logging.getLogger("anthropic").level >= logging.WARNING


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_with_name(self):
        """Test getting logger with a name."""
        logger = get_logger("test_module")
        assert logger is not None

    def test_get_logger_without_name(self):
        """Test getting logger without a name."""
        logger = get_logger()
        assert logger is not None

    def test_get_logger_returns_bound_logger(self):
        """Test that get_logger returns a bound logger."""
        # Ensure structlog is configured first
        setup_logging()
        logger = get_logger("test")
        # structlog may return different wrapper types depending on configuration
        # The important thing is it has the standard logging methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "bind")

    def test_logger_can_log(self, capfd):
        """Test that logger can actually log messages."""
        setup_logging(log_level="DEBUG", json_format=False, enable_colors=False)
        logger = get_logger("test_logger")

        # This should work without errors
        logger.info("Test message", key="value")

    def test_logger_bind_context(self):
        """Test binding context to logger."""
        logger = get_logger("test")
        bound_logger = logger.bind(request_id="123")

        assert bound_logger is not None


class TestLoggingLevels:
    """Test different logging levels."""

    def test_log_levels(self):
        """Test all log levels work."""
        setup_logging(log_level="DEBUG")
        logger = get_logger("test_levels")

        # All these should work without errors
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

    def test_log_with_exception(self):
        """Test logging with exception info."""
        setup_logging(log_level="ERROR")
        logger = get_logger("test_exception")

        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("An error occurred")


class TestLoggingWithContext:
    """Test logging with context variables."""

    def test_log_with_extra_fields(self):
        """Test logging with extra fields."""
        setup_logging(log_level="INFO")
        logger = get_logger("test_context")

        # Should not raise
        logger.info(
            "Message with context",
            user_id="123",
            action="test",
            data={"key": "value"},
        )

    def test_log_bind_and_unbind(self):
        """Test binding and unbinding context."""
        logger = get_logger("test_bind")

        # Bind context
        bound = logger.bind(request_id="abc123")
        assert bound is not None

        # Should be able to log with bound context
        bound.info("Bound message")

        # Unbind
        unbound = bound.unbind("request_id")
        unbound.info("Unbound message")
