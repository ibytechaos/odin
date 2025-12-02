"""Gemini plugin for Odin.

This plugin provides tools for automating Google Gemini's
deep research capabilities through browser automation.

Tools:
- gemini_deep_research: Automate Gemini deep research feature
"""


import asyncio
from datetime import datetime
from typing import Annotated, Any
from uuid import uuid4

from pydantic import Field

from odin.decorators import tool
from odin.plugins import DecoratorPlugin, PluginConfig
from odin.utils.browser_session import (
    BrowserConfig,
    BrowserSession,
    run_with_browser,
)
from odin.utils.progress import (
    ProgressStatus,
    progress_tracker,
)


class GeminiPlugin(DecoratorPlugin):
    """Google Gemini automation plugin.

    This plugin provides tools for automating Google Gemini,
    particularly the deep research feature.

    Note: Requires browser automation and a Google account
    with Gemini access.
    """

    GEMINI_URL = "https://gemini.google.com"
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, config: PluginConfig | None = None) -> None:
        super().__init__(config)

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Google Gemini deep research automation"

    def _get_browser_config(self, debug_host: str | None = None) -> BrowserConfig:
        """Get browser configuration with optional debug host."""
        config = BrowserConfig(
            headless=False,
            user_agent=self.USER_AGENT,
        )
        if debug_host:
            if "://" in debug_host:
                from urllib.parse import urlparse
                parsed = urlparse(debug_host)
                config.debug_scheme = parsed.scheme or "http"
                config.debug_host = parsed.hostname or "localhost"
                config.debug_port = parsed.port or 9222
            else:
                parts = debug_host.split(":")
                config.debug_host = parts[0]
                config.debug_port = int(parts[1]) if len(parts) > 1 else 9222
            config.reuse_existing = True
        return config

    @tool(description="Run Gemini deep research on a topic")
    async def gemini_deep_research(
        self,
        topic: Annotated[
            str | None,
            Field(description="Research topic. If None, resumes from existing state.")
        ] = None,
        confirm_plan: Annotated[
            bool,
            Field(description="Whether to auto-confirm the research plan")
        ] = True,
        wait_timeout: Annotated[
            int,
            Field(description="Maximum time to wait for research completion in seconds", ge=60, le=1800)
        ] = 600,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection (e.g., 'localhost:9222')")
        ] = None,
        progress_session_id: Annotated[
            str | None,
            Field(description="Session ID for progress tracking")
        ] = None,
        resume_url: Annotated[
            str | None,
            Field(description="URL to resume an existing research session")
        ] = None,
    ) -> dict[str, Any]:
        """Automate Google Gemini's deep research feature.

        This tool navigates to Gemini, initiates a deep research session,
        optionally confirms the research plan, and waits for completion.

        The research process typically takes several minutes. Use the
        progress tracking features to monitor status.

        Args:
            topic: The research topic or question
            confirm_plan: Auto-confirm the research plan when presented
            wait_timeout: Maximum wait time for research completion
            debug_host: Browser debug host for remote connection
            progress_session_id: Optional session ID for progress tracking
            resume_url: URL to resume an existing research session

        Returns:
            Research results including status, content, and metadata
        """
        try:
            # Create progress session
            session_id = progress_session_id or str(uuid4())
            progress_tracker.create_session(
                session_id=session_id,
                metadata={
                    "type": "gemini_deep_research",
                    "topic": topic,
                    "started_at": datetime.utcnow().isoformat(),
                },
            )

            progress_tracker.add_event(
                session_id,
                "started",
                f"Starting Gemini deep research: {topic or 'resuming'}",
            )

            config = self._get_browser_config(debug_host)

            async def run_research(session: BrowserSession) -> dict[str, Any]:
                # Navigate to Gemini
                if resume_url:
                    progress_tracker.add_event(
                        session_id, "navigating", "Resuming existing research session"
                    )
                    await session.navigate(resume_url)
                else:
                    progress_tracker.add_event(
                        session_id, "navigating", "Opening Gemini"
                    )
                    await session.navigate(self.GEMINI_URL)

                await asyncio.sleep(3)

                # If starting new research with a topic
                if topic and not resume_url:
                    # Look for the input field
                    progress_tracker.add_event(
                        session_id, "input", f"Entering research topic: {topic}"
                    )

                    try:
                        # Try different selectors for the input
                        input_selectors = [
                            'textarea[aria-label*="prompt"]',
                            'textarea[placeholder*="Enter"]',
                            '[contenteditable="true"]',
                            'textarea',
                        ]

                        for selector in input_selectors:
                            try:
                                await session.fill(selector, topic)
                                break
                            except Exception:
                                continue

                        await asyncio.sleep(1)

                        # Look for deep research option
                        try:
                            # Click on advanced options or deep research button
                            deep_research_selectors = [
                                '[aria-label*="Deep research"]',
                                'button:has-text("Deep")',
                                '[data-test-id*="deep"]',
                            ]

                            for selector in deep_research_selectors:
                                try:
                                    await session.click(selector)
                                    await asyncio.sleep(1)
                                    break
                                except Exception:
                                    continue
                        except Exception:
                            pass

                        # Submit the prompt
                        try:
                            submit_selectors = [
                                'button[aria-label*="Send"]',
                                'button[type="submit"]',
                                '[data-test-id*="send"]',
                            ]

                            for selector in submit_selectors:
                                try:
                                    await session.click(selector)
                                    break
                                except Exception:
                                    continue
                        except Exception:
                            # Try pressing Enter
                            await session.page.keyboard.press("Enter")

                        await asyncio.sleep(5)

                    except Exception as e:
                        progress_tracker.add_event(
                            session_id, "error", f"Failed to enter topic: {e}"
                        )
                        return {
                            "status": "error",
                            "error": f"Failed to enter research topic: {e}",
                        }

                # Handle research plan confirmation
                if confirm_plan:
                    progress_tracker.add_event(
                        session_id, "waiting", "Waiting for research plan..."
                    )

                    # Wait for plan to appear
                    plan_timeout = 60  # 60 seconds for plan
                    plan_start = asyncio.get_event_loop().time()

                    while asyncio.get_event_loop().time() - plan_start < plan_timeout:
                        try:
                            # Look for confirm/start button
                            confirm_selectors = [
                                'button:has-text("Start")',
                                'button:has-text("Confirm")',
                                'button:has-text("Begin")',
                                '[aria-label*="confirm"]',
                            ]

                            for selector in confirm_selectors:
                                try:
                                    await session.click(selector)
                                    progress_tracker.add_event(
                                        session_id, "confirmed", "Research plan confirmed"
                                    )
                                    break
                                except Exception:
                                    continue
                            else:
                                await asyncio.sleep(3)
                                continue
                            break
                        except Exception:
                            await asyncio.sleep(3)

                # Wait for research completion
                progress_tracker.add_event(
                    session_id, "researching", "Waiting for research to complete..."
                )

                research_start = asyncio.get_event_loop().time()
                last_update = research_start
                result_content = None

                while asyncio.get_event_loop().time() - research_start < wait_timeout:
                    # Check for completion indicators
                    try:
                        is_complete = await session.evaluate("""
                            () => {
                                // Look for completion indicators
                                const copyBtn = document.querySelector('button[aria-label*="Copy"]');
                                const exportBtn = document.querySelector('button:has-text("Export")');
                                const shareBtn = document.querySelector('button[aria-label*="Share"]');

                                // Check for loading indicators
                                const loading = document.querySelector('[class*="loading"], [class*="spinner"]');

                                return {
                                    hasExportOptions: !!(copyBtn || exportBtn || shareBtn),
                                    isLoading: !!loading,
                                };
                            }
                        """)

                        if is_complete.get("hasExportOptions") and not is_complete.get("isLoading"):
                            progress_tracker.add_event(
                                session_id, "extracting", "Research complete, extracting results..."
                            )

                            # Extract the research content
                            result_content = await session.evaluate("""
                                () => {
                                    // Try to find the main content area
                                    const selectors = [
                                        '[class*="response"]',
                                        '[class*="output"]',
                                        '[class*="result"]',
                                        '[data-test-id*="message"]',
                                        'article',
                                        'main',
                                    ];

                                    for (const selector of selectors) {
                                        const el = document.querySelector(selector);
                                        if (el && el.innerText.length > 100) {
                                            return el.innerText;
                                        }
                                    }

                                    // Fallback to body content
                                    return document.body.innerText.substring(0, 50000);
                                }
                            """)

                            break

                        # Update progress periodically
                        current_time = asyncio.get_event_loop().time()
                        if current_time - last_update > 30:
                            elapsed = int(current_time - research_start)
                            progress_tracker.add_event(
                                session_id,
                                "progress",
                                f"Research in progress... ({elapsed}s elapsed)",
                            )
                            last_update = current_time

                    except Exception:
                        pass

                    await asyncio.sleep(5)

                # Build result
                if result_content:
                    progress_tracker.add_event(
                        session_id,
                        "completed",
                        "Research completed successfully",
                    )
                    progress_tracker.set_status(session_id, ProgressStatus.COMPLETED)

                    return {
                        "status": "completed",
                        "topic": topic,
                        "content": result_content,
                        "session_id": session_id,
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                else:
                    progress_tracker.add_event(
                        session_id,
                        "timeout",
                        "Research timed out or no results found",
                    )
                    progress_tracker.set_status(session_id, ProgressStatus.FAILED)

                    # Get current page URL for resuming
                    current_url = await session.evaluate("() => window.location.href")

                    return {
                        "status": "timeout",
                        "topic": topic,
                        "session_id": session_id,
                        "resume_url": current_url,
                        "message": "Research timed out. Use resume_url to continue.",
                    }

            result = await run_with_browser(run_research, config)

            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    **result,
                },
            }

        except Exception as e:
            if progress_session_id or session_id:
                progress_tracker.add_event(
                    session_id, "error", f"Research failed: {e}"
                )
                progress_tracker.set_status(session_id, ProgressStatus.FAILED)

            return {
                "success": False,
                "error": str(e),
                "session_id": session_id if 'session_id' in locals() else None,
            }
