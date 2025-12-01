"""Tool registration decorator with Pydantic support.

Supports two parameter definition styles:
1. Annotated style (recommended): Uses Pydantic Field for validation and metadata
2. Docstring style (legacy): Extracts descriptions from Google-style docstrings

Example (Annotated style):
    ```python
    from typing import Annotated, Literal
    from pydantic import Field

    @tool()
    async def search(
        query: Annotated[str, Field(description="Search query", min_length=1)],
        limit: Annotated[int, Field(default=10, ge=1, le=100, description="Max results")],
        format: Annotated[Literal["json", "xml"], Field(description="Output format")] = "json",
    ) -> dict:
        '''Search for items.'''
        pass
    ```

Example (Docstring style - legacy):
    ```python
    @tool()
    async def search(query: str, limit: int = 10) -> dict:
        '''Search for items.

        Args:
            query: Search query string
            limit: Maximum results to return
        '''
        pass
    ```
"""

import inspect
from typing import Annotated, Any, Callable, TypeVar, get_args, get_origin, get_type_hints

from pydantic import Field
from pydantic.fields import FieldInfo

from odin.plugins.base import Tool, ToolParameter, ToolParameterType

F = TypeVar("F", bound=Callable[..., Any])


def tool(
    name: str | None = None,
    description: str | None = None,
) -> Callable[[F], F]:
    """Decorator to register a function as a tool.

    Automatically extracts parameter information from:
    1. Annotated[T, Field(...)] - Pydantic style (preferred)
    2. Type hints + docstring - Legacy style (fallback)

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

        # Get type hints, handling forward references
        try:
            type_hints = get_type_hints(func, include_extras=True)
        except Exception:
            type_hints = {}

        # Parse docstring for description and parameter docs (fallback)
        docstring = inspect.getdoc(func) or ""
        lines = docstring.split("\n")
        func_description = description or (lines[0] if lines else "")
        param_docs = _parse_param_docs(docstring)

        # Build tool parameters from function signature
        parameters = []
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Get the type hint (may be Annotated)
            hint = type_hints.get(param_name, type(None))

            # Extract info from Annotated[T, Field(...)] if present
            field_info = _extract_field_info(hint)
            base_type = _get_base_type(hint)

            # Determine parameter type
            param_type = _python_type_to_tool_type(base_type)

            # Check if required (no default value)
            has_default = param.default != inspect.Parameter.empty
            field_has_default = field_info is not None and field_info.default is not None

            is_required = not has_default and not field_has_default

            # Get default value (priority: signature > Field)
            if has_default:
                default = param.default
            elif field_info is not None and field_info.default is not None:
                default = field_info.default
            else:
                default = None

            # Get description (priority: Field > docstring)
            if field_info is not None and field_info.description:
                param_description = field_info.description
            else:
                param_description = param_docs.get(param_name, f"Parameter {param_name}")

            # Get enum values from Literal type (check both hint and base_type)
            enum_values = _extract_literal_values(hint) or _extract_literal_values(base_type)

            parameters.append(
                ToolParameter(
                    name=param_name,
                    type=param_type,
                    description=param_description,
                    required=is_required,
                    default=default,
                    enum=enum_values,
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


def _extract_field_info(hint: Any) -> FieldInfo | None:
    """Extract Pydantic FieldInfo from Annotated type.

    Args:
        hint: Type hint (may be Annotated[T, Field(...)])

    Returns:
        FieldInfo if found, None otherwise
    """
    if get_origin(hint) is Annotated:
        args = get_args(hint)
        for arg in args[1:]:  # Skip the first arg (base type)
            if isinstance(arg, FieldInfo):
                return arg
    return None


def _get_base_type(hint: Any) -> type:
    """Get the base type from a type hint.

    Handles Annotated[T, ...], Optional[T], Union[T, None], etc.

    Args:
        hint: Type hint

    Returns:
        Base type
    """
    # Handle Annotated[T, ...]
    if get_origin(hint) is Annotated:
        args = get_args(hint)
        if args:
            return _get_base_type(args[0])

    # Handle Optional[T] / Union[T, None]
    origin = get_origin(hint)
    if origin is not None:
        # For Union types, get the first non-None type
        args = get_args(hint)
        if args:
            for arg in args:
                if arg is not type(None):
                    return arg

    return hint if isinstance(hint, type) else type(hint) if hint is not None else type(None)


def _extract_literal_values(hint: Any) -> list[Any] | None:
    """Extract values from Literal type.

    Args:
        hint: Type hint (may be Literal["a", "b"])

    Returns:
        List of literal values if Literal type, None otherwise
    """
    from typing import Literal

    origin = get_origin(hint)

    # Check if it's a Literal type
    if origin is Literal:
        return list(get_args(hint))

    # Handle Annotated[Literal[...], ...]
    if origin is Annotated:
        args = get_args(hint)
        if args:
            return _extract_literal_values(args[0])

    return None


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


def _python_type_to_tool_type(python_type: Any) -> ToolParameterType:
    """Convert Python type hint to ToolParameterType.

    Args:
        python_type: Python type from type hints

    Returns:
        Corresponding ToolParameterType
    """
    from typing import Literal

    # Handle Literal types as string (enum will be extracted separately)
    if get_origin(python_type) is Literal:
        # Determine type from first literal value
        args = get_args(python_type)
        if args:
            first_val = args[0]
            if isinstance(first_val, str):
                return ToolParameterType.STRING
            elif isinstance(first_val, int):
                return ToolParameterType.INTEGER
            elif isinstance(first_val, float):
                return ToolParameterType.NUMBER
            elif isinstance(first_val, bool):
                return ToolParameterType.BOOLEAN
        return ToolParameterType.STRING

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
    origin = get_origin(python_type)
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
