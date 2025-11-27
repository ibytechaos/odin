"""Odin - A modern agent development framework."""

from odin.core.odin import Odin
from odin.config import Settings, get_settings
from odin.plugins import AgentPlugin, DecoratorPlugin, PluginConfig, Tool, ToolParameter
from odin.decorators import tool, measure_latency, count_calls, track_errors

__version__ = "0.1.0"

__all__ = [
    "Odin",
    "AgentPlugin",
    "DecoratorPlugin",
    "PluginConfig",
    "Tool",
    "ToolParameter",
    "Settings",
    "get_settings",
    # Decorators
    "tool",
    "measure_latency",
    "count_calls",
    "track_errors",
]
