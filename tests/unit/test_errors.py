"""Tests for the error handling system."""

import pytest

from odin.errors import (
    OdinError,
    ConfigurationError,
    PluginError,
    ExecutionError,
    ErrorCode,
)


class TestOdinErrors:
    """Test error classes and error codes."""

    def test_odin_error_basic(self):
        """Test basic OdinError creation."""
        error = OdinError("Test error")
        assert str(error) == "[ODIN-9999] Test error"  # UNKNOWN is default

    def test_odin_error_with_code(self):
        """Test OdinError with error code."""
        error = OdinError("Plugin failed", code=ErrorCode.PLUGIN_LOAD_FAILED)
        assert "[ODIN-2002]" in str(error)
        assert "Plugin failed" in str(error)

    def test_odin_error_with_details(self):
        """Test OdinError with details."""
        error = OdinError(
            "Tool not found",
            code=ErrorCode.TOOL_NOT_FOUND,
            details={"tool": "my_tool", "plugin": "my_plugin"},
        )
        error_str = str(error)
        assert "my_tool" in error_str
        assert "my_plugin" in error_str

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Invalid config")
        assert isinstance(error, OdinError)
        assert "Invalid config" in str(error)

    def test_plugin_error(self):
        """Test PluginError."""
        error = PluginError(
            "Plugin initialization failed",
            code=ErrorCode.PLUGIN_INIT_FAILED,
            details={"plugin": "weather"},
        )
        assert isinstance(error, OdinError)
        assert "[ODIN-2003]" in str(error)  # PLUGIN_INIT_FAILED = 2003

    def test_execution_error(self):
        """Test ExecutionError."""
        error = ExecutionError(
            "Tool execution failed",
            code=ErrorCode.TOOL_EXECUTION_FAILED,
            details={"tool": "get_weather", "error": "API timeout"},
        )
        assert isinstance(error, OdinError)
        assert "[ODIN-6002]" in str(error)  # TOOL_EXECUTION_FAILED = 6002

    def test_error_code_values(self):
        """Test that error codes have unique values."""
        codes = [
            ErrorCode.UNKNOWN,
            ErrorCode.CONFIG_MISSING,
            ErrorCode.CONFIG_INVALID,
            ErrorCode.PLUGIN_NOT_FOUND,
            ErrorCode.PLUGIN_INIT_FAILED,
            ErrorCode.PLUGIN_LOAD_FAILED,
            ErrorCode.TOOL_NOT_FOUND,
            ErrorCode.TOOL_EXECUTION_FAILED,
        ]

        values = [c.value for c in codes]
        assert len(values) == len(set(values)), "Error codes should be unique"
