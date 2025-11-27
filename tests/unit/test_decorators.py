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
