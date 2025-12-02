"""Error handling utilities."""

import traceback
from typing import Any

from odin.errors.base import OdinError
from odin.errors.codes import ErrorCode


def format_error(error: Exception) -> dict[str, Any]:
    """Format any exception into a standardized error response.

    Args:
        error: The exception to format

    Returns:
        Dictionary containing error details
    """
    if isinstance(error, OdinError):
        return error.to_dict()

    return {
        "error": error.__class__.__name__,
        "code": str(ErrorCode.UNKNOWN),
        "message": str(error),
        "details": {
            "traceback": traceback.format_exc(),
        },
    }


class ErrorHandler:
    """Context manager for unified error handling."""

    def __init__(
        self,
        fallback_code: ErrorCode = ErrorCode.UNKNOWN,
        suppress: bool = False,
    ) -> None:
        """Initialize error handler.

        Args:
            fallback_code: Error code to use for non-Odin exceptions
            suppress: If True, suppress exceptions and return None
        """
        self.fallback_code = fallback_code
        self.suppress = suppress
        self.error: Exception | None = None

    def __enter__(self) -> ErrorHandler:
        """Enter context."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        """Exit context and handle any exceptions.

        Returns:
            True if exception should be suppressed
        """
        if exc_type is None:
            return False

        if isinstance(exc_val, Exception):
            self.error = exc_val

        return bool(self.suppress)

    def get_error_dict(self) -> dict[str, Any] | None:
        """Get formatted error dictionary if error occurred."""
        if self.error is None:
            return None
        return format_error(self.error)
