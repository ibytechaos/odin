"""Tests for the @tool decorator."""

import pytest

from odin.decorators import tool
from odin.decorators.tool import get_tool_from_function, is_tool
from odin.plugins.base import ToolParameterType


class TestToolDecorator:
    """Test the @tool decorator functionality."""

    def test_basic_tool_registration(self):
        """Test that @tool decorator registers a function as a tool."""

        @tool(description="A test tool")
        async def my_tool(param: str) -> dict:
            """Tool docstring."""
            return {"result": param}

        assert is_tool(my_tool)
        tool_def = get_tool_from_function(my_tool)
        assert tool_def is not None
        assert tool_def.name == "my_tool"
        assert tool_def.description == "A test tool"

    def test_custom_name(self):
        """Test that custom name overrides function name."""

        @tool(name="custom_name", description="Custom named tool")
        async def original_name(x: int) -> dict:
            return {"x": x}

        tool_def = get_tool_from_function(original_name)
        assert tool_def.name == "custom_name"

    def test_parameter_extraction(self):
        """Test that parameters are extracted from function signature."""

        @tool(description="Test params")
        async def tool_with_params(
            required_str: str,
            optional_int: int = 10,
            optional_bool: bool = False,
        ) -> dict:
            """Tool with parameters.

            Args:
                required_str: A required string parameter
                optional_int: An optional integer
                optional_bool: An optional boolean
            """
            return {}

        tool_def = get_tool_from_function(tool_with_params)
        assert len(tool_def.parameters) == 3

        # Check required_str
        str_param = next(p for p in tool_def.parameters if p.name == "required_str")
        assert str_param.type == ToolParameterType.STRING
        assert str_param.required is True
        assert "required string" in str_param.description

        # Check optional_int
        int_param = next(p for p in tool_def.parameters if p.name == "optional_int")
        assert int_param.type == ToolParameterType.INTEGER
        assert int_param.required is False
        assert int_param.default == 10

        # Check optional_bool
        bool_param = next(p for p in tool_def.parameters if p.name == "optional_bool")
        assert bool_param.type == ToolParameterType.BOOLEAN
        assert bool_param.required is False
        assert bool_param.default is False

    def test_description_from_docstring(self):
        """Test that description comes from docstring if not provided."""

        @tool()
        async def auto_description() -> dict:
            """This is the auto description."""
            return {}

        tool_def = get_tool_from_function(auto_description)
        assert tool_def.description == "This is the auto description."

    def test_type_mapping(self):
        """Test Python type to tool type mapping."""

        @tool(description="Type test")
        async def type_test(
            s: str,
            i: int,
            f: float,
            b: bool,
            lst: list,
            dct: dict,
        ) -> dict:
            """Test various types."""
            return {}

        tool_def = get_tool_from_function(type_test)
        params = {p.name: p for p in tool_def.parameters}

        assert params["s"].type == ToolParameterType.STRING
        assert params["i"].type == ToolParameterType.INTEGER
        assert params["f"].type == ToolParameterType.NUMBER
        assert params["b"].type == ToolParameterType.BOOLEAN
        assert params["lst"].type == ToolParameterType.ARRAY
        assert params["dct"].type == ToolParameterType.OBJECT

    def test_non_tool_function(self):
        """Test that non-decorated functions return None."""

        async def regular_function() -> dict:
            return {}

        assert not is_tool(regular_function)
        assert get_tool_from_function(regular_function) is None

    def test_tool_with_no_params(self):
        """Test tool with no parameters."""

        @tool(description="No params tool")
        async def no_params_tool() -> dict:
            return {"result": "ok"}

        tool_def = get_tool_from_function(no_params_tool)
        assert tool_def is not None
        assert len(tool_def.parameters) == 0

    def test_tool_with_self_param(self):
        """Test that self parameter is excluded."""

        class MyPlugin:
            @tool(description="Method tool")
            async def method_tool(self, param: str) -> dict:
                return {"param": param}

        plugin = MyPlugin()
        tool_def = get_tool_from_function(plugin.method_tool)
        assert tool_def is not None
        # self should be excluded
        param_names = [p.name for p in tool_def.parameters]
        assert "self" not in param_names
        assert "param" in param_names

    def test_tool_preserves_function(self):
        """Test that decorated function is still callable."""

        @tool(description="Callable tool")
        async def callable_tool(x: int) -> dict:
            return {"doubled": x * 2}

        # Should still be callable
        import asyncio
        result = asyncio.run(callable_tool(5))
        assert result == {"doubled": 10}

    def test_tool_with_none_type(self):
        """Test tool parameter with None type hint."""

        @tool(description="Test tool")
        async def tool_with_none(param) -> dict:
            """Tool without type hint."""
            return {"param": param}

        tool_def = get_tool_from_function(tool_with_none)
        assert tool_def is not None
        # Parameter without type hint should default to string
        param = next(p for p in tool_def.parameters if p.name == "param")
        assert param.type == ToolParameterType.STRING

    def test_tool_with_optional_type(self):
        """Test tool with Optional type hint."""
        from typing import Optional

        @tool(description="Optional test")
        async def optional_tool(param: Optional[str] = None) -> dict:
            """Tool with optional param."""
            return {"param": param}

        tool_def = get_tool_from_function(optional_tool)
        assert tool_def is not None
        param = next(p for p in tool_def.parameters if p.name == "param")
        assert param.required is False

    def test_tool_with_any_type(self):
        """Test tool with Any type hint."""
        from typing import Any

        @tool(description="Any type test")
        async def any_tool(param: Any) -> dict:
            """Tool with any type."""
            return {"param": param}

        tool_def = get_tool_from_function(any_tool)
        assert tool_def is not None


