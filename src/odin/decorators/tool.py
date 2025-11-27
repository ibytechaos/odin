"""Tool registration decorator."""

import inspect
from typing import Any, Callable, TypeVar, get_type_hints

from odin.plugins.base import Tool, ToolParameter, ToolParameterType

F = TypeVar("F", bound=Callable[..., Any])


def tool(
    name: str | None = None,
    description: str | None = None,
) -> Callable[[F], F]:
    """Decorator to automatically register a function as a tool.

    This decorator:
    1. Automatically extracts function signature as tool parameters
    2. Uses type hints for parameter types
    3. Uses docstring for description
    4. Attaches tool metadata to the function

    Example:
        ```python
        @tool(name="search", description="Search the web")
        async def search_web(query: str, max_results: int = 10) -> dict:
            '''
            Search the web for information.

            Args:
                query: Search query string
                max_results: Maximum number of results to return
            '''
            # implementation
            pass
        ```

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to first line of docstring)

    Returns:
        Decorated function with tool metadata attached
    """

    def decorator(func: F) -> F:
        # Get function metadata
        func_name = name or func.__name__
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)

        # Parse docstring for description and parameter docs
        docstring = inspect.getdoc(func) or ""
        lines = docstring.split("\n")
        func_description = description or (lines[0] if lines else "")

        # Extract parameter descriptions from docstring
        param_docs = _parse_param_docs(docstring)

        # Build tool parameters from function signature
        parameters = []
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Determine parameter type
            param_type = _python_type_to_tool_type(
                type_hints.get(param_name, type(None))
            )

            # Check if required
            is_required = param.default == inspect.Parameter.empty

            # Get default value
            default = None if is_required else param.default

            # Get description from docstring
            param_description = param_docs.get(param_name, f"Parameter {param_name}")

            parameters.append(
                ToolParameter(
                    name=param_name,
                    type=param_type,
                    description=param_description,
                    required=is_required,
                    default=default,
                )
            )

        # Create tool definition
        tool_def = Tool(
            name=func_name,
            description=func_description,
            parameters=parameters,
        )

        # Attach metadata to function
        func._odin_tool = tool_def  # type: ignore
        func._odin_is_tool = True  # type: ignore

        return func

    return decorator


def _parse_param_docs(docstring: str) -> dict[str, str]:
    """Parse parameter descriptions from docstring.

    Supports Google-style and NumPy-style docstrings.

    Args:
        docstring: Function docstring

    Returns:
        Dictionary mapping parameter names to descriptions
    """
    param_docs = {}

    lines = docstring.split("\n")
    in_args_section = False
    current_param = None

    for line in lines:
        stripped = line.strip()

        # Detect Args/Parameters section
        if stripped.lower() in ["args:", "parameters:", "arguments:"]:
            in_args_section = True
            continue

        # Exit args section on next section
        if in_args_section and stripped.endswith(":") and stripped[:-1].lower() in [
            "returns",
            "yields",
            "raises",
            "examples",
            "note",
            "notes",
        ]:
            in_args_section = False
            continue

        if in_args_section:
            # Parse parameter line: "param_name: description" or "param_name (type): description"
            if ":" in stripped:
                parts = stripped.split(":", 1)
                param_name = parts[0].strip()

                # Remove type annotation if present
                if "(" in param_name:
                    param_name = param_name.split("(")[0].strip()

                description = parts[1].strip()
                param_docs[param_name] = description
                current_param = param_name
            elif current_param and stripped:
                # Continuation of previous parameter description
                param_docs[current_param] += " " + stripped

    return param_docs


def _python_type_to_tool_type(python_type: type) -> ToolParameterType:
    """Convert Python type hint to ToolParameterType.

    Args:
        python_type: Python type from type hints

    Returns:
        Corresponding ToolParameterType
    """
    # Handle common types
    if python_type in (str, type(None)):
        return ToolParameterType.STRING
    elif python_type in (int,):
        return ToolParameterType.INTEGER
    elif python_type in (float,):
        return ToolParameterType.NUMBER
    elif python_type in (bool,):
        return ToolParameterType.BOOLEAN
    elif python_type in (list, tuple):
        return ToolParameterType.ARRAY
    elif python_type in (dict,):
        return ToolParameterType.OBJECT

    # Handle typing module types
    origin = getattr(python_type, "__origin__", None)
    if origin is list or origin is tuple:
        return ToolParameterType.ARRAY
    elif origin is dict:
        return ToolParameterType.OBJECT
    elif origin is type(None):
        return ToolParameterType.STRING

    # Default to string
    return ToolParameterType.STRING


def get_tool_from_function(func: Callable[..., Any]) -> Tool | None:
    """Extract tool definition from a decorated function.

    Args:
        func: Function to extract tool from

    Returns:
        Tool definition if function is decorated with @tool, None otherwise
    """
    return getattr(func, "_odin_tool", None)


def is_tool(func: Callable[..., Any]) -> bool:
    """Check if a function is decorated with @tool.

    Args:
        func: Function to check

    Returns:
        True if function is a tool
    """
    return getattr(func, "_odin_is_tool", False)
