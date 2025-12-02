"""Tests for tracing decorators."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from odin.tracing.decorators import traced, timed


@pytest.fixture
def setup_tracing():
    """Setup OpenTelemetry tracing for tests."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(
        otel_trace.get_tracer_provider().get_tracer(__name__)._span_processor
        if hasattr(otel_trace.get_tracer_provider().get_tracer(__name__), "_span_processor")
        else None
    )
    otel_trace.set_tracer_provider(provider)
    return exporter


class TestTracedDecorator:
    """Test @traced decorator."""

    def test_traced_sync_function(self):
        """Test tracing a synchronous function."""

        @traced()
        def sync_func(x: int) -> int:
            return x * 2

        result = sync_func(5)
        assert result == 10

    def test_traced_sync_function_with_name(self):
        """Test tracing with custom span name."""

        @traced(name="custom_operation")
        def named_func() -> str:
            return "done"

        result = named_func()
        assert result == "done"

    def test_traced_sync_function_with_attributes(self):
        """Test tracing with custom attributes."""

        @traced(attributes={"user": "test", "version": "1.0"})
        def attributed_func() -> dict:
            return {"status": "ok"}

        result = attributed_func()
        assert result == {"status": "ok"}

    def test_traced_sync_function_with_kwargs(self):
        """Test tracing function with keyword arguments."""

        @traced()
        def kwargs_func(name: str, count: int = 5) -> dict:
            return {"name": name, "count": count}

        result = kwargs_func(name="test", count=10)
        assert result == {"name": "test", "count": 10}

    def test_traced_sync_function_exception(self):
        """Test tracing function that raises exception."""

        @traced()
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_func()

    @pytest.mark.asyncio
    async def test_traced_async_function(self):
        """Test tracing an asynchronous function."""

        @traced()
        async def async_func(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        result = await async_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_traced_async_function_with_name(self):
        """Test tracing async function with custom name."""

        @traced(name="async_custom_op")
        async def named_async_func() -> str:
            return "async_done"

        result = await named_async_func()
        assert result == "async_done"

    @pytest.mark.asyncio
    async def test_traced_async_function_with_attributes(self):
        """Test tracing async function with attributes."""

        @traced(attributes={"operation": "async_test"})
        async def attributed_async_func(value: str) -> dict:
            return {"value": value}

        result = await attributed_async_func(value="test")
        assert result == {"value": "test"}

    @pytest.mark.asyncio
    async def test_traced_async_function_exception(self):
        """Test tracing async function that raises exception."""

        @traced()
        async def failing_async_func():
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError, match="Async error"):
            await failing_async_func()

    def test_traced_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""

        @traced()
        def documented_func(x: int) -> int:
            """This is the docstring."""
            return x

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is the docstring."


class TestTimedDecorator:
    """Test @timed decorator."""

    def test_timed_sync_function(self):
        """Test timing a synchronous function."""
        with patch("odin.tracing.decorators.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector

            @timed()
            def sync_func() -> str:
                return "done"

            result = sync_func()

            assert result == "done"
            mock_collector.record_latency.assert_called_once()

    def test_timed_sync_function_with_name(self):
        """Test timing with custom metric name."""
        with patch("odin.tracing.decorators.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector

            @timed(metric_name="custom_metric")
            def named_func() -> int:
                return 42

            result = named_func()

            assert result == 42
            call_args = mock_collector.record_latency.call_args
            assert call_args[0][0] == "custom_metric"

    def test_timed_sync_function_with_labels(self):
        """Test timing with custom labels."""
        with patch("odin.tracing.decorators.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector

            @timed(labels={"endpoint": "/api/test"})
            def labeled_func() -> dict:
                return {}

            result = labeled_func()

            call_args = mock_collector.record_latency.call_args
            assert call_args[0][2] == {"endpoint": "/api/test"}

    def test_timed_sync_function_exception(self):
        """Test timing records even on exception."""
        with patch("odin.tracing.decorators.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector

            @timed()
            def failing_func():
                raise ValueError("Error")

            with pytest.raises(ValueError):
                failing_func()

            # Should still record latency
            mock_collector.record_latency.assert_called_once()

    @pytest.mark.asyncio
    async def test_timed_async_function(self):
        """Test timing an asynchronous function."""
        with patch("odin.tracing.decorators.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector

            @timed()
            async def async_func() -> str:
                await asyncio.sleep(0.01)
                return "async_done"

            result = await async_func()

            assert result == "async_done"
            mock_collector.record_latency.assert_called_once()

    @pytest.mark.asyncio
    async def test_timed_async_function_with_name(self):
        """Test timing async function with custom name."""
        with patch("odin.tracing.decorators.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector

            @timed(metric_name="async_operation")
            async def named_async_func() -> int:
                return 100

            result = await named_async_func()

            assert result == 100
            call_args = mock_collector.record_latency.call_args
            assert call_args[0][0] == "async_operation"

    @pytest.mark.asyncio
    async def test_timed_async_function_exception(self):
        """Test timing async function records on exception."""
        with patch("odin.tracing.decorators.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector

            @timed()
            async def failing_async():
                raise RuntimeError("Async failure")

            with pytest.raises(RuntimeError):
                await failing_async()

            mock_collector.record_latency.assert_called_once()

    def test_timed_preserves_function_metadata(self):
        """Test that timed decorator preserves function metadata."""

        @timed()
        def documented_func() -> str:
            """A documented function."""
            return "doc"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "A documented function."


class TestCombinedDecorators:
    """Test using both decorators together."""

    def test_both_decorators_sync(self):
        """Test using both @traced and @timed on sync function."""
        with patch("odin.tracing.decorators.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector

            @traced(name="combined_op")
            @timed(metric_name="combined_time")
            def combined_func(x: int) -> int:
                return x + 1

            result = combined_func(5)

            assert result == 6
            mock_collector.record_latency.assert_called_once()

    @pytest.mark.asyncio
    async def test_both_decorators_async(self):
        """Test using both @traced and @timed on async function."""
        with patch("odin.tracing.decorators.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector

            @traced(name="async_combined")
            @timed(metric_name="async_combined_time")
            async def combined_async(value: str) -> dict:
                await asyncio.sleep(0.01)
                return {"value": value}

            result = await combined_async(value="test")

            assert result == {"value": "test"}
            mock_collector.record_latency.assert_called_once()


class TestDecoratorEdgeCases:
    """Test edge cases for decorators."""

    def test_traced_with_complex_args(self):
        """Test traced with non-primitive arguments."""

        @traced()
        def complex_args_func(data: dict, items: list) -> int:
            return len(data) + len(items)

        result = complex_args_func({"a": 1}, [1, 2, 3])
        assert result == 4

    @pytest.mark.asyncio
    async def test_timed_measures_actual_time(self):
        """Test that timed actually measures time."""
        with patch("odin.tracing.decorators.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector

            @timed()
            async def slow_func():
                await asyncio.sleep(0.1)
                return "done"

            await slow_func()

            call_args = mock_collector.record_latency.call_args
            recorded_latency = call_args[0][1]
            assert recorded_latency >= 0.1

    def test_traced_without_arguments(self):
        """Test traced decorator without any arguments."""

        @traced()
        def no_args_func():
            return "no args"

        result = no_args_func()
        assert result == "no args"
