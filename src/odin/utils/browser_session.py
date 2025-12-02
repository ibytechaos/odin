"""Browser automation utilities using Playwright.

This module provides a high-level browser automation wrapper for
web-based operations like RPA, scraping, and content publishing.

Supports both local browser launch and remote Chrome DevTools Protocol (CDP) connection.

Usage:
    # Simple remote connection
    config = BrowserConfig(host="chrome.example.com", port=443, tls=True)
    async with BrowserSession(config) as session:
        await session.navigate("https://example.com")

    # Or use the global session pool
    session = await get_browser_session(host="chrome.example.com", port=443, tls=True)
    await session.navigate("https://example.com")
"""


import asyncio
import contextlib
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BrowserSessionError(Exception):
    """Base error for browser session operations."""


class BrowserConnectionError(BrowserSessionError):
    """Raised when unable to connect to browser."""


# Backwards compatibility alias
BrowserLoginTimeout = BrowserSessionError


@dataclass
class BrowserConfig:
    """Browser session configuration.

    For remote Chrome connection:
        config = BrowserConfig(host="chrome.example.com", port=443, tls=True)

    For local browser:
        config = BrowserConfig()  # Will launch new browser
    """

    # Remote connection settings (primary use case)
    host: str | None = None
    port: int = 9222
    tls: bool = False

    # Local browser settings
    headless: bool = False
    executable_path: str | None = None

    # Session settings
    timeout: int = 30000  # milliseconds
    download_dir: str | None = None

    @classmethod
    def from_env(cls) -> BrowserConfig:
        """Create config from environment variables.

        Environment variables:
            CHROME_DEBUG_HOST: Remote Chrome host
            CHROME_DEBUG_PORT: Remote Chrome port (default: 9222, or 443 for TLS)
            CHROME_DEBUG_TLS: Use TLS (true/false)
            BROWSER_DOWNLOAD_DIR: Download directory
            BROWSER_HEADLESS: Run headless (true/false)
        """
        host = os.environ.get("CHROME_DEBUG_HOST")
        tls = os.environ.get("CHROME_DEBUG_TLS", "").lower() in ("true", "1", "yes")

        # Default port based on TLS
        default_port = 443 if tls else 9222
        port = int(os.environ.get("CHROME_DEBUG_PORT", default_port))

        return cls(
            host=host,
            port=port,
            tls=tls,
            headless=os.environ.get("BROWSER_HEADLESS", "").lower() in ("true", "1", "yes"),
            download_dir=os.environ.get("BROWSER_DOWNLOAD_DIR"),
        )

    @property
    def is_remote(self) -> bool:
        """Check if this config is for remote connection."""
        return self.host is not None

    @property
    def cdp_url(self) -> str:
        """Build CDP URL for remote connection."""
        if not self.host:
            return "http://localhost:9222"
        scheme = "https" if self.tls else "http"
        return f"{scheme}://{self.host}:{self.port}"


