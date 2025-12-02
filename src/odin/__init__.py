"""Odin - A modern agent development framework."""

from odin.config import Settings, get_settings
from odin.core.odin import Odin
from odin.decorators import count_calls, measure_latency, tool, track_errors
from odin.plugins import AgentPlugin, DecoratorPlugin, PluginConfig, Tool, ToolParameter

__version__ = "0.1.0"

__all__ = [
    "AgentPlugin",
    "DecoratorPlugin",
    "Odin",
    "PluginConfig",
    "Settings",
    "Tool",
    "ToolParameter",
    "count_calls",
    "get_settings",
    "measure_latency",
    # Decorators
    "tool",
    "track_errors",
]
