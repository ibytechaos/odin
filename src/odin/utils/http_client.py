"""HTTP client utilities for built-in plugins.

This module provides async HTTP client functionality with
connection pooling, retry logic, and error handling.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

import aiohttp
from aiohttp import ClientTimeout

logger = logging.getLogger(__name__)


class HTTPClientError(Exception):
    """Base error for HTTP client operations."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class AsyncHTTPClient:
    """Async HTTP client with connection pooling.

    Example:
        ```python
        async with AsyncHTTPClient() as client:
            response = await client.get("https://api.example.com/data")
            data = response["json"]
        ```
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        headers: dict[str, str] | None = None,
    ):
        """Initialize HTTP client.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
            headers: Default headers for all requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.default_headers = headers or {}
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> AsyncHTTPClient:
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if not self.session:
            timeout = ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self.default_headers,
            )

    async def close(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: Any = None,
        retry: bool = True,
    ) -> dict[str, Any]:
        """Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Request headers
            params: Query parameters
            json: JSON body
            data: Form data
            retry: Whether to retry on failure

        Returns:
            Response dictionary with status, headers, text, and json

        Raises:
            HTTPClientError: On request failure
        """
        if not self.session:
            await self.initialize()

        merged_headers = {**self.default_headers, **(headers or {})}
        last_error = None

        attempts = self.max_retries if retry else 1

        for attempt in range(attempts):
            try:
                async with self.session.request(
                    method,
                    url,
                    headers=merged_headers,
                    params=params,
                    json=json,
                    data=data,
                ) as response:
                    text = await response.text()

                    result = {
                        "status": response.status,
                        "headers": dict(response.headers),
                        "text": text,
                        "json": None,
                        "ok": response.ok,
                    }

                    # Try to parse JSON
                    with contextlib.suppress(Exception):
                        result["json"] = await response.json()

                    if response.ok:
                        return result
                    else:
                        last_error = HTTPClientError(
                            f"HTTP {response.status}: {text[:500]}",
                            status_code=response.status,
                        )
                        # Don't retry client errors (4xx)
                        if 400 <= response.status < 500:
                            raise last_error

            except aiohttp.ClientError as e:
                last_error = HTTPClientError(f"Request failed: {e}")
            except TimeoutError:
                last_error = HTTPClientError("Request timed out")

            # Wait before retry
            if attempt < attempts - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        raise last_error or HTTPClientError("Request failed after all retries")

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make a GET request."""
        return await self.request("GET", url, headers=headers, params=params, **kwargs)

    async def post(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: Any = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make a POST request."""
        return await self.request(
            "POST", url, headers=headers, json=json, data=data, **kwargs
        )

    async def put(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make a PUT request."""
        return await self.request("PUT", url, headers=headers, json=json, **kwargs)

    async def delete(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make a DELETE request."""
        return await self.request("DELETE", url, headers=headers, **kwargs)


# Convenience functions for quick requests
async def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
    """Fetch JSON from a URL.

    Args:
        url: Target URL
        headers: Optional headers

    Returns:
        Parsed JSON data
    """
    async with AsyncHTTPClient(headers=headers) as client:
        response = await client.get(url)
        return response.get("json")


async def post_json(
    url: str, data: dict[str, Any], headers: dict[str, str] | None = None
) -> Any:
    """Post JSON to a URL.

    Args:
        url: Target URL
        data: JSON data to post
        headers: Optional headers

    Returns:
        Parsed JSON response
    """
    async with AsyncHTTPClient(headers=headers) as client:
        response = await client.post(url, json=data)
        return response.get("json")
