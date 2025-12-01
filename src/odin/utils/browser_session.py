"""Browser automation utilities using Playwright.

This module provides a high-level browser automation wrapper for
web-based operations like RPA, scraping, and content publishing.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BrowserSessionError(Exception):
    """Base error for browser session operations."""


class BrowserLoginTimeout(BrowserSessionError):
    """Raised when waiting for login times out."""


@dataclass
class BrowserConfig:
    """Browser session configuration."""

    headless: bool = False
    executable_path: str | None = None
    user_agent: str | None = None
    viewport_width: int = 1440
    viewport_height: int = 900
    storage_state_path: Path | None = None
    reuse_existing: bool = False
    debug_host: str | None = None
    debug_port: int | None = None
    debug_scheme: str = "http"
    ignore_cert_errors: bool = False
    timeout: int = 30000  # milliseconds

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrowserConfig":
        """Create config from dictionary."""
        return cls(
            headless=data.get("headless", False),
            executable_path=data.get("executable_path"),
            user_agent=data.get("user_agent"),
            viewport_width=data.get("viewport_width", 1440),
            viewport_height=data.get("viewport_height", 900),
            storage_state_path=Path(data["storage_state_path"])
            if data.get("storage_state_path")
            else None,
            reuse_existing=data.get("reuse_existing", False),
            debug_host=data.get("debug_host"),
            debug_port=data.get("debug_port"),
            debug_scheme=data.get("debug_scheme", "http"),
            ignore_cert_errors=data.get("ignore_cert_errors", False),
            timeout=data.get("timeout", 30000),
        )


class BrowserSession:
    """High-level browser automation wrapper.

    This class manages Playwright browser lifecycle and provides
    common operations for web automation.

    Example:
        ```python
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
        self._background_tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Initialize Playwright and obtain a ready-to-use page."""
        if self.page:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise BrowserSessionError(
                "Playwright is not installed. Install with: pip install playwright && playwright install"
            )

        logger.info(
            "Initializing browser session (headless=%s, reuse_existing=%s)",
            self.config.headless,
            self.config.reuse_existing,
        )

        self.playwright = await async_playwright().__aenter__()

        if self.config.reuse_existing and self.config.debug_port:
            await self._connect_existing_browser()
        else:
            await self._launch_new_browser()

        if not await self._ensure_active_page():
            raise BrowserSessionError("Failed to initialize browser page")

    async def close(self) -> None:
        """Cleanup browser resources."""
        # Cancel background tasks
        for task in list(self._background_tasks):
            if not task.done():
                task.cancel()

        # Save storage state if configured
        if self.context and self.config.storage_state_path:
            try:
                await self._save_storage_state()
            except Exception as exc:
                logger.warning("Failed to save storage state: %s", exc)

        # Close resources in order
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
            self.page = None

        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None

        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None

        if self.playwright:
            try:
                await self.playwright.__aexit__(None, None, None)
            except Exception:
                pass
            self.playwright = None

    async def __aenter__(self) -> "BrowserSession":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    # -------------------------------------------------------------------------
    # Browser initialization
    # -------------------------------------------------------------------------

    async def _launch_new_browser(self) -> None:
        """Launch a new browser instance."""
        launch_options: dict[str, Any] = {
            "headless": self.config.headless,
        }
        if self.config.executable_path:
            launch_options["executable_path"] = self.config.executable_path

        self.browser = await self.playwright.chromium.launch(**launch_options)

        # Context options
        context_kwargs: dict[str, Any] = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
        }
        if self.config.user_agent:
            context_kwargs["user_agent"] = self.config.user_agent
        if self.config.storage_state_path and self.config.storage_state_path.exists():
            context_kwargs["storage_state"] = str(self.config.storage_state_path)

        self.context = await self.browser.new_context(**context_kwargs)
        self.page = await self.context.new_page()

        logger.info("Launched new browser instance")

    async def _connect_existing_browser(self) -> None:
        """Connect to an existing browser via CDP."""
        cdp_url = self._build_cdp_url()

        try:
            logger.info("Connecting to existing browser at %s", cdp_url)

            # Try different connection strategies
            try:
                self.browser = await self.playwright.chromium.connect_over_cdp(cdp_url)
            except Exception:
                # Try WebSocket connection
                ws_url = await self._get_ws_endpoint(cdp_url)
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
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()

            logger.info("Connected to existing browser")

        except Exception as e:
            raise BrowserSessionError(f"Failed to connect to existing browser: {e}")

    def _build_cdp_url(self) -> str:
        """Build CDP URL from config."""
        scheme = self.config.debug_scheme
        host = self.config.debug_host or "localhost"
        port = self.config.debug_port or 9222
        return f"{scheme}://{host}:{port}"

    async def _get_ws_endpoint(self, cdp_url: str) -> str:
        """Get WebSocket endpoint from CDP URL."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{cdp_url}/json/version") as response:
                data = await response.json()
                return data.get("webSocketDebuggerUrl", "")

    async def _ensure_active_page(self) -> bool:
        """Ensure we have an active page."""
        if self.page is None:
            if self.context:
                self.page = await self.context.new_page()
        return self.page is not None

    async def _save_storage_state(self) -> None:
        """Save browser storage state for session persistence."""
        if self.context and self.config.storage_state_path:
            await self.context.storage_state(path=str(self.config.storage_state_path))
            logger.info("Saved storage state to %s", self.config.storage_state_path)

    # -------------------------------------------------------------------------
    # Page operations
    # -------------------------------------------------------------------------

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigate to a URL.

        Args:
            url: Target URL
            wait_until: When to consider navigation complete
        """
        if not self.page:
            raise BrowserSessionError("Browser not started")
        await self.page.goto(url, wait_until=wait_until)

    async def get_content(self) -> str:
        """Get page HTML content."""
        if not self.page:
            raise BrowserSessionError("Browser not started")
        return await self.page.content()

    async def get_text(self, selector: str) -> str:
        """Get text content of an element.

        Args:
            selector: CSS selector

        Returns:
            Element text content
        """
        if not self.page:
            raise BrowserSessionError("Browser not started")
        element = await self.page.wait_for_selector(selector)
        return await element.text_content() if element else ""

    async def click(self, selector: str) -> None:
        """Click an element.

        Args:
            selector: CSS selector
        """
        if not self.page:
            raise BrowserSessionError("Browser not started")
        await self.page.click(selector)

    async def fill(self, selector: str, value: str) -> None:
        """Fill an input field.

        Args:
            selector: CSS selector
            value: Value to fill
        """
        if not self.page:
            raise BrowserSessionError("Browser not started")
        await self.page.fill(selector, value)

    async def screenshot(
        self, path: str | None = None, full_page: bool = False
    ) -> bytes:
        """Take a screenshot.

        Args:
            path: Optional path to save screenshot
            full_page: Capture full page or just viewport

        Returns:
            Screenshot bytes
        """
        if not self.page:
            raise BrowserSessionError("Browser not started")
        return await self.page.screenshot(path=path, full_page=full_page)

    async def wait_for_selector(
        self, selector: str, timeout: int | None = None
    ) -> Any:
        """Wait for an element to appear.

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds

        Returns:
            Element handle
        """
        if not self.page:
            raise BrowserSessionError("Browser not started")
        return await self.page.wait_for_selector(
            selector, timeout=timeout or self.config.timeout
        )

    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript in page context.

        Args:
            expression: JavaScript expression

        Returns:
            Evaluation result
        """
        if not self.page:
            raise BrowserSessionError("Browser not started")
        return await self.page.evaluate(expression)

    async def set_files(self, selector: str, files: list[str]) -> None:
        """Set files for a file input.

        Args:
            selector: CSS selector for file input
            files: List of file paths
        """
        if not self.page:
            raise BrowserSessionError("Browser not started")
        await self.page.set_input_files(selector, files)


# -------------------------------------------------------------------------
# Session pool for managing multiple browser instances
# -------------------------------------------------------------------------

_session_pool: dict[str, BrowserSession] = {}
_session_lock = asyncio.Lock()


def _normalize_config_key(config: BrowserConfig | None) -> str:
    """Generate a unique key for a browser config."""
    if not config:
        return "__default__"
    if config.debug_host:
        return f"{config.debug_host}:{config.debug_port or 9222}"
    return "__default__"


async def get_browser_session(config: BrowserConfig | None = None) -> BrowserSession:
    """Get or create a browser session.

    Args:
        config: Browser configuration

    Returns:
        Browser session instance
    """
    key = _normalize_config_key(config)

    async with _session_lock:
        session = _session_pool.get(key)
        if not session:
            session = BrowserSession(config)
            await session.start()
            _session_pool[key] = session
        elif session.page is None:
            await session.start()
        return session


async def cleanup_browser_session(config: BrowserConfig | None = None) -> None:
    """Cleanup a specific browser session.

    Args:
        config: Browser configuration to identify session
    """
    key = _normalize_config_key(config)

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


async def run_with_browser(
    fn: Callable[[BrowserSession], Awaitable[T]],
    config: BrowserConfig | None = None,
) -> T:
    """Run an operation with a browser session.

    This function handles session pooling and error recovery.

    Args:
        fn: Async function to run with browser session
        config: Browser configuration

    Returns:
        Function result
    """
    key = _normalize_config_key(config)
    session = await get_browser_session(config)

    try:
        return await fn(session)
    except Exception as e:
        # Clean up session on error to prevent state pollution
        logger.warning("Browser operation failed, cleaning up session: %s", e)
        await cleanup_browser_session(config)
        raise
