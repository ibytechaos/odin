"""Error codes for Odin framework."""

from enum import Enum


class ErrorCode(str, Enum):
    """Standardized error codes."""

    # Configuration errors (1xxx)
    CONFIG_MISSING = "ODIN-1001"
    CONFIG_INVALID = "ODIN-1002"
    CONFIG_LOAD_FAILED = "ODIN-1003"

    # Plugin errors (2xxx)
    PLUGIN_NOT_FOUND = "ODIN-2001"
    PLUGIN_LOAD_FAILED = "ODIN-2002"
    PLUGIN_INIT_FAILED = "ODIN-2003"
    PLUGIN_ALREADY_REGISTERED = "ODIN-2004"
    PLUGIN_DEPENDENCY_MISSING = "ODIN-2005"

    # Protocol errors (3xxx)
    PROTOCOL_NOT_SUPPORTED = "ODIN-3001"
    PROTOCOL_PARSE_ERROR = "ODIN-3002"
    PROTOCOL_SERIALIZATION_ERROR = "ODIN-3003"
    PROTOCOL_CONNECTION_ERROR = "ODIN-3004"

    # Storage errors (4xxx)
    STORAGE_NOT_AVAILABLE = "ODIN-4001"
    STORAGE_READ_ERROR = "ODIN-4002"
    STORAGE_WRITE_ERROR = "ODIN-4003"
    STORAGE_CONNECTION_ERROR = "ODIN-4004"

    # Tracing errors (5xxx)
    TRACING_INIT_FAILED = "ODIN-5001"
    TRACING_EXPORT_FAILED = "ODIN-5002"

    # Execution errors (6xxx)
    TOOL_NOT_FOUND = "ODIN-6001"
    TOOL_EXECUTION_FAILED = "ODIN-6002"
    AGENT_EXECUTION_FAILED = "ODIN-6003"
    TIMEOUT_ERROR = "ODIN-6004"
    VALIDATION_ERROR = "ODIN-6005"

    # Unknown error
    UNKNOWN = "ODIN-9999"

    def __str__(self) -> str:
        """Return the error code value."""
        return self.value
