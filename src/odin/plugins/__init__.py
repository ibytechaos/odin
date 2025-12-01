"""Odin plugin system."""

from odin.plugins.base import (
    AgentPlugin,
    DecoratorPlugin,
    PluginConfig,
    Tool,
    ToolParameter,
)
from odin.plugins.manager import PluginManager

# Built-in plugins
from odin.plugins.builtin import (
    BUILTIN_PLUGINS,
    ContentPlugin,
    GeminiPlugin,
    GitHubPlugin,
    GooglePlugin,
    PublishersPlugin,
    TrendingPlugin,
    XiaohongshuPlugin,
    get_all_builtin_plugins,
    get_builtin_plugin,
)

__all__ = [
    # Base classes
    "AgentPlugin",
    "DecoratorPlugin",
    "PluginConfig",
    "Tool",
    "ToolParameter",
    "PluginManager",
    # Built-in plugins
    "GitHubPlugin",
    "XiaohongshuPlugin",
    "GeminiPlugin",
    "GooglePlugin",
    "TrendingPlugin",
    "ContentPlugin",
    "PublishersPlugin",
    # Plugin utilities
    "BUILTIN_PLUGINS",
    "get_all_builtin_plugins",
    "get_builtin_plugin",
]
