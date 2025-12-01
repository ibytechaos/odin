"""Odin utility modules.

This module provides common utilities used across Odin:
- Browser automation (Playwright-based with CDP support)
- Progress tracking for long-running operations
- HTTP client helpers
"""

from odin.utils.browser_session import (
    BrowserConfig,
    BrowserConnectionError,
    BrowserSession,
    BrowserSessionError,
    cleanup_all_browser_sessions,
    cleanup_browser_session,
    get_browser_session,
    run_with_browser,
)
from odin.utils.http_client import (
    AsyncHTTPClient,
    HTTPClientError,
)
from odin.utils.progress import (
    ProgressEvent,
    ProgressTracker,
    progress_tracker,
)

__all__ = [
    # Browser Session (Playwright-based with CDP support)
    "BrowserConfig",
    "BrowserConnectionError",
    "BrowserSession",
    "BrowserSessionError",
    "cleanup_all_browser_sessions",
    "cleanup_browser_session",
    "get_browser_session",
    "run_with_browser",
    # Progress Tracking
    "ProgressEvent",
    "ProgressTracker",
    "progress_tracker",
    # HTTP Client
    "AsyncHTTPClient",
    "HTTPClientError",
]
