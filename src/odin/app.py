"""Odin Application - Configuration-driven agent server.

This module provides a declarative way to define and run Odin agents
using a YAML configuration file (app.yaml).

Example usage:
    ```bash
    # With app.yaml in current directory
    odin serve

    # With specific config file
    odin serve --config my-agent.yaml
    ```

Example app.yaml:
    ```yaml
    name: weather-assistant
    description: An AI assistant for weather information

    server:
      port: 8000

    protocols:
      - type: ag-ui
        path: /

    llm:
      provider: openai
      model: gpt-4

    plugins:
      - name: weather
        module: my_plugins.weather
    ```
"""

import asyncio
import importlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from odin.config.app_config import AppConfig, ProtocolType, load_app_config
from odin.core.odin import Odin
from odin.logging import get_logger
from odin.plugins import AgentPlugin

logger = get_logger(__name__)


class OdinApp:
    """Configuration-driven Odin application.

    Loads configuration from app.yaml and automatically sets up:
    - Odin core framework
    - Plugins from configuration
    - Protocol endpoints (AG-UI, A2A, MCP)
    - Observability
    """

    def __init__(self, config: AppConfig | str | Path | None = None):
        """Initialize Odin application.

        Args:
            config: AppConfig instance, path to YAML file, or None to use default
        """
        if config is None:
            config = "app.yaml"

        if isinstance(config, (str, Path)):
            self.config = load_app_config(config)
        else:
            self.config = config

        self.odin: Odin | None = None
        self.fastapi: FastAPI | None = None
        self._adapters: dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize the application."""
        logger.info(
            "Initializing Odin application",
            name=self.config.name,
            version=self.config.version,
        )

        # Create Odin core
        self.odin = Odin()
        await self.odin.initialize()

        # Load plugins
        await self._load_plugins()

        logger.info(
            "Application initialized",
            plugins=len(self.odin.list_plugins()),
            tools=len(self.odin.list_tools()),
        )

    async def _load_plugins(self) -> None:
        """Load plugins from configuration."""
        for plugin_config in self.config.get_enabled_plugins():
            try:
                # Dynamic import
                module_path = plugin_config.module
                module = importlib.import_module(module_path)

                # Look for Plugin class
                plugin_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, AgentPlugin)
                        and attr is not AgentPlugin
                    ):
                        plugin_class = attr
                        break

                if plugin_class is None:
                    logger.warning(
                        "No AgentPlugin found in module",
                        module=module_path,
                    )
                    continue

                # Instantiate and register
                plugin = plugin_class(**plugin_config.config)
                await self.odin.register_plugin(plugin)

                logger.info(
                    "Plugin loaded",
                    name=plugin_config.name,
                    module=module_path,
                )

            except Exception as e:
                logger.error(
                    "Failed to load plugin",
                    name=plugin_config.name,
                    module=plugin_config.module,
                    error=str(e),
                )
                raise

    def create_fastapi(self) -> FastAPI:
        """Create FastAPI application with configured protocols.

        Returns:
            Configured FastAPI application
        """

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan."""
            await self.initialize()
            await self._setup_protocols(app)
            yield
            if self.odin:
                await self.odin.shutdown()

        self.fastapi = FastAPI(
            title=self.config.name,
            description=self.config.description,
            version=self.config.version,
            lifespan=lifespan,
        )

        # CORS
        self.fastapi.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.server.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Health check
        @self.fastapi.get("/health")
        async def health():
            return {
                "status": "healthy",
                "name": self.config.name,
                "version": self.config.version,
            }

        return self.fastapi

    async def _setup_protocols(self, app: FastAPI) -> None:
        """Setup protocol endpoints."""
        for protocol in self.config.get_enabled_protocols():
            try:
                if protocol.type == ProtocolType.AGUI:
                    await self._setup_agui(app, protocol)
                elif protocol.type == ProtocolType.A2A:
                    await self._setup_a2a(app, protocol)
                elif protocol.type == ProtocolType.HTTP:
                    await self._setup_http(app, protocol)
                # MCP requires separate server (stdio)

                logger.info(
                    "Protocol endpoint configured",
                    type=protocol.type,
                    path=protocol.path,
                )

            except Exception as e:
                logger.error(
                    "Failed to setup protocol",
                    type=protocol.type,
                    error=str(e),
                )
                raise

    async def _setup_agui(self, app: FastAPI, protocol) -> None:
        """Setup AG-UI protocol endpoint."""
        try:
            from odin.protocols.copilotkit import CopilotKitAdapter

            adapter = CopilotKitAdapter(self.odin)
            adapter.mount(app, protocol.path)
            self._adapters["agui"] = adapter

        except ImportError:
            # Fall back to basic AG-UI
            from odin.protocols.agui import AGUIServer

            agui = AGUIServer(self.odin, path=protocol.path)
            app.mount(protocol.path, agui.app)
            self._adapters["agui"] = agui

    async def _setup_a2a(self, app: FastAPI, protocol) -> None:
        """Setup A2A protocol endpoint."""
        from odin.protocols.a2a import A2AServer

        a2a = A2AServer(
            self.odin,
            name=self.config.name,
            description=self.config.description,
        )
        # Mount A2A routes under the specified path
        app.mount(protocol.path, a2a.app)
        self._adapters["a2a"] = a2a

    async def _setup_http(self, app: FastAPI, protocol) -> None:
        """Setup HTTP/REST endpoint."""
        # TODO: Implement HTTP/REST adapter
        logger.warning("HTTP protocol not yet implemented")

    async def run(self) -> None:
        """Run the application server."""
        import uvicorn

        if self.fastapi is None:
            self.create_fastapi()

        logger.info(
            "Starting server",
            host=self.config.server.host,
            port=self.config.server.port,
        )

        config = uvicorn.Config(
            self.fastapi,
            host=self.config.server.host,
            port=self.config.server.port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()


def create_app(config_path: str = "app.yaml") -> FastAPI:
    """Create FastAPI application from config file.

    This is the entry point for uvicorn/gunicorn:
    ```bash
    uvicorn odin.app:create_app --factory
    ```

    Args:
        config_path: Path to configuration file

    Returns:
        FastAPI application
    """
    odin_app = OdinApp(config_path)
    return odin_app.create_fastapi()


async def serve(config_path: str = "app.yaml") -> None:
    """Serve the application.

    Args:
        config_path: Path to configuration file
    """
    odin_app = OdinApp(config_path)
    await odin_app.run()


if __name__ == "__main__":
    asyncio.run(serve())
