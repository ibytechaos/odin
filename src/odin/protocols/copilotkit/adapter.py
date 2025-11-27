"""CopilotKit adapter for Odin framework.

Converts Odin tools to CopilotKit actions and provides FastAPI integration.
"""

from typing import Any

from fastapi import FastAPI

from odin.core.odin import Odin
from odin.logging import get_logger

logger = get_logger(__name__)


class CopilotKitAdapter:
    """Adapter to expose Odin tools as CopilotKit actions.

    This adapter converts Odin's tool definitions to CopilotKit's Action format
    and provides FastAPI endpoint integration.

    Example:
        ```python
        from fastapi import FastAPI
        from odin import Odin
        from odin.protocols.copilotkit import CopilotKitAdapter

        app = FastAPI()
        odin = Odin()
        await odin.initialize()
        await odin.register_plugin(MyPlugin())

        # Create adapter and mount endpoints
        adapter = CopilotKitAdapter(odin)
        adapter.mount(app, "/copilotkit")
        ```
    """

    def __init__(self, odin_app: Odin):
        """Initialize CopilotKit adapter.

        Args:
            odin_app: Odin framework instance
        """
        self.odin_app = odin_app
        self._sdk = None

    def _convert_odin_tool_to_copilotkit_action(self, tool: dict) -> Any:
        """Convert an Odin tool definition to a CopilotKit Action.

        Args:
            tool: Odin tool dictionary

        Returns:
            CopilotKit Action object
        """
        try:
            from copilotkit import Action as CopilotAction
        except ImportError:
            raise ImportError(
                "copilotkit package is required. Install with: pip install copilotkit"
            )

        # Convert parameters to CopilotKit format
        parameters = []
        for param in tool.get("parameters", []):
            param_def = {
                "name": param["name"],
                "type": self._map_type(param.get("type", "string")),
                "description": param.get("description", ""),
                "required": param.get("required", False),
            }
            parameters.append(param_def)

        # Create handler that calls Odin's execute_tool
        tool_name = tool["name"]

        async def handler(**kwargs):
            logger.info(
                "CopilotKit action called",
                tool=tool_name,
                params=list(kwargs.keys()),
            )
            try:
                result = await self.odin_app.execute_tool(tool_name, **kwargs)
                logger.info("CopilotKit action completed", tool=tool_name)
                return result
            except Exception as e:
                logger.error(
                    "CopilotKit action failed",
                    tool=tool_name,
                    error=str(e),
                )
                raise

        action = CopilotAction(
            name=tool["name"],
            description=tool.get("description", ""),
            parameters=parameters,
            handler=handler,
        )

        return action

    def _map_type(self, odin_type: str) -> str:
        """Map Odin type to CopilotKit type.

        Args:
            odin_type: Odin parameter type

        Returns:
            CopilotKit parameter type
        """
        type_mapping = {
            "str": "string",
            "string": "string",
            "int": "number",
            "integer": "number",
            "float": "number",
            "number": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "list": "array",
            "array": "array",
            "dict": "object",
            "object": "object",
        }
        return type_mapping.get(odin_type.lower(), "string")

    def get_actions(self) -> list:
        """Get all Odin tools as CopilotKit actions.

        Returns:
            List of CopilotKit Action objects
        """
        actions = []
        tools = self.odin_app.list_tools()

        for tool in tools:
            try:
                action = self._convert_odin_tool_to_copilotkit_action(tool)
                actions.append(action)
                logger.info(
                    "Converted tool to CopilotKit action",
                    tool=tool["name"],
                )
            except Exception as e:
                logger.error(
                    "Failed to convert tool",
                    tool=tool["name"],
                    error=str(e),
                )

        return actions

    def get_sdk(self):
        """Get CopilotKit SDK instance with all Odin tools.

        Returns:
            CopilotKitSDK instance
        """
        try:
            from copilotkit import CopilotKitSDK
        except ImportError:
            raise ImportError(
                "copilotkit package is required. Install with: pip install copilotkit"
            )

        if self._sdk is None:
            actions = self.get_actions()
            self._sdk = CopilotKitSDK(actions=actions)
            logger.info(
                "CopilotKit SDK created",
                action_count=len(actions),
            )

        return self._sdk

    def mount(self, app: FastAPI, path: str = "/copilotkit"):
        """Mount CopilotKit endpoints on FastAPI app.

        Args:
            app: FastAPI application
            path: Endpoint path (default: "/copilotkit")
        """
        try:
            from copilotkit.integrations.fastapi import add_fastapi_endpoint
        except ImportError:
            raise ImportError(
                "copilotkit package is required. Install with: pip install copilotkit"
            )

        sdk = self.get_sdk()
        add_fastapi_endpoint(app, sdk, path)

        logger.info(
            "CopilotKit endpoint mounted",
            path=path,
            actions=len(self.get_actions()),
        )
