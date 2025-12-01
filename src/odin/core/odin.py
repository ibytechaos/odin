"""Main Odin framework class."""

from typing import Any

from odin.config import Settings, get_settings
from odin.logging import get_logger, setup_logging
from odin.plugins import AgentPlugin
from odin.plugins.manager import PluginManager
from odin.tracing import setup_tracing, shutdown_tracing

logger = get_logger(__name__)


class Odin:
    """Main Odin framework class.

    Orchestrates plugin management, configuration, logging, and protocol servers.

    Example:
        ```python
        from odin import Odin
        from odin.plugins.crewai import CrewAIPlugin

        # Initialize framework
        app = Odin()

        # Register plugins
        await app.register_plugin(CrewAIPlugin())

        # Start MCP server
        await app.serve_mcp(port=8001)
        ```
    """

    version = "0.1.0"  # Framework version

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize Odin framework.

        Args:
            settings: Optional custom settings (defaults to environment config)
        """
        # Load settings
        self.settings = settings or get_settings()

        # Setup logging
        setup_logging(
            log_level=self.settings.log_level,
            json_format=self.settings.is_production(),
            enable_colors=self.settings.is_development(),
        )

        logger.info(
            "Initializing Odin framework",
            version="0.1.0",
            env=self.settings.env,
        )

        # Setup tracing if enabled
        if self.settings.otel_enabled:
            exporter_type = "console" if self.settings.is_development() else "otlp"
            setup_tracing(self.settings, exporter_type=exporter_type)

        # Initialize plugin manager
        self._plugin_manager = PluginManager()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize framework and discover plugins."""
        if self._initialized:
            logger.warning("Odin already initialized")
            return

        logger.info("Initializing Odin framework")

        # Load builtin plugins
        if self.settings.builtin_plugins:
            await self._load_builtin_plugins(self.settings.builtin_plugins)

        # Auto-discover plugins if enabled
        if self.settings.plugin_auto_discovery:
            await self._plugin_manager.discover_plugins(self.settings.plugin_dirs)

        self._initialized = True
        logger.info("Odin framework initialized successfully")

    async def _load_builtin_plugins(self, plugin_names: list[str]) -> None:
        """Load specified builtin plugins.

        Args:
            plugin_names: List of builtin plugin names to load
        """
        from odin.plugins.builtin import BUILTIN_PLUGINS

        for name in plugin_names:
            if name not in BUILTIN_PLUGINS:
                logger.warning(f"Unknown builtin plugin: {name}, available: {list(BUILTIN_PLUGINS.keys())}")
                continue

            try:
                plugin_class = BUILTIN_PLUGINS[name]
                plugin = plugin_class()
                await self._plugin_manager.register_plugin(plugin)
                logger.info(f"Loaded builtin plugin: {name}")
            except Exception as e:
                logger.error(f"Failed to load builtin plugin {name}: {e}")

    async def shutdown(self) -> None:
        """Shutdown framework and cleanup resources."""
        logger.info("Shutting down Odin framework")
        await self._plugin_manager.shutdown_all()

        # Shutdown tracing
        if self.settings.otel_enabled:
            shutdown_tracing()

        self._initialized = False
        logger.info("Odin framework shut down successfully")

    async def register_plugin(self, plugin: AgentPlugin) -> None:
        """Register a plugin with the framework.

        Args:
            plugin: Plugin instance to register
        """
        await self._plugin_manager.register_plugin(plugin)

    async def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin.

        Args:
            plugin_name: Name of plugin to unregister
        """
        await self._plugin_manager.unregister_plugin(plugin_name)

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all registered plugins.

        Returns:
            List of plugin information
        """
        return self._plugin_manager.list_plugins()

    def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools from registered plugins.

        Returns:
            List of tool definitions
        """
        tools = self._plugin_manager.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type.value,
                        "description": p.description,
                        "required": p.required,
                    }
                    for p in tool.parameters
                ],
            }
            for tool in tools
        ]

    async def execute_tool(
        self, tool_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Execute a tool.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        return await self._plugin_manager.execute_tool(tool_name, **kwargs)

    @property
    def plugin_manager(self) -> PluginManager:
        """Get the plugin manager instance.

        Returns:
            Plugin manager
        """
        return self._plugin_manager

    def is_initialized(self) -> bool:
        """Check if framework is initialized.

        Returns:
            True if initialized
        """
        return self._initialized
