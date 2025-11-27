"""Odin error handling system."""

from odin.errors.base import (
    OdinError,
    ConfigurationError,
    PluginError,
    ProtocolError,
    StorageError,
    TracingError,
    ExecutionError,
    RetryableError,
)
from odin.errors.codes import ErrorCode
from odin.errors.handlers import ErrorHandler, format_error

__all__ = [
    "OdinError",
    "ConfigurationError",
    "PluginError",
    "ProtocolError",
    "StorageError",
    "TracingError",
    "ExecutionError",
    "RetryableError",
    "ErrorCode",
    "ErrorHandler",
    "format_error",
]
