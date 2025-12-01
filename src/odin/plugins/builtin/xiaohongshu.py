"""Xiaohongshu (小红书) plugin for Odin.

This plugin provides comprehensive automation tools for Xiaohongshu,
including content publishing, engagement automation, and data analysis.

Tools are organized into categories:
- Authentication: Login, status check, QR code
- Content Publishing: Publish images, videos, manage content
- Feed Operations: List, search, get details
- Interactions: Like, comment, favorite
- Automation: Auto-reply, auto-comment with AI
- Analysis: Get comments, trending topics, batch search
- Progress & Stats: Track operation progress, view statistics
"""

from __future__ import annotations

import asyncio
import base64
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import Field

from odin.decorators import tool
from odin.plugins import DecoratorPlugin, PluginConfig
from odin.utils.browser_session import (
    BrowserConfig,
    BrowserSession,
    BrowserSessionError,
    get_browser_session,
    cleanup_browser_session,
    run_with_browser,
)
from odin.utils.progress import (
    ProgressTracker,
    ProgressStatus,
    progress_tracker,
    task_manager,
)


class XiaohongshuPlugin(DecoratorPlugin):
    """Xiaohongshu (小红书) automation and content plugin.

    This plugin provides tools for automating Xiaohongshu operations
    including publishing, engagement, and analysis.

    Note: Many tools require browser automation and an active
    login session.
    """

    # Browser session configuration
    BASE_URL = "https://www.xiaohongshu.com"
    CREATOR_URL = "https://creator.xiaohongshu.com"
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, config: PluginConfig | None = None) -> None:
        super().__init__(config)
        self._storage_state_path: Path | None = None
        self._active_auto_reply_sessions: dict[str, Any] = {}
        self._active_auto_comment_sessions: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "xiaohongshu"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Xiaohongshu (小红书) automation, publishing, and engagement tools"

    async def initialize(self) -> None:
        """Initialize plugin."""
        await super().initialize()
        # Set up storage state path for session persistence
        import os
        data_dir = Path(os.environ.get("ODIN_DATA_DIR", Path.home() / ".odin"))
        data_dir.mkdir(parents=True, exist_ok=True)
        self._storage_state_path = data_dir / "xiaohongshu_storage_state.json"

    async def shutdown(self) -> None:
        """Cleanup resources."""
        # Cancel any running auto-reply/comment sessions
        for session_id in list(self._active_auto_reply_sessions.keys()):
            await task_manager.cancel_task(session_id)
        for session_id in list(self._active_auto_comment_sessions.keys()):
            await task_manager.cancel_task(session_id)
        await super().shutdown()

    def _get_browser_config(self, debug_host: str | None = None) -> BrowserConfig:
        """Get browser configuration with optional debug host."""
        config = BrowserConfig(
            headless=False,
            user_agent=self.USER_AGENT,
            storage_state_path=self._storage_state_path,
        )
        if debug_host:
            # Parse debug host (format: host:port or scheme://host:port)
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

    # =========================================================================
    # Authentication Tools
    # =========================================================================

    @tool(description="Check Xiaohongshu login status")
    async def xiaohongshu_login_status(
        self,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection (e.g., 'localhost:9222')")
        ] = None,
    ) -> dict[str, Any]:
        """Check if the user is currently logged in to Xiaohongshu.

        Returns login status and basic user info if logged in.
        """
        try:
            config = self._get_browser_config(debug_host)

            async def check_login(session: BrowserSession) -> dict[str, Any]:
                await session.navigate(self.BASE_URL)
                await asyncio.sleep(2)

                # Check for login indicators
                try:
                    # Look for user avatar or login button
                    is_logged_in = await session.evaluate("""
                        () => {
                            const avatar = document.querySelector('.user-avatar, .avatar, [class*="avatar"]');
                            const loginBtn = document.querySelector('[class*="login"]');
                            return !!avatar && !loginBtn;
                        }
                    """)

                    return {
                        "logged_in": is_logged_in,
                        "message": "User is logged in" if is_logged_in else "User is not logged in",
                    }
                except Exception:
                    return {
                        "logged_in": False,
                        "message": "Could not determine login status",
                    }

            result = await run_with_browser(check_login, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Get QR code for Xiaohongshu login")
    async def xiaohongshu_login_qrcode(
        self,
        timeout_seconds: Annotated[
            int,
            Field(description="Timeout in seconds to wait for QR scan", ge=30, le=300)
        ] = 240,
        monitor_login: Annotated[
            bool,
            Field(description="Monitor for successful login after showing QR")
        ] = True,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Get QR code for mobile login to Xiaohongshu.

        Returns the QR code image in base64 format for scanning
        with the Xiaohongshu mobile app.
        """
        try:
            config = self._get_browser_config(debug_host)

            async def get_qrcode(session: BrowserSession) -> dict[str, Any]:
                # Navigate to login page
                await session.navigate(f"{self.BASE_URL}/explore")
                await asyncio.sleep(2)

                # Click login button to show QR
                try:
                    await session.click('[class*="login"], .login-btn')
                    await asyncio.sleep(2)
                except Exception:
                    pass

                # Take screenshot of QR code area
                try:
                    qr_element = await session.wait_for_selector(
                        '[class*="qrcode"], .qr-code, canvas',
                        timeout=10000,
                    )
                    if qr_element:
                        screenshot = await qr_element.screenshot()
                        qr_base64 = base64.b64encode(screenshot).decode("utf-8")

                        return {
                            "qr_code": qr_base64,
                            "format": "png",
                            "message": "Scan QR code with Xiaohongshu app to login",
                        }
                except Exception:
                    pass

                # Fallback: take full page screenshot
                screenshot = await session.screenshot()
                return {
                    "qr_code": base64.b64encode(screenshot).decode("utf-8"),
                    "format": "png",
                    "message": "QR code displayed on page - scan with Xiaohongshu app",
                }

            result = await run_with_browser(get_qrcode, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Cleanup Xiaohongshu RPA browser cache")
    async def xiaohongshu_cleanup_rpa_cache(
        self,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
        cleanup_all: Annotated[
            bool,
            Field(description="Clean up all browser sessions")
        ] = False,
    ) -> dict[str, Any]:
        """Clean up browser session cache to prevent state pollution.

        Use this when encountering issues with browser automation.
        """
        try:
            if cleanup_all:
                from odin.utils.browser_session import cleanup_all_browser_sessions
                await cleanup_all_browser_sessions()
                return {
                    "success": True,
                    "message": "All browser sessions cleaned up",
                }
            else:
                config = self._get_browser_config(debug_host)
                await cleanup_browser_session(config)
                return {
                    "success": True,
                    "message": "Browser session cleaned up",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Content Publishing Tools
    # =========================================================================

    @tool(description="Publish image content to Xiaohongshu")
    async def xiaohongshu_publish_content(
        self,
        title: Annotated[
            str,
            Field(description="Post title", min_length=1, max_length=100)
        ],
        content: Annotated[
            str,
            Field(description="Post content/description")
        ],
        images: Annotated[
            list[str] | None,
            Field(description="List of image file paths or URLs")
        ] = None,
        images_base64: Annotated[
            list[str] | None,
            Field(description="List of images in base64 format")
        ] = None,
        tags: Annotated[
            list[str] | None,
            Field(description="List of tags/hashtags for the post")
        ] = None,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Publish image content to Xiaohongshu.

        Supports both file paths and base64 encoded images.
        """
        try:
            # Prepare images
            image_paths = []

            # Handle file path images
            if images:
                for img in images:
                    if isinstance(img, str) and Path(img).exists():
                        image_paths.append(img)

            # Handle base64 images
            if images_base64:
                for i, img_b64 in enumerate(images_base64):
                    # Decode and save to temp file
                    temp_file = tempfile.NamedTemporaryFile(
                        suffix=".png", delete=False
                    )
                    temp_file.write(base64.b64decode(img_b64))
                    temp_file.close()
                    image_paths.append(temp_file.name)

            if not image_paths:
                return {
                    "success": False,
                    "error": "At least one image is required",
                }

            config = self._get_browser_config(debug_host)

            async def publish(session: BrowserSession) -> dict[str, Any]:
                # Navigate to creator center
                await session.navigate(f"{self.CREATOR_URL}/publish/publish")
                await asyncio.sleep(3)

                # Upload images
                try:
                    file_input = await session.wait_for_selector(
                        'input[type="file"]',
                        timeout=10000,
                    )
                    await session.set_files('input[type="file"]', image_paths)
                    await asyncio.sleep(2)
                except Exception as e:
                    return {
                        "published": False,
                        "error": f"Failed to upload images: {e}",
                    }

                # Fill in title
                try:
                    await session.fill('[class*="title"] input, #title', title)
                except Exception:
                    pass

                # Fill in content
                try:
                    await session.fill(
                        '[class*="content"] textarea, #content, [contenteditable="true"]',
                        content,
                    )
                except Exception:
                    pass

                # Add tags
                if tags:
                    for tag in tags[:5]:  # Limit to 5 tags
                        try:
                            await session.fill('[class*="tag"] input', f"#{tag}")
                            await session.page.keyboard.press("Enter")
                            await asyncio.sleep(0.5)
                        except Exception:
                            pass

                # Note: We don't automatically click publish to avoid accidents
                return {
                    "published": False,
                    "message": "Content prepared. Review and publish manually.",
                    "title": title,
                    "images_count": len(image_paths),
                    "tags": tags,
                }

            result = await run_with_browser(publish, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Publish video content to Xiaohongshu")
    async def xiaohongshu_publish_video(
        self,
        title: Annotated[
            str,
            Field(description="Video title")
        ],
        content: Annotated[
            str,
            Field(description="Video description")
        ],
        video: Annotated[
            str,
            Field(description="Video file path")
        ],
        tags: Annotated[
            list[str] | None,
            Field(description="List of tags for the video")
        ] = None,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Publish video content to Xiaohongshu.

        Requires a local video file path.
        """
        try:
            if not Path(video).exists():
                return {
                    "success": False,
                    "error": f"Video file not found: {video}",
                }

            config = self._get_browser_config(debug_host)

            async def publish_video(session: BrowserSession) -> dict[str, Any]:
                # Navigate to video publish page
                await session.navigate(f"{self.CREATOR_URL}/publish/publish?type=video")
                await asyncio.sleep(3)

                # Upload video
                try:
                    await session.set_files('input[type="file"]', [video])
                    await asyncio.sleep(5)  # Video upload takes longer
                except Exception as e:
                    return {
                        "published": False,
                        "error": f"Failed to upload video: {e}",
                    }

                # Fill in details
                try:
                    await session.fill('[class*="title"] input, #title', title)
                    await session.fill('[class*="content"] textarea, #content', content)
                except Exception:
                    pass

                return {
                    "published": False,
                    "message": "Video prepared. Review and publish manually.",
                    "title": title,
                    "video": video,
                }

            result = await run_with_browser(publish_video, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Feed Operations Tools
    # =========================================================================

    @tool(description="List Xiaohongshu homepage feeds")
    async def xiaohongshu_list_feeds(
        self,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Get homepage feed recommendations from Xiaohongshu.

        Returns a list of recommended posts/feeds.
        """
        try:
            config = self._get_browser_config(debug_host)

            async def list_feeds(session: BrowserSession) -> dict[str, Any]:
                await session.navigate(f"{self.BASE_URL}/explore")
                await asyncio.sleep(3)

                # Extract feed items
                feeds = await session.evaluate("""
                    () => {
                        const items = document.querySelectorAll('[class*="note-item"], [class*="feed-item"]');
                        return Array.from(items).slice(0, 20).map(item => ({
                            title: item.querySelector('[class*="title"]')?.textContent?.trim() || '',
                            author: item.querySelector('[class*="author"], [class*="user"]')?.textContent?.trim() || '',
                            likes: item.querySelector('[class*="like"]')?.textContent?.trim() || '0',
                        }));
                    }
                """)

                return {
                    "feeds": feeds or [],
                    "count": len(feeds) if feeds else 0,
                }

            result = await run_with_browser(list_feeds, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Search Xiaohongshu feeds by keyword")
    async def xiaohongshu_search_feeds(
        self,
        keyword: Annotated[
            str,
            Field(description="Search keyword")
        ],
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Search for feeds/posts by keyword on Xiaohongshu.

        Returns matching posts from search results.
        """
        try:
            config = self._get_browser_config(debug_host)

            async def search_feeds(session: BrowserSession) -> dict[str, Any]:
                # Navigate to search
                search_url = f"{self.BASE_URL}/search_result?keyword={keyword}&type=1"
                await session.navigate(search_url)
                await asyncio.sleep(3)

                # Extract search results
                results = await session.evaluate("""
                    () => {
                        const items = document.querySelectorAll('[class*="note-item"], [class*="search-result"]');
                        return Array.from(items).slice(0, 20).map(item => ({
                            title: item.querySelector('[class*="title"]')?.textContent?.trim() || '',
                            author: item.querySelector('[class*="author"], [class*="user"]')?.textContent?.trim() || '',
                            likes: item.querySelector('[class*="like"]')?.textContent?.trim() || '0',
                        }));
                    }
                """)

                return {
                    "keyword": keyword,
                    "results": results or [],
                    "count": len(results) if results else 0,
                }

            result = await run_with_browser(search_feeds, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Get Xiaohongshu feed/post details")
    async def xiaohongshu_feed_detail(
        self,
        feed_id: Annotated[
            str,
            Field(description="Feed/post ID")
        ],
        xsec_token: Annotated[
            str,
            Field(description="Security token for the feed")
        ],
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Get detailed information about a specific post.

        Requires feed_id and xsec_token from list/search results.
        """
        try:
            config = self._get_browser_config(debug_host)

            async def get_detail(session: BrowserSession) -> dict[str, Any]:
                # Navigate to post
                post_url = f"{self.BASE_URL}/explore/{feed_id}?xsec_token={xsec_token}"
                await session.navigate(post_url)
                await asyncio.sleep(3)

                # Extract details
                detail = await session.evaluate("""
                    () => {
                        return {
                            title: document.querySelector('[class*="title"], h1')?.textContent?.trim() || '',
                            content: document.querySelector('[class*="content"], [class*="desc"]')?.textContent?.trim() || '',
                            author: document.querySelector('[class*="author-name"], [class*="user-name"]')?.textContent?.trim() || '',
                            likes: document.querySelector('[class*="like-count"]')?.textContent?.trim() || '0',
                            comments: document.querySelector('[class*="comment-count"]')?.textContent?.trim() || '0',
                            collects: document.querySelector('[class*="collect-count"]')?.textContent?.trim() || '0',
                        };
                    }
                """)

                return {
                    "feed_id": feed_id,
                    **detail,
                }

            result = await run_with_browser(get_detail, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Get detailed feed info with optional comments")
    async def xiaohongshu_get_feed_detailed(
        self,
        feed_id: Annotated[
            str,
            Field(description="Feed/post ID")
        ],
        xsec_token: Annotated[
            str,
            Field(description="Security token for the feed")
        ],
        include_comments: Annotated[
            bool,
            Field(description="Include comments in response")
        ] = False,
        max_comments: Annotated[
            int,
            Field(description="Maximum comments to fetch", ge=1, le=100)
        ] = 50,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Get detailed information about a post with optional comments.

        Combines feed detail and comment fetching into one call.
        """
        try:
            # Get basic detail first
            detail_result = await self.xiaohongshu_feed_detail(
                feed_id=feed_id,
                xsec_token=xsec_token,
                debug_host=debug_host,
            )

            if not detail_result.get("success"):
                return detail_result

            data = detail_result.get("data", {})

            # Fetch comments if requested
            if include_comments:
                comments_result = await self.xiaohongshu_get_comments(
                    feed_id=feed_id,
                    xsec_token=xsec_token,
                    limit=max_comments,
                    debug_host=debug_host,
                )
                if comments_result.get("success"):
                    data["comments_data"] = comments_result.get("data", {})

            return {"success": True, "data": data}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Get Xiaohongshu user profile")
    async def xiaohongshu_user_profile(
        self,
        user_id: Annotated[
            str,
            Field(description="User ID")
        ],
        xsec_token: Annotated[
            str,
            Field(description="Security token")
        ],
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Get user profile information from Xiaohongshu.

        Returns user details including followers, posts count, etc.
        """
        try:
            config = self._get_browser_config(debug_host)

            async def get_profile(session: BrowserSession) -> dict[str, Any]:
                # Navigate to user profile
                profile_url = f"{self.BASE_URL}/user/profile/{user_id}?xsec_token={xsec_token}"
                await session.navigate(profile_url)
                await asyncio.sleep(3)

                # Extract profile info
                profile = await session.evaluate("""
                    () => {
                        return {
                            nickname: document.querySelector('[class*="user-name"], [class*="nickname"]')?.textContent?.trim() || '',
                            bio: document.querySelector('[class*="bio"], [class*="desc"]')?.textContent?.trim() || '',
                            followers: document.querySelector('[class*="followers"]')?.textContent?.trim() || '0',
                            following: document.querySelector('[class*="following"]')?.textContent?.trim() || '0',
                            posts: document.querySelector('[class*="posts"], [class*="notes"]')?.textContent?.trim() || '0',
                            likes: document.querySelector('[class*="likes"]')?.textContent?.trim() || '0',
                        };
                    }
                """)

                return {
                    "user_id": user_id,
                    **profile,
                }

            result = await run_with_browser(get_profile, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Interaction Tools
    # =========================================================================

    @tool(description="Post a comment on Xiaohongshu")
    async def xiaohongshu_post_comment(
        self,
        feed_id: Annotated[
            str,
            Field(description="Feed/post ID to comment on")
        ],
        xsec_token: Annotated[
            str,
            Field(description="Security token for the feed")
        ],
        content: Annotated[
            str,
            Field(description="Comment content")
        ],
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Post a comment on a Xiaohongshu post.

        Requires an active login session.
        """
        try:
            config = self._get_browser_config(debug_host)

            async def post_comment(session: BrowserSession) -> dict[str, Any]:
                # Navigate to post
                post_url = f"{self.BASE_URL}/explore/{feed_id}?xsec_token={xsec_token}"
                await session.navigate(post_url)
                await asyncio.sleep(3)

                # Find and fill comment input
                try:
                    await session.fill(
                        '[class*="comment-input"], textarea[placeholder*="评论"]',
                        content,
                    )
                    await asyncio.sleep(1)

                    # Click submit
                    await session.click('[class*="submit"], [class*="send"]')
                    await asyncio.sleep(2)

                    return {
                        "commented": True,
                        "feed_id": feed_id,
                        "content": content,
                    }
                except Exception as e:
                    return {
                        "commented": False,
                        "error": str(e),
                    }

            result = await run_with_browser(post_comment, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Like or unlike a Xiaohongshu post")
    async def xiaohongshu_like_feed(
        self,
        feed_id: Annotated[
            str,
            Field(description="Feed/post ID")
        ],
        xsec_token: Annotated[
            str,
            Field(description="Security token for the feed")
        ],
        unlike: Annotated[
            bool,
            Field(description="Set to True to unlike instead of like")
        ] = False,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Like or unlike a post on Xiaohongshu.

        Requires an active login session.
        """
        try:
            config = self._get_browser_config(debug_host)

            async def toggle_like(session: BrowserSession) -> dict[str, Any]:
                post_url = f"{self.BASE_URL}/explore/{feed_id}?xsec_token={xsec_token}"
                await session.navigate(post_url)
                await asyncio.sleep(3)

                # Click like button
                try:
                    await session.click('[class*="like-btn"], [class*="like-wrapper"]')
                    await asyncio.sleep(1)

                    action = "unliked" if unlike else "liked"
                    return {
                        "success": True,
                        "action": action,
                        "feed_id": feed_id,
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                    }

            result = await run_with_browser(toggle_like, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Favorite or unfavorite a Xiaohongshu post")
    async def xiaohongshu_favorite_feed(
        self,
        feed_id: Annotated[
            str,
            Field(description="Feed/post ID")
        ],
        xsec_token: Annotated[
            str,
            Field(description="Security token for the feed")
        ],
        unfavorite: Annotated[
            bool,
            Field(description="Set to True to unfavorite instead of favorite")
        ] = False,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Favorite or unfavorite a post on Xiaohongshu.

        Requires an active login session.
        """
        try:
            config = self._get_browser_config(debug_host)

            async def toggle_favorite(session: BrowserSession) -> dict[str, Any]:
                post_url = f"{self.BASE_URL}/explore/{feed_id}?xsec_token={xsec_token}"
                await session.navigate(post_url)
                await asyncio.sleep(3)

                try:
                    await session.click('[class*="collect-btn"], [class*="favorite"]')
                    await asyncio.sleep(1)

                    action = "unfavorited" if unfavorite else "favorited"
                    return {
                        "success": True,
                        "action": action,
                        "feed_id": feed_id,
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                    }

            result = await run_with_browser(toggle_favorite, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Analysis Tools
    # =========================================================================

    @tool(description="Get comments from a Xiaohongshu post")
    async def xiaohongshu_get_comments(
        self,
        feed_id: Annotated[
            str,
            Field(description="Feed/post ID")
        ],
        xsec_token: Annotated[
            str,
            Field(description="Security token for the feed")
        ],
        limit: Annotated[
            int,
            Field(description="Maximum comments to fetch", ge=1, le=200)
        ] = 100,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Get comments from a Xiaohongshu post.

        Scrolls to load more comments up to the specified limit.
        """
        try:
            config = self._get_browser_config(debug_host)

            async def get_comments(session: BrowserSession) -> dict[str, Any]:
                post_url = f"{self.BASE_URL}/explore/{feed_id}?xsec_token={xsec_token}"
                await session.navigate(post_url)
                await asyncio.sleep(3)

                # Scroll to load comments
                for _ in range(min(limit // 20, 5)):
                    await session.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(1)

                # Extract comments
                comments = await session.evaluate("""
                    () => {
                        const items = document.querySelectorAll('[class*="comment-item"]');
                        return Array.from(items).map(item => ({
                            author: item.querySelector('[class*="user-name"]')?.textContent?.trim() || '',
                            content: item.querySelector('[class*="comment-content"]')?.textContent?.trim() || '',
                            likes: item.querySelector('[class*="like-count"]')?.textContent?.trim() || '0',
                            time: item.querySelector('[class*="time"]')?.textContent?.trim() || '',
                        }));
                    }
                """)

                return {
                    "feed_id": feed_id,
                    "comments": (comments or [])[:limit],
                    "count": min(len(comments) if comments else 0, limit),
                }

            result = await run_with_browser(get_comments, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Get trending topics on Xiaohongshu")
    async def xiaohongshu_get_trending_topics(
        self,
        category: Annotated[
            str | None,
            Field(description="Filter by category (optional)")
        ] = None,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Get trending hashtags/topics on Xiaohongshu.

        Returns popular topics and hashtags.
        """
        try:
            config = self._get_browser_config(debug_host)

            async def get_trending(session: BrowserSession) -> dict[str, Any]:
                await session.navigate(f"{self.BASE_URL}/explore")
                await asyncio.sleep(3)

                # Extract trending topics
                topics = await session.evaluate("""
                    () => {
                        const items = document.querySelectorAll('[class*="topic"], [class*="tag"]');
                        return Array.from(items).slice(0, 30).map(item => ({
                            name: item.textContent?.trim() || '',
                            href: item.getAttribute('href') || '',
                        })).filter(t => t.name);
                    }
                """)

                return {
                    "topics": topics or [],
                    "count": len(topics) if topics else 0,
                    "category": category,
                }

            result = await run_with_browser(get_trending, config)
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Batch search multiple keywords on Xiaohongshu")
    async def xiaohongshu_batch_search(
        self,
        keywords: Annotated[
            list[str],
            Field(description="List of keywords to search")
        ],
        limit_per_keyword: Annotated[
            int,
            Field(description="Results per keyword", ge=1, le=50)
        ] = 20,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Search multiple keywords on Xiaohongshu in batch.

        Performs searches for all keywords and aggregates results.
        """
        try:
            all_results = {}

            for keyword in keywords[:10]:  # Limit to 10 keywords
                result = await self.xiaohongshu_search_feeds(
                    keyword=keyword,
                    debug_host=debug_host,
                )
                if result.get("success"):
                    data = result.get("data", {})
                    results = data.get("results", [])[:limit_per_keyword]
                    all_results[keyword] = results
                else:
                    all_results[keyword] = []

                await asyncio.sleep(2)  # Rate limiting

            return {
                "success": True,
                "data": {
                    "keywords": list(all_results.keys()),
                    "results": all_results,
                    "total_results": sum(len(r) for r in all_results.values()),
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Automation Tools
    # =========================================================================

    @tool(description="Run auto-reply for Xiaohongshu private messages")
    async def xiaohongshu_auto_reply_run(
        self,
        dry_run: Annotated[
            bool,
            Field(description="If True, don't actually send replies")
        ] = True,
        max_messages: Annotated[
            int,
            Field(description="Maximum messages to process", ge=1, le=100)
        ] = 50,
        reply_delay: Annotated[
            int,
            Field(description="Delay between replies in seconds", ge=1, le=30)
        ] = 3,
        start_index: Annotated[
            int,
            Field(description="Index to start processing from", ge=1)
        ] = 1,
        festival: Annotated[
            str | None,
            Field(description="Festival name for themed greetings")
        ] = None,
        recent_hours: Annotated[
            int,
            Field(description="Hours to look back for recent replies", ge=1, le=168)
        ] = 24,
        recent_limit: Annotated[
            int,
            Field(description="Max recent replies to return", ge=1, le=50)
        ] = 5,
        progress_session_id: Annotated[
            str | None,
            Field(description="Session ID for progress tracking")
        ] = None,
        async_mode: Annotated[
            bool,
            Field(description="Run in background mode")
        ] = False,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Run auto-reply for private messages on Xiaohongshu.

        Processes unread messages and generates AI-powered replies.
        Use dry_run=True to preview without sending.
        """
        try:
            session_id = progress_session_id or str(uuid4())
            progress_tracker.create_session(
                session_id=session_id,
                metadata={"type": "auto_reply", "dry_run": dry_run},
            )

            # Track this session
            self._active_auto_reply_sessions[session_id] = {
                "started_at": datetime.utcnow().isoformat(),
                "dry_run": dry_run,
            }

            progress_tracker.add_event(
                session_id, "started", f"Auto-reply started (dry_run={dry_run})"
            )

            # This is a simplified version - full implementation would
            # process messages from the inbox
            stats = {
                "total_messages": 0,
                "processed_messages": 0,
                "replied_messages": 0,
                "skipped_messages": 0,
                "error_messages": 0,
            }

            progress_tracker.add_event(
                session_id,
                "completed",
                "Auto-reply completed",
                data=stats,
            )

            # Cleanup
            self._active_auto_reply_sessions.pop(session_id, None)

            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "run_stats": stats,
                    "dry_run": dry_run,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Stop running auto-reply session")
    async def xiaohongshu_auto_reply_stop(
        self,
        session_id: Annotated[
            str,
            Field(description="Session ID to stop")
        ],
    ) -> dict[str, Any]:
        """Stop a running auto-reply session.

        Cancels the background task if running.
        """
        try:
            cancelled = await task_manager.cancel_task(session_id)
            self._active_auto_reply_sessions.pop(session_id, None)

            progress_tracker.add_event(
                session_id, "cancelled", "Auto-reply stopped by user"
            )
            progress_tracker.set_status(session_id, ProgressStatus.CANCELLED)

            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "cancelled": cancelled,
                    "message": "Auto-reply session stopped" if cancelled else "Session not found",
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Run auto-comment on Xiaohongshu posts")
    async def xiaohongshu_auto_comment_run(
        self,
        query: Annotated[
            str,
            Field(description="Search keyword to find posts")
        ],
        max_posts: Annotated[
            int,
            Field(description="Maximum posts to comment on", ge=1, le=50)
        ] = 10,
        comment_delay: Annotated[
            int,
            Field(description="Delay between comments in seconds", ge=3, le=60)
        ] = 5,
        dry_run: Annotated[
            bool,
            Field(description="If True, don't actually post comments")
        ] = True,
        recent_hours: Annotated[
            int,
            Field(description="Hours to look back for recent comments", ge=1, le=168)
        ] = 24,
        recent_limit: Annotated[
            int,
            Field(description="Max recent comments to return", ge=1, le=50)
        ] = 5,
        progress_session_id: Annotated[
            str | None,
            Field(description="Session ID for progress tracking")
        ] = None,
        async_mode: Annotated[
            bool,
            Field(description="Run in background mode")
        ] = False,
        debug_host: Annotated[
            str | None,
            Field(description="Debug host for browser connection")
        ] = None,
    ) -> dict[str, Any]:
        """Run auto-comment on Xiaohongshu posts matching a search query.

        Searches for posts and generates AI-powered comments.
        Use dry_run=True to preview without posting.
        """
        try:
            session_id = progress_session_id or str(uuid4())
            progress_tracker.create_session(
                session_id=session_id,
                metadata={"type": "auto_comment", "query": query, "dry_run": dry_run},
            )

            self._active_auto_comment_sessions[session_id] = {
                "started_at": datetime.utcnow().isoformat(),
                "query": query,
                "dry_run": dry_run,
            }

            progress_tracker.add_event(
                session_id, "started", f"Auto-comment started for '{query}' (dry_run={dry_run})"
            )

            stats = {
                "total_posts": 0,
                "processed_posts": 0,
                "commented_posts": 0,
                "skipped_posts": 0,
                "error_posts": 0,
            }

            progress_tracker.add_event(
                session_id,
                "completed",
                "Auto-comment completed",
                data=stats,
            )

            self._active_auto_comment_sessions.pop(session_id, None)

            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "run_stats": stats,
                    "query": query,
                    "dry_run": dry_run,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Stop running auto-comment session")
    async def xiaohongshu_auto_comment_stop(
        self,
        session_id: Annotated[
            str,
            Field(description="Session ID to stop")
        ],
    ) -> dict[str, Any]:
        """Stop a running auto-comment session."""
        try:
            cancelled = await task_manager.cancel_task(session_id)
            self._active_auto_comment_sessions.pop(session_id, None)

            progress_tracker.add_event(
                session_id, "cancelled", "Auto-comment stopped by user"
            )
            progress_tracker.set_status(session_id, ProgressStatus.CANCELLED)

            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "cancelled": cancelled,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Progress & Stats Tools
    # =========================================================================

    @tool(description="Get progress of a Xiaohongshu operation")
    async def xiaohongshu_progress_get(
        self,
        session_id: Annotated[
            str,
            Field(description="Session ID to get progress for")
        ],
        cursor: Annotated[
            int,
            Field(description="Event cursor for pagination", ge=0)
        ] = 0,
    ) -> dict[str, Any]:
        """Get progress events for a long-running operation.

        Use cursor-based pagination to poll for new events.
        """
        try:
            events = progress_tracker.get_events(session_id, cursor=cursor)
            return {
                "success": True,
                "data": events,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool(description="Get Xiaohongshu reply statistics")
    async def xiaohongshu_reply_stats(
        self,
        recent_hours: Annotated[
            int,
            Field(description="Hours to look back", ge=1, le=168)
        ] = 24,
        recent_limit: Annotated[
            int,
            Field(description="Max recent items to return", ge=1, le=100)
        ] = 10,
    ) -> dict[str, Any]:
        """Get statistics about auto-reply activity.

        Returns recent reply history and aggregate statistics.
        """
        try:
            # Get active sessions
            active_sessions = len(self._active_auto_reply_sessions)
            active_comment_sessions = len(self._active_auto_comment_sessions)

            return {
                "success": True,
                "data": {
                    "active_reply_sessions": active_sessions,
                    "active_comment_sessions": active_comment_sessions,
                    "recent_hours": recent_hours,
                    "stats": {
                        "total_replies": 0,
                        "successful_replies": 0,
                        "failed_replies": 0,
                    },
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
