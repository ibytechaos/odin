"""Decorators for automatic tracing and metrics collection."""

import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from odin.logging import get_logger
from odin.tracing.metrics import get_metrics_collector

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def traced(
    name: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], F]:
    """Decorator to automatically trace a function.

    Args:
        name: Span name (defaults to function name)
        attributes: Additional span attributes

    Example:
        ```python
        @traced(name="my_operation", attributes={"user_id": "123"})
        async def my_function():
            pass
        ```
    """

    def decorator(func: F) -> F:
        tracer = trace.get_tracer(__name__)
        span_name = name or f"{func.__module__}.{func.__name__}"

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with tracer.start_as_current_span(span_name) as span:
                    # Add attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                    # Add function arguments as attributes
                    if kwargs:
                        for key, value in kwargs.items():
                            if isinstance(value, (str, int, float, bool)):
                                span.set_attribute(f"arg.{key}", value)

                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        raise

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with tracer.start_as_current_span(span_name) as span:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                    if kwargs:
                        for key, value in kwargs.items():
                            if isinstance(value, (str, int, float, bool)):
                                span.set_attribute(f"arg.{key}", value)

                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        raise

            return sync_wrapper  # type: ignore

    return decorator


def timed(
    metric_name: str | None = None,
    labels: dict[str, str] | None = None,
) -> Callable[[F], F]:
    """Decorator to automatically record execution time as a metric.

    Args:
        metric_name: Metric name (defaults to function name)
        labels: Additional metric labels

    Example:
        ```python
        @timed(metric_name="api_latency", labels={"endpoint": "/users"})
        async def fetch_users():
            pass
        ```
    """

    def decorator(func: F) -> F:
        metrics_collector = get_metrics_collector()
        name = metric_name or f"{func.__module__}.{func.__name__}"

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    metrics_collector.record_latency(
                        name, duration, labels or {}
                    )

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    metrics_collector.record_latency(
                        name, duration, labels or {}
                    )

            return sync_wrapper  # type: ignore

    return decorator
