"""Built-in Utility Tools for Odin.

These are atomic, LLM-independent tools that can be composed
by AI agents to build complex workflows. They don't require
any external API calls.
"""

import hashlib
import json
import math
import random
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from odin.decorators import tool
from odin.plugins import DecoratorPlugin


class UtilityTools(DecoratorPlugin):
    """Collection of utility tools for text, data, and math operations."""

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

    @tool()
    def text_length(self, text: str) -> dict[str, int]:
        """Get the length of text in characters and words.

        Args:
            text: Input text to measure

        Returns:
            Dictionary with character and word counts
        """
        return {
            "characters": len(text),
            "words": len(text.split()),
            "lines": len(text.splitlines()),
        }

    @tool()
    def text_case(
        self,
        text: str,
        case: Literal["upper", "lower", "title", "capitalize", "snake", "camel"],
    ) -> str:
        """Convert text to different cases.

        Args:
            text: Input text to convert
            case: Target case (upper, lower, title, capitalize, snake, camel)

        Returns:
            Converted text
        """
        if case == "upper":
            return text.upper()
        elif case == "lower":
            return text.lower()
        elif case == "title":
            return text.title()
        elif case == "capitalize":
            return text.capitalize()
        elif case == "snake":
            # Convert to snake_case
            s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
            s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
            return s.replace("-", "_").replace(" ", "_").lower()
        elif case == "camel":
            # Convert to camelCase
            words = re.split(r"[-_\s]+", text)
            return words[0].lower() + "".join(w.capitalize() for w in words[1:])
        return text

    @tool()
    def text_replace(
        self, text: str, find: str, replace: str, regex: bool = False
    ) -> str:
        """Replace occurrences in text.

        Args:
            text: Input text
            find: String or regex pattern to find
            replace: Replacement string
            regex: Whether to use regex matching

        Returns:
            Text with replacements applied
        """
        if regex:
            return re.sub(find, replace, text)
        return text.replace(find, replace)

    @tool()
    def text_split(
        self, text: str, delimiter: str = "\n", max_splits: int = -1
    ) -> list[str]:
        """Split text by delimiter.

        Args:
            text: Input text to split
            delimiter: Delimiter to split on
            max_splits: Maximum splits (-1 for unlimited)

        Returns:
            List of split parts
        """
        if max_splits == -1:
            return text.split(delimiter)
        return text.split(delimiter, max_splits)

    @tool()
    def text_join(self, parts: list[str], delimiter: str = "\n") -> str:
        """Join text parts with delimiter.

        Args:
            parts: List of text parts to join
            delimiter: Delimiter to join with

        Returns:
            Joined text
        """
        return delimiter.join(parts)

    @tool()
    def regex_match(self, text: str, pattern: str) -> dict[str, Any]:
        """Match regex pattern against text.

        Args:
            text: Input text to match
            pattern: Regex pattern

        Returns:
            Match results with groups
        """
        matches = list(re.finditer(pattern, text))
        return {
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
        }

    @tool()
    def regex_extract(self, text: str, pattern: str, group: int = 0) -> list[str]:
        """Extract all matches of a pattern from text.

        Args:
            text: Input text
            pattern: Regex pattern (with optional groups)
            group: Group number to extract (0 for full match)

        Returns:
            List of matched strings
        """
        matches = re.findall(pattern, text)
        if matches and isinstance(matches[0], tuple):
            # Pattern has groups, return specified group
            return [m[group] if group < len(m) else m[0] for m in matches]
        return matches

    # ==================== Data Processing ====================

    @tool()
    def json_parse(self, text: str) -> Any:
        """Parse JSON string to object.

        Args:
            text: JSON string to parse

        Returns:
            Parsed JSON object
        """
        return json.loads(text)

    @tool()
    def json_format(self, data: Any, indent: int = 2) -> str:
        """Format data as JSON string.

        Args:
            data: Data to format
            indent: Indentation level

        Returns:
            Formatted JSON string
        """
        return json.dumps(data, indent=indent, ensure_ascii=False, default=str)

    @tool()
    def json_query(self, data: dict | list, path: str) -> Any:
        """Query JSON data using dot notation path.

        Args:
            data: JSON data (dict or list)
            path: Dot notation path (e.g., "users.0.name" or "config.database.host")

        Returns:
            Value at path or None if not found
        """
        parts = path.split(".")
        current = data

        for part in parts:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index] if 0 <= index < len(current) else None
                except ValueError:
                    return None
            else:
                return None

        return current

    # ==================== Validation ====================

    @tool()
    def validate_email(self, email: str) -> dict[str, Any]:
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
            "valid": is_valid,
            "local": parts[0],
            "domain": parts[1] if len(parts) > 1 else "",
        }

    @tool()
    def validate_url(self, url: str) -> dict[str, Any]:
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
            "valid": is_valid,
            "protocol": protocol,
            "url": url,
        }

    @tool()
    def validate_json(self, text: str) -> dict[str, Any]:
        """Validate if string is valid JSON.

        Args:
            text: String to validate

        Returns:
            Validation result
        """
        try:
            json.loads(text)
            return {"valid": True, "error": None}
        except json.JSONDecodeError as e:
            return {"valid": False, "error": str(e)}

    # ==================== Hashing & Encoding ====================

    @tool()
    def hash_text(
        self, text: str, algorithm: Literal["md5", "sha1", "sha256", "sha512"] = "sha256"
    ) -> str:
        """Hash text using specified algorithm.

        Args:
            text: Text to hash
            algorithm: Hash algorithm (md5, sha1, sha256, sha512)

        Returns:
            Hex-encoded hash
        """
        hasher = hashlib.new(algorithm)
        hasher.update(text.encode("utf-8"))
        return hasher.hexdigest()

    @tool()
    def base64_encode(self, text: str) -> str:
        """Encode text to base64.

        Args:
            text: Text to encode

        Returns:
            Base64 encoded string
        """
        import base64

        return base64.b64encode(text.encode("utf-8")).decode("utf-8")

    @tool()
    def base64_decode(self, encoded: str) -> str:
        """Decode base64 string.

        Args:
            encoded: Base64 encoded string

        Returns:
            Decoded text
        """
        import base64

        return base64.b64decode(encoded).decode("utf-8")

    # ==================== Math & Numbers ====================

    @tool()
    def calculate(self, expression: str) -> float:
        """Evaluate a mathematical expression safely.

        Args:
            expression: Math expression (e.g., "2 + 2 * 3", "sqrt(16)")

        Returns:
            Calculated result
        """
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
        return float(eval(expression, {"__builtins__": {}}, safe_dict))

    @tool()
    def random_number(
        self, min_val: float = 0, max_val: float = 1, integer: bool = False
    ) -> float | int:
        """Generate a random number.

        Args:
            min_val: Minimum value
            max_val: Maximum value
            integer: Whether to return integer

        Returns:
            Random number
        """
        if integer:
            return random.randint(int(min_val), int(max_val))
        return random.uniform(min_val, max_val)

    @tool()
    def uuid_generate(self, version: Literal[1, 4] = 4) -> str:
        """Generate a UUID.

        Args:
            version: UUID version (1 or 4)

        Returns:
            Generated UUID string
        """
        if version == 1:
            return str(uuid.uuid1())
        return str(uuid.uuid4())

    # ==================== Date & Time ====================

    @tool()
    def datetime_now(self, timezone_name: str = "UTC") -> dict[str, Any]:
        """Get current date and time.

        Args:
            timezone_name: Timezone name (currently only UTC supported)

        Returns:
            Current datetime information
        """
        now = datetime.now(timezone.utc)
        return {
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
        }

    @tool()
    def datetime_format(self, iso_string: str, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime string.

        Args:
            iso_string: ISO format datetime string
            format: Output format string (strftime format)

        Returns:
            Formatted datetime string
        """
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime(format)

    @tool()
    def datetime_parse(self, date_string: str, format: str = "%Y-%m-%d") -> dict[str, Any]:
        """Parse datetime string to components.

        Args:
            date_string: Date string to parse
            format: Input format string (strftime format)

        Returns:
            Parsed datetime components
        """
        dt = datetime.strptime(date_string, format)
        return {
            "iso": dt.isoformat(),
            "year": dt.year,
            "month": dt.month,
            "day": dt.day,
            "hour": dt.hour,
            "minute": dt.minute,
            "second": dt.second,
        }

    # ==================== List Operations ====================

    @tool()
    def list_sort(
        self, items: list[Any], reverse: bool = False, key: str | None = None
    ) -> list[Any]:
        """Sort a list.

        Args:
            items: List to sort
            reverse: Sort in descending order
            key: Key path for sorting objects (dot notation)

        Returns:
            Sorted list
        """
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

            return sorted(items, key=get_key, reverse=reverse)
        return sorted(items, reverse=reverse)

    @tool()
    def list_filter(
        self, items: list[dict], key: str, value: Any, operator: str = "eq"
    ) -> list[dict]:
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
            if operator == "eq":
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

        return [item for item in items if matches(item)]

    @tool()
    def list_unique(self, items: list[Any]) -> list[Any]:
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
        return result
