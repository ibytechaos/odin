"""Odin Built-in Tools.

These tools are available by default in all Odin applications.
They provide common utilities that can be composed by AI agents
to build complex workflows.

Tool Categories:
- utilities: Text processing, validation, hashing, math
- datetime: Date and time operations
- http: HTTP client for API calls
"""

from pathlib import Path


def get_builtin_tools_dir() -> Path:
    """Get the directory containing built-in tools."""
    return Path(__file__).parent


__all__ = ["get_builtin_tools_dir"]
