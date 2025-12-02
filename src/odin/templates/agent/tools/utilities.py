"""Utility tools - common atomic operations.

These are "pan-agents" - simple utility tools that don't require LLM
but provide useful atomic operations for your agent.
"""

import hashlib
import json
import re
from typing import Any
from urllib.parse import urlparse

from odin.decorators import tool
from odin.plugins import DecoratorPlugin


class UtilityTools(DecoratorPlugin):
    """Common utility tools for data processing and validation.

    These atomic tools can be composed by the LLM to build
    more complex workflows.
    """

    @property
    def name(self) -> str:
        return "utilities"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Utility tools for data processing"

    # ==================== Text Processing ====================

    @tool()
    def text_length(self, text: str) -> dict:
        """Count characters, words, and lines in text.

        Args:
            text: The text to analyze

        Returns:
            Character, word, and line counts
        """
        return {
            "characters": len(text),
            "words": len(text.split()),
            "lines": len(text.splitlines()),
        }

    @tool()
    def text_case(self, text: str, case: str = "lower") -> dict:
        """Convert text case.

        Args:
            text: The text to convert
            case: Target case (lower, upper, title, capitalize)

        Returns:
            Converted text
        """
        cases = {
            "lower": text.lower(),
            "upper": text.upper(),
            "title": text.title(),
            "capitalize": text.capitalize(),
        }
        result = cases.get(case, text)
        return {"result": result, "case": case}

    @tool()
    def text_replace(self, text: str, find: str, replace: str) -> dict:
        """Replace text occurrences.

        Args:
            text: The source text
            find: Text to find
            replace: Replacement text

        Returns:
            Modified text and replacement count
        """
        count = text.count(find)
        result = text.replace(find, replace)
        return {"result": result, "replacements": count}

    @tool()
    def regex_match(self, text: str, pattern: str) -> dict:
        """Find regex matches in text.

        Args:
            text: The text to search
            pattern: Regular expression pattern

        Returns:
            List of matches
        """
        try:
            matches = re.findall(pattern, text)
            return {"matches": matches, "count": len(matches)}
        except re.error as e:
            return {"error": f"Invalid regex: {e}", "matches": []}

    # ==================== Data Processing ====================

    @tool()
    def json_parse(self, json_string: str) -> dict:
        """Parse a JSON string.

        Args:
            json_string: JSON string to parse

        Returns:
            Parsed JSON data
        """
        try:
            data = json.loads(json_string)
            return {"success": True, "data": data}
        except json.JSONDecodeError as e:
            return {"success": False, "error": str(e)}

    @tool()
    def json_format(self, data: Any, indent: int = 2) -> dict:
        """Format data as pretty JSON.

        Args:
            data: Data to format
            indent: Indentation spaces

        Returns:
            Formatted JSON string
        """
        try:
            formatted = json.dumps(data, indent=indent, ensure_ascii=False)
            return {"result": formatted}
        except (TypeError, ValueError) as e:
            return {"error": str(e)}

    # ==================== Validation ====================

    @tool()
    def validate_email(self, email: str) -> dict:
        """Validate an email address format.

        Args:
            email: Email address to validate

        Returns:
            Validation result
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        is_valid = bool(re.match(pattern, email))
        return {"email": email, "valid": is_valid}

    @tool()
    def validate_url(self, url: str) -> dict:
        """Validate and parse a URL.

        Args:
            url: URL to validate

        Returns:
            Parsed URL components
        """
        try:
            parsed = urlparse(url)
            is_valid = all([parsed.scheme, parsed.netloc])
            return {
                "url": url,
                "valid": is_valid,
                "scheme": parsed.scheme,
                "host": parsed.netloc,
                "path": parsed.path,
            }
        except Exception as e:
            return {"url": url, "valid": False, "error": str(e)}

    # ==================== Hashing ====================

    @tool()
    def hash_text(self, text: str, algorithm: str = "sha256") -> dict:
        """Generate hash of text.

        Args:
            text: Text to hash
            algorithm: Hash algorithm (md5, sha1, sha256, sha512)

        Returns:
            Hash digest
        """
        algorithms = {
            "md5": hashlib.md5,
            "sha1": hashlib.sha1,
            "sha256": hashlib.sha256,
            "sha512": hashlib.sha512,
        }

        if algorithm not in algorithms:
            return {"error": f"Unknown algorithm: {algorithm}"}

        hasher = algorithms[algorithm](text.encode())
        return {"hash": hasher.hexdigest(), "algorithm": algorithm}

    # ==================== Math ====================

    @tool()
    def calculate(self, expression: str) -> dict:
        """Evaluate a mathematical expression safely.

        Args:
            expression: Math expression (e.g., "2 + 2 * 3")

        Returns:
            Calculation result
        """
        # Only allow safe characters
        allowed = set("0123456789+-*/().% ")
        if not all(c in allowed for c in expression):
            return {"error": "Invalid characters in expression"}

        try:
            # Use eval with restricted builtins
            result = eval(expression, {"__builtins__": {}}, {})
            return {"expression": expression, "result": result}
        except Exception as e:
            return {"error": str(e)}

    @tool()
    def random_number(self, min_val: int = 0, max_val: int = 100) -> dict:
        """Generate a random number.

        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)

        Returns:
            Random number
        """
        import random

        result = random.randint(min_val, max_val)
        return {"result": result, "range": [min_val, max_val]}

    @tool()
    def uuid_generate(self) -> dict:
        """Generate a new UUID.

        Returns:
            New UUID string
        """
        import uuid

        return {"uuid": str(uuid.uuid4())}
