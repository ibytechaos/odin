"""Odin utility modules.

This module provides common utilities used across Odin:
- Browser automation (CDP-based and Playwright)
- Progress tracking for long-running operations
- HTTP client helpers
"""

from odin.utils.browser import BrowserManager, get_browser_manager
from odin.utils.browser_session import (
    BrowserSession,
    BrowserConfig,
    BrowserSessionError,
    BrowserLoginTimeout,
    get_browser_session,
    cleanup_browser_session,
    cleanup_all_browser_sessions,
    run_with_browser,
)
from odin.utils.progress import (
    ProgressTracker,
    ProgressEvent,
    progress_tracker,
)
from odin.utils.http_client import (
    AsyncHTTPClient,
    HTTPClientError,
)

__all__ = [
    # Browser Manager (CDP-based singleton)
    "BrowserManager",
    "get_browser_manager",
    # Browser Session (Playwright-based pooled sessions)
    "BrowserSession",
    "BrowserConfig",
    "BrowserSessionError",
    "BrowserLoginTimeout",
    "get_browser_session",
    "cleanup_browser_session",
    "cleanup_all_browser_sessions",
    "run_with_browser",
    # Progress Tracking
    "ProgressTracker",
    "ProgressEvent",
    "progress_tracker",
    # HTTP Client
    "AsyncHTTPClient",
    "HTTPClientError",
]
