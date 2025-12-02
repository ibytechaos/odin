"""Odin plugin system."""

from odin.plugins.base import (
    AgentPlugin,
    DecoratorPlugin,
    PluginConfig,
    Tool,
    ToolParameter,
)

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
from odin.plugins.manager import PluginManager

__all__ = [
    # Plugin utilities
    "BUILTIN_PLUGINS",
    # Base classes
    "AgentPlugin",
    "ContentPlugin",
    "DecoratorPlugin",
    "GeminiPlugin",
    # Built-in plugins
    "GitHubPlugin",
    "GooglePlugin",
    "PluginConfig",
    "PluginManager",
    "PublishersPlugin",
    "Tool",
    "ToolParameter",
    "TrendingPlugin",
    "XiaohongshuPlugin",
    "get_all_builtin_plugins",
    "get_builtin_plugin",
]
