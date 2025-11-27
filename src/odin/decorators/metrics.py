"""Metrics collection decorators."""

import functools
import time
from typing import Any, Callable, TypeVar

from odin.tracing import get_metrics_collector

F = TypeVar("F", bound=Callable[..., Any])


def measure_latency(
    metric_name: str | None = None,
    labels: dict[str, str] | None = None,
) -> Callable[[F], F]:
    """Decorator to automatically measure function latency.

    Example:
        ```python
        @measure_latency(metric_name="api.request")
        async def fetch_data():
            pass
        ```

    Args:
        metric_name: Metric name (defaults to module.function)
        labels: Additional metric labels

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        metrics = get_metrics_collector()
        name = metric_name or f"{func.__module__}.{func.__name__}"

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    return await func(*args, **kwargs)
                finally:
                    latency = time.time() - start_time
                    metrics.record_latency(name, latency, labels or {})

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    return func(*args, **kwargs)
                finally:
                    latency = time.time() - start_time
                    metrics.record_latency(name, latency, labels or {})

            return sync_wrapper  # type: ignore

    return decorator


def count_calls(
    metric_name: str | None = None,
    labels: dict[str, str] | None = None,
) -> Callable[[F], F]:
    """Decorator to count function calls.

    Example:
        ```python
        @count_calls(metric_name="api.requests", labels={"endpoint": "/users"})
        async def get_users():
            pass
        ```

    Args:
        metric_name: Metric name (defaults to module.function.calls)
        labels: Additional metric labels

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        metrics = get_metrics_collector()
        name = metric_name or f"{func.__module__}.{func.__name__}.calls"

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                metrics.increment_counter(name, 1, labels or {})
                return await func(*args, **kwargs)

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                metrics.increment_counter(name, 1, labels or {})
                return func(*args, **kwargs)

            return sync_wrapper  # type: ignore

    return decorator


def track_errors(
    metric_name: str | None = None,
    labels: dict[str, str] | None = None,
) -> Callable[[F], F]:
    """Decorator to track function errors.

    Example:
        ```python
        @track_errors(metric_name="api.errors")
        async def risky_operation():
            pass
        ```

    Args:
        metric_name: Metric name (defaults to module.function.errors)
        labels: Additional metric labels

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        metrics = get_metrics_collector()
        name = metric_name or f"{func.__module__}.{func.__name__}.errors"

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_labels = {
                        **(labels or {}),
                        "error_type": e.__class__.__name__,
                    }
                    metrics.increment_counter(name, 1, error_labels)
                    raise

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_labels = {
                        **(labels or {}),
                        "error_type": e.__class__.__name__,
                    }
                    metrics.increment_counter(name, 1, error_labels)
                    raise

            return sync_wrapper  # type: ignore

    return decorator


# Import asyncio at the end to avoid circular imports
import asyncio
