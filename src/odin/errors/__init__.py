"""Odin error handling system."""

from odin.errors.base import (
    ConfigurationError,
    ExecutionError,
    OdinError,
    PluginError,
    ProtocolError,
    RetryableError,
    StorageError,
    TracingError,
)
from odin.errors.codes import ErrorCode
from odin.errors.handlers import ErrorHandler, format_error

__all__ = [
    "ConfigurationError",
    "ErrorCode",
    "ErrorHandler",
    "ExecutionError",
    "OdinError",
    "PluginError",
    "ProtocolError",
    "RetryableError",
    "StorageError",
    "TracingError",
    "format_error",
]
