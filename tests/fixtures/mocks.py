"""Common mocks for testing."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock


class MockPage:
    """Mock Playwright page object."""

    def __init__(self) -> None:
        self.url = "https://example.com"
        self._content = "<html><body>Test</body></html>"
        self._screenshot_data = b"fake_image_data"

    async def goto(self, url: str, **kwargs: Any) -> None:
        self.url = url

    async def content(self) -> str:
        return self._content

    async def screenshot(self, **kwargs: Any) -> bytes:
        return self._screenshot_data

    async def click(self, selector: str) -> None:
        pass

    async def fill(self, selector: str, value: str) -> None:
        pass

    async def wait_for_selector(self, selector: str, **kwargs: Any) -> MagicMock:
        element = MagicMock()
        element.text_content = AsyncMock(return_value="Test text")
        return element

    async def evaluate(self, expression: str) -> Any:
        return None

    async def query_selector(self, selector: str) -> MagicMock | None:
        return MagicMock()

    async def query_selector_all(self, selector: str) -> list[MagicMock]:
        return [MagicMock()]

    async def set_input_files(self, selector: str, files: list[str]) -> None:
        pass

    async def close(self) -> None:
        pass


class MockBrowserSession:
    """Mock BrowserSession for testing."""

    def __init__(self, config: Any = None) -> None:
        self.config = config
        self.page = MockPage()
        self.browser = MagicMock()
        self.context = MagicMock()
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def close(self) -> None:
        self._started = False

    async def __aenter__(self) -> "MockBrowserSession":
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> None:
        self.page.url = url

    async def get_content(self) -> str:
        return await self.page.content()

    async def get_text(self, selector: str) -> str:
        element = await self.page.wait_for_selector(selector)
        return await element.text_content()

    async def click(self, selector: str) -> None:
        await self.page.click(selector)

    async def fill(self, selector: str, value: str) -> None:
        await self.page.fill(selector, value)

    async def screenshot(self, path: str | None = None, full_page: bool = False) -> bytes:
        return await self.page.screenshot(path=path, full_page=full_page)

    async def wait_for_selector(
        self, selector: str, timeout: int | None = None, state: str = "visible"
    ) -> Any:
        return await self.page.wait_for_selector(selector, timeout=timeout, state=state)

    async def evaluate(self, expression: str) -> Any:
        return await self.page.evaluate(expression)

    @property
    def url(self) -> str:
        return self.page.url

    @property
    def download_dir(self) -> str:
        return "/tmp/test_downloads"


def create_mock_browser_session(config: Any = None) -> MockBrowserSession:
    """Create a mock browser session for testing."""
    return MockBrowserSession(config)


class MockHTTPClient:
    """Mock HTTP client for testing."""

    def __init__(
        self,
        timeout: int = 30,
        default_responses: dict[str, Any] | None = None,
    ) -> None:
        self.timeout = timeout
        self._responses: dict[str, Any] = default_responses or {}
        self._closed = False

    def set_response(self, url: str, response: Any) -> None:
        """Set a mock response for a URL."""
        self._responses[url] = response

    async def get(self, url: str, **kwargs: Any) -> Any:
        if url in self._responses:
            return self._responses[url]
        return create_mock_http_response(200, {"data": "mock"})

    async def post(self, url: str, **kwargs: Any) -> Any:
        if url in self._responses:
            return self._responses[url]
        return create_mock_http_response(200, {"success": True})

    async def put(self, url: str, **kwargs: Any) -> Any:
        return create_mock_http_response(200, {"updated": True})

    async def delete(self, url: str, **kwargs: Any) -> Any:
        return create_mock_http_response(200, {"deleted": True})

    async def close(self) -> None:
        self._closed = True

    async def __aenter__(self) -> "MockHTTPClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()


class MockHTTPResponse:
    """Mock HTTP response."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: Any = None,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self._text = text
        self.headers = headers or {}

    def json(self) -> Any:
        return self._json_data

    @property
    def text(self) -> str:
        return self._text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def create_mock_http_response(
    status_code: int = 200,
    json_data: Any = None,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> MockHTTPResponse:
    """Create a mock HTTP response."""
    return MockHTTPResponse(
        status_code=status_code,
        json_data=json_data,
        text=text,
        headers=headers,
    )
