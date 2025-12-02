"""Utility Tools plugin for Odin.

This plugin provides atomic, LLM-independent tools that can be composed
by AI agents to build complex workflows. They don't require
any external API calls.

Tools:
- Text processing: text_length, text_case, text_replace, text_split, text_join
- Regex: regex_match, regex_extract
- JSON: json_parse, json_format, json_query
- Validation: validate_email, validate_url, validate_json
- Hashing: hash_text, base64_encode, base64_decode
- Math: calculate, random_number, uuid_generate
- DateTime: datetime_now, datetime_format, datetime_parse
- List operations: list_sort, list_filter, list_unique
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from odin.decorators import tool
from odin.plugins import DecoratorPlugin, PluginConfig


class UtilitiesPlugin(DecoratorPlugin):
    """Collection of utility tools for text, data, and math operations.

    This plugin provides atomic, composable tools that AI agents
    can use for common data manipulation tasks.
    """

    def __init__(self, config: PluginConfig | None = None) -> None:
        super().__init__(config)

    @property
    def name(self) -> str:
        return "utilities"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Built-in utility tools for text, data, and math operations"

    # ==================== Text Processing ====================

    @tool(description="Get the length of text in characters and words")
    def text_length(
        self,
        text: Annotated[str, Field(description="Input text to measure")],
    ) -> dict[str, Any]:
        """Get the length of text in characters and words.

        Args:
            text: Input text to measure

        Returns:
            Dictionary with character and word counts
        """
        return {
            "success": True,
            "data": {
                "characters": len(text),
                "words": len(text.split()),
                "lines": len(text.splitlines()),
            },
        }

    @tool(description="Convert text to different cases")
    def text_case(
        self,
        text: Annotated[str, Field(description="Input text to convert")],
        case: Annotated[
            Literal["upper", "lower", "title", "capitalize", "snake", "camel"],
            Field(description="Target case"),
        ],
    ) -> dict[str, Any]:
        """Convert text to different cases.

        Args:
            text: Input text to convert
            case: Target case (upper, lower, title, capitalize, snake, camel)

        Returns:
            Converted text
        """
        result = text
        if case == "upper":
            result = text.upper()
        elif case == "lower":
            result = text.lower()
        elif case == "title":
            result = text.title()
        elif case == "capitalize":
            result = text.capitalize()
        elif case == "snake":
            # Convert to snake_case
            s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
            s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
            result = s.replace("-", "_").replace(" ", "_").lower()
        elif case == "camel":
            # Convert to camelCase
            words = re.split(r"[-_\s]+", text)
            result = words[0].lower() + "".join(w.capitalize() for w in words[1:])

        return {"success": True, "data": {"result": result}}

    @tool(description="Replace occurrences in text")
    def text_replace(
        self,
        text: Annotated[str, Field(description="Input text")],
        find: Annotated[str, Field(description="String or regex pattern to find")],
        replace: Annotated[str, Field(description="Replacement string")],
        regex: Annotated[
            bool, Field(description="Whether to use regex matching")
        ] = False,
    ) -> dict[str, Any]:
        """Replace occurrences in text.

        Args:
            text: Input text
            find: String or regex pattern to find
            replace: Replacement string
            regex: Whether to use regex matching

        Returns:
            Text with replacements applied
        """
        try:
            result = re.sub(find, replace, text) if regex else text.replace(find, replace)
            return {"success": True, "data": {"result": result}}
        except re.error as e:
            return {"success": False, "error": f"Invalid regex: {e}"}

    @tool(description="Split text by delimiter")
    def text_split(
        self,
        text: Annotated[str, Field(description="Input text to split")],
        delimiter: Annotated[str, Field(description="Delimiter to split on")] = "\n",
        max_splits: Annotated[
            int, Field(description="Maximum splits (-1 for unlimited)")
        ] = -1,
    ) -> dict[str, Any]:
        """Split text by delimiter.

        Args:
            text: Input text to split
            delimiter: Delimiter to split on
            max_splits: Maximum splits (-1 for unlimited)

        Returns:
            List of split parts
        """
        parts = text.split(delimiter) if max_splits == -1 else text.split(delimiter, max_splits)
        return {"success": True, "data": {"parts": parts, "count": len(parts)}}

    @tool(description="Join text parts with delimiter")
    def text_join(
        self,
        parts: Annotated[list[str], Field(description="List of text parts to join")],
        delimiter: Annotated[str, Field(description="Delimiter to join with")] = "\n",
    ) -> dict[str, Any]:
        """Join text parts with delimiter.

        Args:
            parts: List of text parts to join
            delimiter: Delimiter to join with

        Returns:
            Joined text
        """
        result = delimiter.join(parts)
        return {"success": True, "data": {"result": result}}

    @tool(description="Match regex pattern against text")
    def regex_match(
        self,
        text: Annotated[str, Field(description="Input text to match")],
        pattern: Annotated[str, Field(description="Regex pattern")],
    ) -> dict[str, Any]:
        """Match regex pattern against text.

        Args:
            text: Input text to match
            pattern: Regex pattern

        Returns:
            Match results with groups
        """
        try:
            matches = list(re.finditer(pattern, text))
            return {
                "success": True,
                "data": {
                    "matched": len(matches) > 0,
                    "count": len(matches),
                    "matches": [
                        {
                            "text": m.group(),
                            "start": m.start(),
                            "end": m.end(),
                            "groups": m.groups(),
                        }
                        for m in matches
                    ],
                },
            }
        except re.error as e:
            return {"success": False, "error": f"Invalid regex: {e}"}

    @tool(description="Extract all matches of a pattern from text")
    def regex_extract(
        self,
        text: Annotated[str, Field(description="Input text")],
        pattern: Annotated[
            str, Field(description="Regex pattern (with optional groups)")
        ],
        group: Annotated[
            int, Field(description="Group number to extract (0 for full match)")
        ] = 0,
    ) -> dict[str, Any]:
        """Extract all matches of a pattern from text.

        Args:
            text: Input text
            pattern: Regex pattern (with optional groups)
            group: Group number to extract (0 for full match)

        Returns:
            List of matched strings
        """
        try:
            matches = re.findall(pattern, text)
            if matches and isinstance(matches[0], tuple):
                # Pattern has groups, return specified group
                result = [
                    m[group] if group < len(m) else m[0] for m in matches
                ]
            else:
                result = matches
            return {"success": True, "data": {"matches": result, "count": len(result)}}
        except re.error as e:
            return {"success": False, "error": f"Invalid regex: {e}"}

    # ==================== Data Processing ====================

    @tool(description="Parse JSON string to object")
    def json_parse(
        self,
        text: Annotated[str, Field(description="JSON string to parse")],
    ) -> dict[str, Any]:
        """Parse JSON string to object.

        Args:
            text: JSON string to parse

        Returns:
            Parsed JSON object
        """
        try:
            result = json.loads(text)
            return {"success": True, "data": {"result": result}}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}

    @tool(description="Format data as JSON string")
    def json_format(
        self,
        data: Annotated[Any, Field(description="Data to format")],
        indent: Annotated[int, Field(description="Indentation level")] = 2,
    ) -> dict[str, Any]:
        """Format data as JSON string.

        Args:
            data: Data to format
            indent: Indentation level

        Returns:
            Formatted JSON string
        """
        result = json.dumps(data, indent=indent, ensure_ascii=False, default=str)
        return {"success": True, "data": {"result": result}}

    @tool(description="Query JSON data using dot notation path")
    def json_query(
        self,
        data: Annotated[
            dict | list, Field(description="JSON data (dict or list)")
        ],
        path: Annotated[
            str,
            Field(
                description='Dot notation path (e.g., "users.0.name" or "config.database.host")'
            ),
        ],
    ) -> dict[str, Any]:
        """Query JSON data using dot notation path.

        Args:
            data: JSON data (dict or list)
            path: Dot notation path (e.g., "users.0.name")

        Returns:
            Value at path or None if not found
        """
        parts = path.split(".")
        current = data

        for part in parts:
            if current is None:
                return {"success": True, "data": {"value": None, "found": False}}
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index] if 0 <= index < len(current) else None
                except ValueError:
                    return {"success": True, "data": {"value": None, "found": False}}
            else:
                return {"success": True, "data": {"value": None, "found": False}}

        return {"success": True, "data": {"value": current, "found": current is not None}}

    # ==================== Validation ====================

    @tool(description="Validate email address format")
    def validate_email(
        self,
        email: Annotated[str, Field(description="Email address to validate")],
    ) -> dict[str, Any]:
        """Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            Validation result with details
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        is_valid = bool(re.match(pattern, email))
        parts = email.split("@") if "@" in email else [email, ""]
        return {
            "success": True,
            "data": {
                "valid": is_valid,
                "local": parts[0],
                "domain": parts[1] if len(parts) > 1 else "",
            },
        }

    @tool(description="Validate URL format")
    def validate_url(
        self,
        url: Annotated[str, Field(description="URL to validate")],
    ) -> dict[str, Any]:
        """Validate URL format.

        Args:
            url: URL to validate

        Returns:
            Validation result with parsed components
        """
        pattern = r"^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?(\?[^\s]*)?$"
        is_valid = bool(re.match(pattern, url, re.IGNORECASE))

        # Parse components
        protocol_match = re.match(r"^(https?):\/\/", url)
        protocol = protocol_match.group(1) if protocol_match else "http"

        return {
            "success": True,
            "data": {
                "valid": is_valid,
                "protocol": protocol,
                "url": url,
            },
        }

    @tool(description="Validate if string is valid JSON")
    def validate_json(
        self,
        text: Annotated[str, Field(description="String to validate")],
    ) -> dict[str, Any]:
        """Validate if string is valid JSON.

        Args:
            text: String to validate

        Returns:
            Validation result
        """
        try:
            json.loads(text)
            return {"success": True, "data": {"valid": True, "error": None}}
        except json.JSONDecodeError as e:
            return {"success": True, "data": {"valid": False, "error": str(e)}}

    # ==================== Hashing & Encoding ====================

    @tool(description="Hash text using specified algorithm")
    def hash_text(
        self,
        text: Annotated[str, Field(description="Text to hash")],
        algorithm: Annotated[
            Literal["md5", "sha1", "sha256", "sha512"],
            Field(description="Hash algorithm"),
        ] = "sha256",
    ) -> dict[str, Any]:
        """Hash text using specified algorithm.

        Args:
            text: Text to hash
            algorithm: Hash algorithm (md5, sha1, sha256, sha512)

        Returns:
            Hex-encoded hash
        """
        hasher = hashlib.new(algorithm)
        hasher.update(text.encode("utf-8"))
        return {"success": True, "data": {"hash": hasher.hexdigest()}}

    @tool(description="Encode text to base64")
    def base64_encode(
        self,
        text: Annotated[str, Field(description="Text to encode")],
    ) -> dict[str, Any]:
        """Encode text to base64.

        Args:
            text: Text to encode

        Returns:
            Base64 encoded string
        """
        import base64

        result = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        return {"success": True, "data": {"result": result}}

    @tool(description="Decode base64 string")
    def base64_decode(
        self,
        encoded: Annotated[str, Field(description="Base64 encoded string")],
    ) -> dict[str, Any]:
        """Decode base64 string.

        Args:
            encoded: Base64 encoded string

        Returns:
            Decoded text
        """
        import base64

        try:
            result = base64.b64decode(encoded).decode("utf-8")
            return {"success": True, "data": {"result": result}}
        except Exception as e:
            return {"success": False, "error": f"Decode error: {e}"}

    # ==================== Math & Numbers ====================

    @tool(description="Evaluate a mathematical expression safely")
    def calculate(
        self,
        expression: Annotated[
            str,
            Field(description='Math expression (e.g., "2 + 2 * 3", "sqrt(16)")'),
        ],
    ) -> dict[str, Any]:
        """Evaluate a mathematical expression safely.

        Args:
            expression: Math expression (e.g., "2 + 2 * 3", "sqrt(16)")

        Returns:
            Calculated result
        """
        try:
            # Safe math functions
            safe_dict = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pi": math.pi,
                "e": math.e,
                "floor": math.floor,
                "ceil": math.ceil,
            }
            # Only allow safe operations
            result = float(eval(expression, {"__builtins__": {}}, safe_dict))
            return {"success": True, "data": {"result": result}}
        except Exception as e:
            return {"success": False, "error": f"Calculation error: {e}"}

    @tool(description="Generate a random number")
    def random_number(
        self,
        min_val: Annotated[float, Field(description="Minimum value")] = 0,
        max_val: Annotated[float, Field(description="Maximum value")] = 1,
        integer: Annotated[bool, Field(description="Whether to return integer")] = False,
    ) -> dict[str, Any]:
        """Generate a random number.

        Args:
            min_val: Minimum value
            max_val: Maximum value
            integer: Whether to return integer

        Returns:
            Random number
        """
        if integer:
            result = random.randint(int(min_val), int(max_val))
        else:
            result = random.uniform(min_val, max_val)
        return {"success": True, "data": {"result": result}}

    @tool(description="Generate a UUID")
    def uuid_generate(
        self,
        version: Annotated[
            Literal[1, 4], Field(description="UUID version (1 or 4)")
        ] = 4,
    ) -> dict[str, Any]:
        """Generate a UUID.

        Args:
            version: UUID version (1 or 4)

        Returns:
            Generated UUID string
        """
        result = str(uuid.uuid1()) if version == 1 else str(uuid.uuid4())
        return {"success": True, "data": {"uuid": result}}

    # ==================== Date & Time ====================

    @tool(description="Get current date and time")
    def datetime_now(
        self,
        timezone_name: Annotated[
            str, Field(description="Timezone name (currently only UTC supported)")
        ] = "UTC",
    ) -> dict[str, Any]:
        """Get current date and time.

        Args:
            timezone_name: Timezone name (currently only UTC supported)

        Returns:
            Current datetime information
        """
        now = datetime.now(UTC)
        return {
            "success": True,
            "data": {
                "iso": now.isoformat(),
                "timestamp": now.timestamp(),
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second,
                "weekday": now.strftime("%A"),
                "timezone": "UTC",
            },
        }

    @tool(description="Format datetime string")
    def datetime_format(
        self,
        iso_string: Annotated[str, Field(description="ISO format datetime string")],
        format: Annotated[
            str, Field(description="Output format string (strftime format)")
        ] = "%Y-%m-%d %H:%M:%S",
    ) -> dict[str, Any]:
        """Format datetime string.

        Args:
            iso_string: ISO format datetime string
            format: Output format string (strftime format)

        Returns:
            Formatted datetime string
        """
        try:
            dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            result = dt.strftime(format)
            return {"success": True, "data": {"result": result}}
        except Exception as e:
            return {"success": False, "error": f"Format error: {e}"}

    @tool(description="Parse datetime string to components")
    def datetime_parse(
        self,
        date_string: Annotated[str, Field(description="Date string to parse")],
        format: Annotated[
            str, Field(description="Input format string (strftime format)")
        ] = "%Y-%m-%d",
    ) -> dict[str, Any]:
        """Parse datetime string to components.

        Args:
            date_string: Date string to parse
            format: Input format string (strftime format)

        Returns:
            Parsed datetime components
        """
        try:
            dt = datetime.strptime(date_string, format)
            return {
                "success": True,
                "data": {
                    "iso": dt.isoformat(),
                    "year": dt.year,
                    "month": dt.month,
                    "day": dt.day,
                    "hour": dt.hour,
                    "minute": dt.minute,
                    "second": dt.second,
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Parse error: {e}"}

    # ==================== List Operations ====================

    @tool(description="Sort a list")
    def list_sort(
        self,
        items: Annotated[list[Any], Field(description="List to sort")],
        reverse: Annotated[
            bool, Field(description="Sort in descending order")
        ] = False,
        key: Annotated[
            str | None,
            Field(description="Key path for sorting objects (dot notation)"),
        ] = None,
    ) -> dict[str, Any]:
        """Sort a list.

        Args:
            items: List to sort
            reverse: Sort in descending order
            key: Key path for sorting objects (dot notation)

        Returns:
            Sorted list
        """
        try:
            if key:
                def get_key(item):
                    parts = key.split(".")
                    val = item
                    for part in parts:
                        if isinstance(val, dict):
                            val = val.get(part)
                        else:
                            return None
                    return val

                result = sorted(items, key=get_key, reverse=reverse)
            else:
                result = sorted(items, reverse=reverse)
            return {"success": True, "data": {"result": result}}
        except Exception as e:
            return {"success": False, "error": f"Sort error: {e}"}

    @tool(description="Filter a list of objects")
    def list_filter(
        self,
        items: Annotated[list[dict], Field(description="List of objects to filter")],
        key: Annotated[str, Field(description="Key to filter on (dot notation)")],
        value: Annotated[Any, Field(description="Value to compare")],
        operator: Annotated[
            str,
            Field(
                description="Comparison operator (eq, ne, gt, lt, gte, lte, contains)"
            ),
        ] = "eq",
    ) -> dict[str, Any]:
        """Filter a list of objects.

        Args:
            items: List of objects to filter
            key: Key to filter on (dot notation)
            value: Value to compare
            operator: Comparison operator (eq, ne, gt, lt, gte, lte, contains)

        Returns:
            Filtered list
        """
        def get_val(item):
            parts = key.split(".")
            val = item
            for part in parts:
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    return None
            return val

        def matches(item):
            val = get_val(item)
            if operator == "eq":  # noqa: SIM116
                return val == value
            elif operator == "ne":
                return val != value
            elif operator == "gt":
                return val > value
            elif operator == "lt":
                return val < value
            elif operator == "gte":
                return val >= value
            elif operator == "lte":
                return val <= value
            elif operator == "contains":
                return value in val if val else False
            return False

        result = [item for item in items if matches(item)]
        return {"success": True, "data": {"result": result, "count": len(result)}}

    @tool(description="Remove duplicates from list while preserving order")
    def list_unique(
        self,
        items: Annotated[list[Any], Field(description="List with potential duplicates")],
    ) -> dict[str, Any]:
        """Remove duplicates from list while preserving order.

        Args:
            items: List with potential duplicates

        Returns:
            List with duplicates removed
        """
        seen = set()
        result = []
        for item in items:
            # Convert dicts to frozen representation for comparison
            key = json.dumps(item, sort_keys=True) if isinstance(item, dict) else item
            if key not in seen:
                seen.add(key)
                result.append(item)
        return {
            "success": True,
            "data": {
                "result": result,
                "original_count": len(items),
                "unique_count": len(result),
            },
        }
