"""Base exception classes for Odin framework."""

from typing import Any

from odin.errors.codes import ErrorCode


class OdinError(Exception):
    """Base exception for all Odin errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize error.

        Args:
            message: Human-readable error message
            code: Error code from ErrorCode enum
            details: Additional error context
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        """Return formatted error string."""
        base = f"[{self.code}] {self.message}"
        if self.details:
            base += f" | Details: {self.details}"
        return base

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "error": self.__class__.__name__,
            "code": str(self.code),
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(OdinError):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.CONFIG_INVALID,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize configuration error."""
        super().__init__(message, code, details)


class PluginError(OdinError):
    """Plugin-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.PLUGIN_LOAD_FAILED,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize plugin error."""
        super().__init__(message, code, details)


class ProtocolError(OdinError):
    """Protocol-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.PROTOCOL_NOT_SUPPORTED,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize protocol error."""
        super().__init__(message, code, details)


class StorageError(OdinError):
    """Storage-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.STORAGE_NOT_AVAILABLE,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize storage error."""
        super().__init__(message, code, details)


class TracingError(OdinError):
    """Tracing-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.TRACING_INIT_FAILED,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize tracing error."""
        super().__init__(message, code, details)


class ExecutionError(OdinError):
    """Execution-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.AGENT_EXECUTION_FAILED,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize execution error."""
        super().__init__(message, code, details)


class RetryableError(OdinError):
    """Errors that can be retried."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        details: dict[str, Any] | None = None,
        retry_after: float | None = None,
    ) -> None:
        """Initialize retryable error.

        Args:
            message: Error message
            code: Error code
            details: Additional context
            retry_after: Suggested retry delay in seconds
        """
        super().__init__(message, code, details)
        self.retry_after = retry_after

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary."""
        result = super().to_dict()
        if self.retry_after is not None:
            result["retry_after"] = self.retry_after
        return result
