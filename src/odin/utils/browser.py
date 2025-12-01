"""Unified Browser Automation Utility for Odin.

Provides a shared browser instance using Chrome DevTools Protocol (CDP).
All browser-based tools should use this utility instead of managing their own browser.

Usage:
    from odin.utils.browser import BrowserManager

    browser_manager = BrowserManager()
    page = await browser_manager.get_page()
    # Use page for automation...
    await browser_manager.close()

Start Chrome with remote debugging:
    macOS: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome --remote-debugging-port=9222
    Linux: google-chrome --remote-debugging-port=9222
    Windows: chrome.exe --remote-debugging-port=9222
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class BrowserManager:
    """Manages a shared browser connection via CDP.

    This class provides a singleton-like pattern for browser management,
    allowing multiple tools to share the same browser instance.
    """

    _instance: "BrowserManager | None" = None
    _lock: asyncio.Lock | None = None

    def __new__(cls) -> "BrowserManager":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize browser manager (only runs once due to singleton)."""
        if self._initialized:
            return

        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._download_dir: str | None = None
        self._initialized = True

    @classmethod
    async def _get_lock(cls) -> asyncio.Lock:
        """Get or create the async lock."""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    def _get_settings(self) -> tuple[str, str]:
        """Get browser settings from config."""
        try:
            from odin.config import get_settings

            settings = get_settings()
            debug_url = settings.browser_debug_url or "http://localhost:9222"
            download_dir = settings.browser_download_dir or tempfile.mkdtemp(prefix="odin_browser_")
        except Exception:
            # Fallback if settings not available
            debug_url = "http://localhost:9222"
            download_dir = tempfile.mkdtemp(prefix="odin_browser_")

        return debug_url, download_dir

    async def connect(self, force_reconnect: bool = False) -> None:
        """Connect to browser via CDP.

        Args:
            force_reconnect: If True, close existing connection and reconnect

        Raises:
            ConnectionError: If unable to connect to browser
        """
        lock = await self._get_lock()
        async with lock:
            if self._browser is not None and not force_reconnect:
                return

            # Close existing connection if any
            if force_reconnect and self._browser is not None:
                await self._close_internal()

            debug_url, download_dir = self._get_settings()
            self._download_dir = download_dir

            # Ensure download directory exists
            Path(download_dir).mkdir(parents=True, exist_ok=True)

            self._playwright = await async_playwright().start()

            try:
                # Connect to existing browser via CDP
                self._browser = await self._playwright.chromium.connect_over_cdp(
                    debug_url,
                    timeout=10000,  # 10 second timeout for connection
                )

                # Get existing context or create new one
                contexts = self._browser.contexts
                if contexts:
                    self._context = contexts[0]
                else:
                    self._context = await self._browser.new_context(
                        accept_downloads=True,
                    )

                # Get existing page or create new one
                pages = self._context.pages
                if pages:
                    self._page = pages[0]
                else:
                    self._page = await self._context.new_page()

            except Exception as e:
                if self._playwright:
                    await self._playwright.stop()
                    self._playwright = None
                raise ConnectionError(
                    f"Failed to connect to browser at {debug_url}. "
                    f"Make sure Chrome is running with --remote-debugging-port=9222. "
                    f"Error: {e}"
                ) from e

    async def _close_internal(self) -> None:
        """Internal close without lock (called from within locked context)."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
            self._context = None
            self._page = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    async def close(self) -> None:
        """Close browser connection (does not close the actual browser)."""
        lock = await self._get_lock()
        async with lock:
            await self._close_internal()

    async def get_page(self, new_page: bool = False) -> Page:
        """Get a page instance, connecting if necessary.

        Args:
            new_page: If True, create a new page instead of reusing existing

        Returns:
            Page instance for browser automation

        Raises:
            ConnectionError: If unable to connect to browser
        """
        await self.connect()

        if new_page and self._context:
            return await self._context.new_page()

        if self._page is None:
            raise ConnectionError("No page available")

        return self._page

    async def get_context(self) -> BrowserContext:
        """Get the browser context, connecting if necessary.

        Returns:
            BrowserContext instance

        Raises:
            ConnectionError: If unable to connect to browser
        """
        await self.connect()

        if self._context is None:
            raise ConnectionError("No context available")

        return self._context

    @property
    def is_connected(self) -> bool:
        """Check if browser is connected."""
        return self._browser is not None and self._browser.is_connected()

    @property
    def download_dir(self) -> str:
        """Get the download directory path."""
        if self._download_dir is None:
            _, download_dir = self._get_settings()
            self._download_dir = download_dir
        return self._download_dir

    async def navigate(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: int = 30000,
    ) -> dict[str, Any]:
        """Navigate to a URL with error handling.

        Args:
            url: URL to navigate to
            wait_until: Navigation wait condition (domcontentloaded, load, networkidle)
            timeout: Navigation timeout in milliseconds

        Returns:
            Dict with success status and current URL
        """
        try:
            page = await self.get_page()
            await page.goto(url, wait_until=wait_until, timeout=timeout)
            return {
                "success": True,
                "url": page.url,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url,
            }

    async def wait_for_selector(
        self,
        selector: str,
        timeout: int = 30000,
        state: str = "visible",
    ) -> bool:
        """Wait for a selector to appear.

        Args:
            selector: CSS selector to wait for
            timeout: Timeout in milliseconds
            state: Element state to wait for (visible, hidden, attached, detached)

        Returns:
            True if element found, False otherwise
        """
        try:
            page = await self.get_page()
            await page.wait_for_selector(selector, timeout=timeout, state=state)
            return True
        except Exception:
            return False


# Global instance for convenience
_browser_manager: BrowserManager | None = None


def get_browser_manager() -> BrowserManager:
    """Get the global browser manager instance.

    Returns:
        BrowserManager singleton instance
    """
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager


async def get_page(new_page: bool = False) -> Page:
    """Convenience function to get a browser page.

    Args:
        new_page: If True, create a new page

    Returns:
        Page instance
    """
    return await get_browser_manager().get_page(new_page=new_page)


async def close_browser() -> None:
    """Convenience function to close browser connection."""
    await get_browser_manager().close()