class BrowserSession:
    """High-level browser automation wrapper.

    This class manages Playwright browser lifecycle and provides
    common operations for web automation.

    Example:
        ```python
        config = BrowserConfig(host="chrome.example.com", port=443, tls=True)
        async with BrowserSession(config) as session:
            await session.navigate("https://example.com")
            content = await session.get_content()
        ```
    """

    def __init__(self, config: BrowserConfig | None = None) -> None:
        """Initialize browser session.

        Args:
            config: Browser configuration. Uses defaults if None.
        """
        self.config = config or BrowserConfig()
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._download_dir: str | None = None

    async def start(self) -> None:
        """Initialize Playwright and obtain a ready-to-use page."""
        if self.page:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise BrowserSessionError(
                "Playwright is not installed. Install with: pip install playwright && playwright install"
            ) from e

        logger.info(
            "Initializing browser session (remote=%s, host=%s)",
            self.config.is_remote,
            self.config.host,
        )

        self.playwright = await async_playwright().__aenter__()

        if self.config.is_remote:
            await self._connect_remote()
        else:
            await self._launch_local()

        if not self.page:
            raise BrowserSessionError("Failed to initialize browser page")

    async def close(self) -> None:
        """Cleanup browser resources."""
        if self.page:
            with contextlib.suppress(Exception):
                await self.page.close()
            self.page = None

        if self.context:
            with contextlib.suppress(Exception):
                await self.context.close()
            self.context = None

        if self.browser:
            with contextlib.suppress(Exception):
                await self.browser.close()
            self.browser = None

        if self.playwright:
            with contextlib.suppress(Exception):
                await self.playwright.__aexit__(None, None, None)
            self.playwright = None

    async def __aenter__(self) -> BrowserSession:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    # -------------------------------------------------------------------------
    # Browser initialization
    # -------------------------------------------------------------------------

    async def _launch_local(self) -> None:
        """Launch a new local browser instance."""
        launch_options: dict[str, Any] = {
            "headless": self.config.headless,
        }
        if self.config.executable_path:
            launch_options["executable_path"] = self.config.executable_path

        self.browser = await self.playwright.chromium.launch(**launch_options)
        self.context = await self.browser.new_context(
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        self.page = await self.context.new_page()
        logger.info("Launched new local browser instance")

    async def _connect_remote(self) -> None:
        """Connect to a remote browser via CDP."""
        cdp_url = self.config.cdp_url

        try:
            logger.info("Connecting to remote browser at %s", cdp_url)

            # Get WebSocket endpoint
            ws_url = await self._get_ws_endpoint(cdp_url)
            logger.debug("WebSocket endpoint: %s", ws_url)

            # Connect via CDP
            self.browser = await self.playwright.chromium.connect_over_cdp(ws_url)

            # Get existing context or create new one
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                pages = self.context.pages
                if pages:
                    self.page = pages[0]
                else:
                    self.page = await self.context.new_page()
            else:
                self.context = await self.browser.new_context(accept_downloads=True)
                self.page = await self.context.new_page()

            logger.info("Connected to remote browser")

        except Exception as e:
            error_msg = str(e)
            raise BrowserConnectionError(
                f"Failed to connect to browser at {cdp_url}. "
                f"Make sure Chrome is running with remote debugging enabled. "
                f"Error: {error_msg}"
            ) from e

    async def _get_ws_endpoint(self, cdp_url: str) -> str:
        """Get WebSocket endpoint from CDP URL."""
        import aiohttp

        # Use the same TLS setting for the HTTP request
        ssl_context = None
        if self.config.tls:
            import ssl
            ssl_context = ssl.create_default_context()

        connector = aiohttp.TCPConnector(ssl=ssl_context)

        try:
            async with (
                aiohttp.ClientSession(connector=connector) as http_session,
                http_session.get(
                    f"{cdp_url}/json/version",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response,
            ):
                data = await response.json()
                ws_url = data.get("webSocketDebuggerUrl", "")

                # If TLS, ensure WebSocket URL uses wss://
                if self.config.tls and ws_url.startswith("ws://"):
                    ws_url = "wss://" + ws_url[5:]

                return ws_url
        except Exception as e:
            raise BrowserConnectionError(
                f"Failed to get WebSocket endpoint from {cdp_url}/json/version: {e}"
            ) from e

    # -------------------------------------------------------------------------
    # Page operations
    # -------------------------------------------------------------------------

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigate to a URL."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        await self.page.goto(url, wait_until=wait_until, timeout=self.config.timeout)

    async def get_content(self) -> str:
        """Get page HTML content."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        return await self.page.content()

    async def get_text(self, selector: str) -> str:
        """Get text content of an element."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        element = await self.page.wait_for_selector(selector, timeout=self.config.timeout)
        return await element.text_content() if element else ""

    async def click(self, selector: str) -> None:
        """Click an element."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        await self.page.click(selector)

    async def fill(self, selector: str, value: str) -> None:
        """Fill an input field."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        await self.page.fill(selector, value)

    async def screenshot(self, path: str | None = None, full_page: bool = False) -> bytes:
        """Take a screenshot."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        return await self.page.screenshot(path=path, full_page=full_page)

    async def wait_for_selector(self, selector: str, timeout: int | None = None, state: str = "visible") -> Any:
        """Wait for an element to appear."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        return await self.page.wait_for_selector(
            selector, timeout=timeout or self.config.timeout, state=state
        )

    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript in page context."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        return await self.page.evaluate(expression)

    async def set_files(self, selector: str, files: list[str]) -> None:
        """Set files for a file input."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        await self.page.set_input_files(selector, files)

    async def query_selector(self, selector: str) -> Any:
        """Query a single element."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        return await self.page.query_selector(selector)

    async def query_selector_all(self, selector: str) -> list[Any]:
        """Query all matching elements."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        return await self.page.query_selector_all(selector)

    @property
    def url(self) -> str:
        """Get current page URL."""
        if not self.page:
            return ""
        return self.page.url

    @property
    def download_dir(self) -> str:
        """Get download directory, creating if needed."""
        if self._download_dir is None:
            self._download_dir = self.config.download_dir or tempfile.mkdtemp(prefix="odin_browser_")
            Path(self._download_dir).mkdir(parents=True, exist_ok=True)
        return self._download_dir


# -------------------------------------------------------------------------
# Session pool for managing browser instances
# -------------------------------------------------------------------------

_session_pool: dict[str, BrowserSession] = {}
_session_lock = asyncio.Lock()


def _get_session_key(host: str | None, port: int, tls: bool) -> str:
    """Generate a unique key for session pooling."""
    if host:
        return f"{'https' if tls else 'http'}://{host}:{port}"
    return "__local__"


async def get_browser_session(
    host: str | None = None,
    port: int | None = None,
    tls: bool = False,
    config: BrowserConfig | None = None,
) -> BrowserSession:
    """Get or create a browser session.

    Args:
        host: Remote Chrome host (e.g., "chrome.example.com")
        port: Remote Chrome port (default: 443 for TLS, 9222 otherwise)
        tls: Use TLS/HTTPS
        config: Full BrowserConfig (overrides host/port/tls if provided)

    Returns:
        Browser session instance
    """
    if config is None:
        # Try environment variables if no host specified
        if host is None:
            config = BrowserConfig.from_env()
        else:
            if port is None:
                port = 443 if tls else 9222
            config = BrowserConfig(host=host, port=port, tls=tls)

    key = _get_session_key(config.host, config.port, config.tls)

    async with _session_lock:
        session = _session_pool.get(key)
        if session is None or session.page is None:
            session = BrowserSession(config)
            await session.start()
            _session_pool[key] = session
        return session


async def cleanup_browser_session(
    host: str | None = None,
    port: int | None = None,
    tls: bool = False,
    config: BrowserConfig | None = None,
) -> None:
    """Cleanup a specific browser session."""
    if config:
        key = _get_session_key(config.host, config.port, config.tls)
    else:
        if port is None:
            port = 443 if tls else 9222
        key = _get_session_key(host, port, tls)

    async with _session_lock:
        session = _session_pool.pop(key, None)
        if session:
            try:
                await session.close()
                logger.info("Cleaned up browser session: %s", key)
            except Exception as e:
                logger.error("Error closing browser session: %s", e)


async def cleanup_all_browser_sessions() -> None:
    """Cleanup all browser sessions."""
    async with _session_lock:
        for key in list(_session_pool.keys()):
            session = _session_pool.pop(key, None)
            if session:
                try:
                    await session.close()
                    logger.info("Cleaned up browser session: %s", key)
                except Exception as e:
                    logger.error("Error closing browser session: %s", e)


async def run_with_browser[T](
    fn: Callable[[BrowserSession], Awaitable[T]],
    host: str | None = None,
    port: int | None = None,
    tls: bool = False,
    config: BrowserConfig | None = None,
) -> T:
    """Run an operation with a browser session.

    This function handles session pooling and error recovery.
    """
    session = await get_browser_session(host=host, port=port, tls=tls, config=config)

    try:
        return await fn(session)
    except Exception as e:
        logger.warning("Browser operation failed, cleaning up session: %s", e)
        if config:
            await cleanup_browser_session(config=config)
        else:
            await cleanup_browser_session(host=host, port=port, tls=tls)
        raise
