"""Odin built-in plugins.

This module contains built-in plugins that provide commonly used tools
for agent development. All plugins follow the Odin plugin architecture
and can be enabled/disabled via configuration.

Available plugins:
- HTTPPlugin: HTTP client tools for API calls and web requests
- UtilitiesPlugin: Utility tools for text, data, and math operations
- NotebookLLMPlugin: Google NotebookLLM automation tools
- GitHubPlugin: GitHub trending repositories discovery and analysis
- XiaohongshuPlugin: Xiaohongshu (小红书) automation and content tools
- GeminiPlugin: Google Gemini deep research automation
- GooglePlugin: Google Custom Search API integration
- TrendingPlugin: Hot topics mining from multiple sources
- ContentPlugin: Content generation and storage (Obsidian, etc.)
- PublishersPlugin: Multi-platform blog publishing automation
- MobilePlugin: Mobile device automation tools (Android, Harmony, iOS)
"""

from odin.plugins.builtin.content import ContentPlugin
from odin.plugins.builtin.gemini import GeminiPlugin
from odin.plugins.builtin.github import GitHubPlugin
from odin.plugins.builtin.google import GooglePlugin
from odin.plugins.builtin.http import HTTPPlugin
from odin.plugins.builtin.mobile import MobilePlugin
from odin.plugins.builtin.notebookllm import NotebookLLMPlugin
from odin.plugins.builtin.publishers import PublishersPlugin
from odin.plugins.builtin.trending import TrendingPlugin
from odin.plugins.builtin.utilities import UtilitiesPlugin
from odin.plugins.builtin.xiaohongshu import XiaohongshuPlugin

__all__ = [
    "ContentPlugin",
    "GeminiPlugin",
    "GitHubPlugin",
    "GooglePlugin",
    "HTTPPlugin",
    "MobilePlugin",
    "NotebookLLMPlugin",
    "PublishersPlugin",
    "TrendingPlugin",
    "UtilitiesPlugin",
    "XiaohongshuPlugin",
]

# Plugin registry for easy loading
BUILTIN_PLUGINS = {
    "http": HTTPPlugin,
    "utilities": UtilitiesPlugin,
    "notebookllm": NotebookLLMPlugin,
    "github": GitHubPlugin,
    "xiaohongshu": XiaohongshuPlugin,
    "gemini": GeminiPlugin,
    "google": GooglePlugin,
    "trending": TrendingPlugin,
    "content": ContentPlugin,
    "publishers": PublishersPlugin,
    "mobile": MobilePlugin,
}


def get_all_builtin_plugins():
    """Get instances of all built-in plugins.

    Returns:
        List of plugin instances
    """
    return [plugin_class() for plugin_class in BUILTIN_PLUGINS.values()]


def get_builtin_plugin(name: str):
    """Get a specific built-in plugin by name.

    Args:
        name: Plugin name (e.g., 'github', 'xiaohongshu')

    Returns:
        Plugin instance or None if not found
    """
    plugin_class = BUILTIN_PLUGINS.get(name)
    if plugin_class:
        return plugin_class()
    return None
