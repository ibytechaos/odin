"""Built-in HTTP Tools for Odin.

HTTP client tools for making API calls and web requests.
These allow AI agents to interact with external services.
"""

import json
from typing import Any, Literal

from odin.decorators import tool
from odin.plugins import DecoratorPlugin


class HTTPTools(DecoratorPlugin):
    """HTTP client tools for making web requests."""

    @property
    def name(self) -> str:
        return "http"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "HTTP client tools for API calls and web requests"

    @tool()
    async def http_get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make an HTTP GET request.

        Args:
            url: URL to request
            headers: Optional request headers
            params: Optional query parameters
            timeout: Request timeout in seconds

        Returns:
            Response with status, headers, and body
        """
        import httpx

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers, params=params)

            # Try to parse JSON body
            try:
                body = response.json()
            except (json.JSONDecodeError, ValueError):
                body = response.text

            return {
                "status": response.status_code,
                "headers": dict(response.headers),
                "body": body,
                "url": str(response.url),
            }

    @tool()
    async def http_post(
        self,
        url: str,
        body: dict[str, Any] | str | None = None,
        headers: dict[str, str] | None = None,
        content_type: Literal["json", "form", "text"] = "json",
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make an HTTP POST request.

        Args:
            url: URL to request
            body: Request body (dict for JSON/form, string for text)
            headers: Optional request headers
            content_type: Body content type (json, form, text)
            timeout: Request timeout in seconds

        Returns:
            Response with status, headers, and body
        """
        import httpx

        headers = headers or {}

        async with httpx.AsyncClient(timeout=timeout) as client:
            if content_type == "json":
                response = await client.post(url, json=body, headers=headers)
            elif content_type == "form":
                response = await client.post(url, data=body, headers=headers)
            else:
                response = await client.post(url, content=body, headers=headers)

            # Try to parse JSON body
            try:
                response_body = response.json()
            except (json.JSONDecodeError, ValueError):
                response_body = response.text

            return {
                "status": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "url": str(response.url),
            }

    @tool()
    async def http_request(
        self,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        url: str,
        body: dict[str, Any] | str | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make a generic HTTP request.

        Args:
            method: HTTP method
            url: URL to request
            body: Optional request body
            headers: Optional request headers
            params: Optional query parameters
            timeout: Request timeout in seconds

        Returns:
            Response with status, headers, and body
        """
        import httpx

        async with httpx.AsyncClient(timeout=timeout) as client:
            kwargs: dict[str, Any] = {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
            }

            if body is not None and method in ("POST", "PUT", "PATCH"):
                if isinstance(body, dict):
                    kwargs["json"] = body
                else:
                    kwargs["content"] = body

            response = await client.request(**kwargs)

            # Try to parse JSON body
            try:
                response_body = response.json()
            except (json.JSONDecodeError, ValueError):
                response_body = response.text

            return {
                "status": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "url": str(response.url),
            }

    @tool()
    async def fetch_webpage(
        self,
        url: str,
        extract_text: bool = True,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Fetch a webpage and optionally extract text content.

        Args:
            url: URL of the webpage
            extract_text: Whether to extract text (strips HTML tags)
            timeout: Request timeout in seconds

        Returns:
            Webpage content and metadata
        """
        import re

        import httpx

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)

            html = response.text
            text = html

            if extract_text:
                # Remove script and style elements
                text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                # Remove HTML tags
                text = re.sub(r"<[^>]+>", " ", text)
                # Clean up whitespace
                text = re.sub(r"\s+", " ", text).strip()

            # Extract title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else None

            return {
                "url": str(response.url),
                "status": response.status_code,
                "title": title,
                "content": text[:10000] if extract_text else html[:10000],  # Limit size
                "content_type": response.headers.get("content-type", ""),
                "truncated": len(text if extract_text else html) > 10000,
            }
