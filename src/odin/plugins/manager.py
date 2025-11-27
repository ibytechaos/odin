"""Plugin manager for loading, registering, and managing plugins."""

import importlib
import importlib.util
import sys
import time
from pathlib import Path
from typing import Any

from odin.errors import ErrorCode, ExecutionError, PluginError
from odin.logging import get_logger
from odin.plugins.base import AgentPlugin, DecoratorPlugin, Tool
from odin.tracing import get_metrics_collector, traced

logger = get_logger(__name__)
metrics = get_metrics_collector()


class PluginManager:
    """Manages plugin lifecycle and tool execution."""

    def __init__(self) -> None:
        """Initialize plugin manager."""
        self._plugins: dict[str, AgentPlugin] = {}
        self._tools: dict[str, tuple[str, Tool]] = {}  # tool_name -> (plugin_name, Tool)

    async def register_plugin(self, plugin: AgentPlugin) -> None:
        """Register a plugin instance.

        Args:
            plugin: Plugin to register

        Raises:
            PluginError: If plugin already registered or initialization fails
        """
        if plugin.name in self._plugins:
            raise PluginError(
                f"Plugin '{plugin.name}' is already registered",
                code=ErrorCode.PLUGIN_ALREADY_REGISTERED,
                details={"plugin": plugin.name},
            )

        logger.info(
            "Registering plugin",
            plugin=plugin.name,
            version=plugin.version,
        )

        # Check dependencies
        for dep in plugin.dependencies:
            if dep not in self._plugins:
                raise PluginError(
                    f"Plugin '{plugin.name}' requires '{dep}' which is not loaded",
                    code=ErrorCode.PLUGIN_DEPENDENCY_MISSING,
                    details={"plugin": plugin.name, "missing_dependency": dep},
                )

        # Initialize plugin
        try:
            if not plugin.is_initialized():
                await plugin.initialize()
        except Exception as e:
            raise PluginError(
                f"Failed to initialize plugin '{plugin.name}': {e}",
                code=ErrorCode.PLUGIN_INIT_FAILED,
                details={"plugin": plugin.name, "error": str(e)},
            ) from e

        # Register plugin
        self._plugins[plugin.name] = plugin

        # Register tools
        try:
            tools = await plugin.get_tools()
            for tool in tools:
                if tool.name in self._tools:
                    logger.warning(
                        "Tool name conflict, overwriting",
                        tool=tool.name,
                        old_plugin=self._tools[tool.name][0],
                        new_plugin=plugin.name,
                    )
                self._tools[tool.name] = (plugin.name, tool)
        except Exception as e:
            # Unregister plugin if tool registration fails
            del self._plugins[plugin.name]
            raise PluginError(
                f"Failed to get tools from plugin '{plugin.name}': {e}",
                code=ErrorCode.PLUGIN_LOAD_FAILED,
                details={"plugin": plugin.name, "error": str(e)},
            ) from e

        # Record metrics
        metrics.record_plugin_loaded(plugin.name, loaded=True)

        logger.info(
            "Plugin registered successfully",
            plugin=plugin.name,
            tools=[t.name for t in tools],
        )

    async def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin.

        Args:
            plugin_name: Name of plugin to unregister

        Raises:
            PluginError: If plugin not found
        """
        if plugin_name not in self._plugins:
            raise PluginError(
                f"Plugin '{plugin_name}' is not registered",
                code=ErrorCode.PLUGIN_NOT_FOUND,
                details={"plugin": plugin_name},
            )

        logger.info("Unregistering plugin", plugin=plugin_name)

        plugin = self._plugins[plugin_name]

        # Remove tools
        tools_to_remove = [
            tool_name
            for tool_name, (pname, _) in self._tools.items()
            if pname == plugin_name
        ]
        for tool_name in tools_to_remove:
            del self._tools[tool_name]

        # Shutdown plugin
        try:
            await plugin.shutdown()
        except Exception as e:
            logger.warning(
                "Error during plugin shutdown",
                plugin=plugin_name,
                error=str(e),
            )

        # Remove plugin
        del self._plugins[plugin_name]

        # Record metrics
        metrics.record_plugin_loaded(plugin_name, loaded=False)

        logger.info("Plugin unregistered", plugin=plugin_name)

    def get_plugin(self, plugin_name: str) -> AgentPlugin:
        """Get a registered plugin.

        Args:
            plugin_name: Name of plugin to get

        Returns:
            Plugin instance

        Raises:
            PluginError: If plugin not found
        """
        if plugin_name not in self._plugins:
            raise PluginError(
                f"Plugin '{plugin_name}' is not registered",
                code=ErrorCode.PLUGIN_NOT_FOUND,
                details={"plugin": plugin_name},
            )
        return self._plugins[plugin_name]

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all registered plugins.

        Returns:
            List of plugin information dictionaries
        """
        return [
            {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "initialized": plugin.is_initialized(),
                "tools": len([t for t, (pn, _) in self._tools.items() if pn == plugin.name]),
            }
            for plugin in self._plugins.values()
        ]

    def get_tool(self, tool_name: str) -> Tool:
        """Get a tool definition.

        Args:
            tool_name: Name of tool

        Returns:
            Tool definition

        Raises:
            ExecutionError: If tool not found
        """
        if tool_name not in self._tools:
            raise ExecutionError(
                f"Tool '{tool_name}' not found",
                code=ErrorCode.TOOL_NOT_FOUND,
                details={"tool": tool_name},
            )
        return self._tools[tool_name][1]

    def list_tools(self) -> list[Tool]:
        """List all available tools.

        Returns:
            List of tool definitions
        """
        return [tool for _, tool in self._tools.values()]

    async def execute_tool(
        self, tool_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Execute a tool.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters

        Returns:
            Tool execution result

        Raises:
            ExecutionError: If tool execution fails
        """
        if tool_name not in self._tools:
            raise ExecutionError(
                f"Tool '{tool_name}' not found",
                code=ErrorCode.TOOL_NOT_FOUND,
                details={"tool": tool_name},
            )

        plugin_name, tool = self._tools[tool_name]
        plugin = self._plugins[plugin_name]

        logger.info(
            "Executing tool",
            tool=tool_name,
            plugin=plugin_name,
            parameters=kwargs,
        )

        # Record metrics with timing
        start_time = time.time()
        success = False
        error_type = None

        try:
            result = await plugin.execute_tool(tool_name, **kwargs)
            success = True
            logger.info("Tool executed successfully", tool=tool_name)
            return result
        except Exception as e:
            error_type = e.__class__.__name__
            logger.error(
                "Tool execution failed",
                tool=tool_name,
                plugin=plugin_name,
                error=str(e),
            )
            raise ExecutionError(
                f"Tool '{tool_name}' execution failed: {e}",
                code=ErrorCode.TOOL_EXECUTION_FAILED,
                details={
                    "tool": tool_name,
                    "plugin": plugin_name,
                    "error": str(e),
                },
            ) from e
        finally:
            latency = time.time() - start_time
            metrics.record_tool_execution(
                tool_name=tool_name,
                plugin_name=plugin_name,
                success=success,
                latency=latency,
                error_type=error_type,
            )

    async def load_plugin_from_file(self, file_path: Path) -> None:
        """Load a plugin from a Python file.

        Args:
            file_path: Path to plugin file

        Raises:
            PluginError: If plugin loading fails
        """
        if not file_path.exists():
            raise PluginError(
                f"Plugin file not found: {file_path}",
                code=ErrorCode.PLUGIN_NOT_FOUND,
                details={"path": str(file_path)},
            )

        logger.info("Loading plugin from file", path=str(file_path))

        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location(
                f"odin.plugins.dynamic.{file_path.stem}", file_path
            )
            if spec is None or spec.loader is None:
                raise PluginError(
                    f"Failed to load plugin spec from {file_path}",
                    code=ErrorCode.PLUGIN_LOAD_FAILED,
                )

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Find plugin class (excluding base classes)
            plugin_class = None
            base_classes = {AgentPlugin, DecoratorPlugin}
            for name in dir(module):
                obj = getattr(module, name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, AgentPlugin)
                    and obj not in base_classes
                ):
                    plugin_class = obj
                    break

            if plugin_class is None:
                raise PluginError(
                    f"No AgentPlugin subclass found in {file_path}",
                    code=ErrorCode.PLUGIN_LOAD_FAILED,
                    details={"path": str(file_path)},
                )

            # Instantiate and register
            plugin = plugin_class()
            await self.register_plugin(plugin)

        except Exception as e:
            raise PluginError(
                f"Failed to load plugin from {file_path}: {e}",
                code=ErrorCode.PLUGIN_LOAD_FAILED,
                details={"path": str(file_path), "error": str(e)},
            ) from e

    async def discover_plugins(self, plugin_dirs: list[Path]) -> None:
        """Discover and load plugins from directories.

        Args:
            plugin_dirs: List of directories to search for plugins
        """
        logger.info("Discovering plugins", dirs=[str(d) for d in plugin_dirs])

        for plugin_dir in plugin_dirs:
            if not plugin_dir.exists():
                logger.warning("Plugin directory not found", dir=str(plugin_dir))
                continue

            for file_path in plugin_dir.glob("*.py"):
                if file_path.name.startswith("_"):
                    continue

                try:
                    await self.load_plugin_from_file(file_path)
                except Exception as e:
                    logger.error(
                        "Failed to load plugin file",
                        path=str(file_path),
                        error=str(e),
                    )

    async def shutdown_all(self) -> None:
        """Shutdown all registered plugins."""
        logger.info("Shutting down all plugins")

        for plugin_name in list(self._plugins.keys()):
            try:
                await self.unregister_plugin(plugin_name)
            except Exception as e:
                logger.error(
                    "Error unregistering plugin",
                    plugin=plugin_name,
                    error=str(e),
                )