class TestToolToFormats:
    """Test Tool format conversion methods."""

    def test_to_openai_format(self):
        """Test conversion to OpenAI format."""

        @tool(description="OpenAI format test")
        async def openai_test(name: str, count: int = 1) -> dict:
            """Test tool for OpenAI format.

            Args:
                name: The name parameter
                count: Number of times
            """
            return {}

        tool_def = get_tool_from_function(openai_test)
        openai_format = tool_def.to_openai_format()

        assert openai_format["type"] == "function"
        assert openai_format["function"]["name"] == "openai_test"
        assert openai_format["function"]["description"] == "OpenAI format test"

        params = openai_format["function"]["parameters"]
        assert params["type"] == "object"
        assert "name" in params["properties"]
        assert "count" in params["properties"]
        assert "name" in params["required"]

    def test_to_mcp_format(self):
        """Test conversion to MCP format."""

        @tool(description="MCP format test")
        async def mcp_test(query: str) -> dict:
            """Test tool for MCP format.

            Args:
                query: The search query
            """
            return {}

        tool_def = get_tool_from_function(mcp_test)
        mcp_format = tool_def.to_mcp_format()

        assert mcp_format["name"] == "mcp_test"
        assert mcp_format["description"] == "MCP format test"
        assert "inputSchema" in mcp_format
        assert mcp_format["inputSchema"]["type"] == "object"


class TestToolAnnotatedParams:
    """Test tool with Annotated parameters (Pydantic Field)."""

    def test_annotated_param_with_field(self):
        """Test parameter with Annotated and Field."""
        from typing import Annotated
        from pydantic import Field

        @tool(description="Annotated test")
        async def annotated_tool(
            name: Annotated[str, Field(description="The user name")]
        ) -> dict:
            return {"name": name}

        tool_def = get_tool_from_function(annotated_tool)
        param = next(p for p in tool_def.parameters if p.name == "name")
        assert "user name" in param.description.lower()

    def test_annotated_param_with_default(self):
        """Test Annotated parameter with default value."""
        from typing import Annotated
        from pydantic import Field

        @tool(description="Default test")
        async def default_tool(
            count: Annotated[int, Field(description="Count", default=5)]
        ) -> dict:
            return {"count": count}

        tool_def = get_tool_from_function(default_tool)
        param = next(p for p in tool_def.parameters if p.name == "count")
        # Field default should be captured
        assert param.required is False or param.default == 5
