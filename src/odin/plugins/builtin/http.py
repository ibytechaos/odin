"""HTTP Tools plugin for Odin.

This plugin provides HTTP client tools for making API calls
and web requests. Allows AI agents to interact with external services.

Tools:
- http_get: Make HTTP GET request
- http_post: Make HTTP POST request
- http_request: Make generic HTTP request
- fetch_webpage: Fetch and extract webpage content
"""


import json
import re
from typing import Annotated, Any, Literal

from pydantic import Field

from odin.decorators import tool
from odin.plugins import DecoratorPlugin, PluginConfig


class HTTPPlugin(DecoratorPlugin):
    """HTTP client tools for making web requests.

    This plugin provides tools for AI agents to make HTTP requests
    and interact with external APIs and web services.
    """

    def __init__(self, config: PluginConfig | None = None) -> None:
        super().__init__(config)

    @property
    def name(self) -> str:
        return "http"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "HTTP client tools for API calls and web requests"

    @tool(description="Make an HTTP GET request")
    async def http_get(
        self,
        url: Annotated[str, Field(description="URL to request")],
        headers: Annotated[
            dict[str, str] | None,
            Field(description="Optional request headers"),
        ] = None,
        params: Annotated[
            dict[str, str] | None,
            Field(description="Optional query parameters"),
        ] = None,
        timeout: Annotated[
            int, Field(description="Request timeout in seconds", ge=1, le=300)
        ] = 30,
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
        try:
            import httpx

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=headers, params=params)

                # Try to parse JSON body
                try:
                    body = response.json()
                except (json.JSONDecodeError, ValueError):
                    body = response.text

                return {
                    "success": True,
                    "data": {
                        "status": response.status_code,
                        "headers": dict(response.headers),
                        "body": body,
                        "url": str(response.url),
                    },
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Make an HTTP POST request")
    async def http_post(
        self,
        url: Annotated[str, Field(description="URL to request")],
        body: Annotated[
            dict[str, Any] | str | None,
            Field(description="Request body (dict for JSON/form, string for text)"),
        ] = None,
        headers: Annotated[
            dict[str, str] | None,
            Field(description="Optional request headers"),
        ] = None,
        content_type: Annotated[
            Literal["json", "form", "text"],
            Field(description="Body content type"),
        ] = "json",
        timeout: Annotated[
            int, Field(description="Request timeout in seconds", ge=1, le=300)
        ] = 30,
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
        try:
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
                    "success": True,
                    "data": {
                        "status": response.status_code,
                        "headers": dict(response.headers),
                        "body": response_body,
                        "url": str(response.url),
                    },
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Make a generic HTTP request")
    async def http_request(
        self,
        method: Annotated[
            Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
            Field(description="HTTP method"),
        ],
        url: Annotated[str, Field(description="URL to request")],
        body: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional request body"),
        ] = None,
        headers: Annotated[
            dict[str, str] | None,
            Field(description="Optional request headers"),
        ] = None,
        params: Annotated[
            dict[str, str] | None,
            Field(description="Optional query parameters"),
        ] = None,
        timeout: Annotated[
            int, Field(description="Request timeout in seconds", ge=1, le=300)
        ] = 30,
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
        try:
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
                    "success": True,
                    "data": {
                        "status": response.status_code,
                        "headers": dict(response.headers),
                        "body": response_body,
                        "url": str(response.url),
                    },
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Fetch a webpage and extract text content")
    async def fetch_webpage(
        self,
        url: Annotated[str, Field(description="URL of the webpage")],
        extract_text: Annotated[
            bool, Field(description="Whether to extract text (strips HTML tags)")
        ] = True,
        timeout: Annotated[
            int, Field(description="Request timeout in seconds", ge=1, le=300)
        ] = 30,
    ) -> dict[str, Any]:
        """Fetch a webpage and optionally extract text content.

        Args:
            url: URL of the webpage
            extract_text: Whether to extract text (strips HTML tags)
            timeout: Request timeout in seconds

        Returns:
            Webpage content and metadata
        """
        try:
            import httpx

            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=True
            ) as client:
                response = await client.get(url)

                html = response.text
                text = html

                if extract_text:
                    # Remove script and style elements
                    text = re.sub(
                        r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL
                    )
                    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                    # Remove HTML tags
                    text = re.sub(r"<[^>]+>", " ", text)
                    # Clean up whitespace
                    text = re.sub(r"\s+", " ", text).strip()

                # Extract title
                title_match = re.search(
                    r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE
                )
                title = title_match.group(1).strip() if title_match else None

                content = text if extract_text else html
                truncated = len(content) > 10000

                return {
                    "success": True,
                    "data": {
                        "url": str(response.url),
                        "status": response.status_code,
                        "title": title,
                        "content": content[:10000],  # Limit size
                        "content_type": response.headers.get("content-type", ""),
                        "truncated": truncated,
                    },
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
