"""Base plugin interface for Odin framework."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolParameterType(str, Enum):
    """Tool parameter types."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Tool parameter definition."""

    name: str = Field(..., description="Parameter name")
    type: ToolParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Any | None = Field(None, description="Default value")
    enum: list[Any] | None = Field(None, description="Allowed values")


class Tool(BaseModel):
    """Tool definition."""

    name: str = Field(..., description="Unique tool name")
    description: str = Field(..., description="Tool description")
    parameters: list[ToolParameter] = Field(
        default_factory=list, description="Tool parameters"
    )
    returns: dict[str, Any] | None = Field(None, description="Return value schema")
    examples: list[dict[str, Any]] | None = Field(
        None, description="Usage examples"
    )

    def to_openai_format(self) -> dict[str, Any]:
        """Convert tool to OpenAI function calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type.value,
                "description": param.description,
            }
            if param.enum:
                properties[param.name]["enum"] = param.enum
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_mcp_format(self) -> dict[str, Any]:
        """Convert tool to MCP tool schema format."""
        input_schema = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for param in self.parameters:
            input_schema["properties"][param.name] = {
                "type": param.type.value,
                "description": param.description,
            }
            if param.enum:
                input_schema["properties"][param.name]["enum"] = param.enum
            if param.required:
                input_schema["required"].append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": input_schema,
        }


class PluginConfig(BaseModel):
    """Plugin configuration."""

    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)


class AgentPlugin(ABC):
    """Base class for all Odin plugins.

    Plugins encapsulate agent capabilities and expose them as tools.
    They can be loaded dynamically and provide a uniform interface
    for different agent frameworks (CrewAI, LangGraph, etc.).
    """

    def __init__(self, config: PluginConfig | None = None) -> None:
        """Initialize plugin.

        Args:
            config: Plugin configuration
        """
        self.config = config or PluginConfig()
        self._initialized = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Get plugin name.

        Returns:
            Unique plugin identifier
        """
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Get plugin version.

        Returns:
            Semantic version string (e.g., "1.0.0")
        """
        pass

    @property
    def description(self) -> str:
        """Get plugin description.

        Returns:
            Human-readable description
        """
        return ""

    @property
    def dependencies(self) -> list[str]:
        """Get plugin dependencies.

        Returns:
            List of required plugin names
        """
        return []

    async def initialize(self) -> None:
        """Initialize plugin resources.

        Called once before the plugin is used.
        Override to set up connections, load models, etc.
        """
        self._initialized = True

    async def shutdown(self) -> None:
        """Cleanup plugin resources.

        Called when plugin is being unloaded.
        Override to close connections, release resources, etc.
        """
        self._initialized = False

    @abstractmethod
    async def get_tools(self) -> list[Tool]:
        """Get list of tools provided by this plugin.

        Returns:
            List of tool definitions
        """
        pass

    @abstractmethod
    async def execute_tool(
        self, tool_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Execute a tool provided by this plugin.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters

        Returns:
            Tool execution result

        Raises:
            ExecutionError: If tool execution fails
        """
        pass

    def is_initialized(self) -> bool:
        """Check if plugin is initialized.

        Returns:
            True if initialized
        """
        return self._initialized


class DecoratorPlugin(AgentPlugin):
    """Base class for plugins using @tool decorator.

    This class automatically discovers and manages tools defined with
    the @tool decorator, eliminating boilerplate code.

    Example:
        ```python
        from odin.plugins import DecoratorPlugin
        from odin.decorators import tool

        class MyPlugin(DecoratorPlugin):
            @property
            def name(self) -> str:
                return "my_plugin"

            @property
            def version(self) -> str:
                return "1.0.0"

            @tool(description="Say hello")
            async def say_hello(self, name: str) -> dict:
                return {"message": f"Hello, {name}!"}
        ```
    """

    async def get_tools(self) -> list[Tool]:
        """Auto-discover tools from @tool decorated methods."""
        from odin.decorators.tool import get_tool_from_function, is_tool

        tools = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            attr = getattr(self, attr_name)
            if callable(attr) and is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def:
                    tools.append(tool_def)
        return tools

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a @tool decorated method by name."""
        import asyncio

        from odin.decorators.tool import get_tool_from_function, is_tool

        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            attr = getattr(self, attr_name)
            if callable(attr) and is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def and tool_def.name == tool_name:
                    # Handle both sync and async methods
                    result = attr(**kwargs)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result

        raise ValueError(f"Tool '{tool_name}' not found in plugin '{self.name}'")
