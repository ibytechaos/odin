"""Odin - A modern agent development framework."""

from odin.core.odin import Odin
from odin.config import Settings, get_settings
from odin.plugins import AgentPlugin, PluginConfig, Tool, ToolParameter

__version__ = "0.1.0"

__all__ = [
    "Odin",
    "AgentPlugin",
    "PluginConfig",
    "Tool",
    "ToolParameter",
    "Settings",
    "get_settings",
]
