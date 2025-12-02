"""Publishers plugin for Odin.

This plugin provides tools for publishing content to multiple
Chinese blogging and content platforms through browser automation.

Supported platforms:
- CSDN (csdn.net)
- Juejin (掘金 juejin.cn)
- Jianshu (简书 jianshu.com)
- Zhihu (知乎 zhihu.com)
- Toutiao (头条号 toutiao.com)
- CNBlogs (博客园 cnblogs.com)
- SegmentFault (segmentfault.com)
- OSChina (开源中国 oschina.net)
- 51CTO (51cto.com)
- InfoQ (infoq.cn)
- MPWeixin (微信公众号)
- Tencent Cloud (腾讯云开发者社区)
- Alibaba Cloud (阿里云开发者社区)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Any

from pydantic import Field

from odin.decorators import tool
from odin.plugins import DecoratorPlugin, PluginConfig
from odin.utils.browser_session import (
    BrowserConfig,
    BrowserSession,
    run_with_browser,
)


class Platform(str, Enum):
    """Supported publishing platforms."""
    CSDN = "csdn"
    JUEJIN = "juejin"
    JIANSHU = "jianshu"
    ZHIHU = "zhihu"
    TOUTIAO = "toutiao"
    CNBLOGS = "cnblogs"
    SEGMENTFAULT = "segmentfault"
    OSCHINA = "oschina"
    CTO51 = "cto51"
    INFOQ = "infoq"
    MPWEIXIN = "mpweixin"
    TXCLOUD = "txcloud"
    ALICLOUD = "alicloud"


@dataclass
class PlatformConfig:
    """Configuration for a publishing platform."""
    name: str
    url: str
    editor_url: str
    login_url: str
    selectors: dict[str, str]


# Platform configurations
PLATFORM_CONFIGS: dict[Platform, PlatformConfig] = {
    Platform.CSDN: PlatformConfig(
        name="CSDN",
        url="https://www.csdn.net",
        editor_url="https://editor.csdn.net/md",
        login_url="https://passport.csdn.net/login",
        selectors={
            "title": '[class*="title"] input, #title',
            "content": '.editor-content, [contenteditable="true"], textarea',
            "publish": '[class*="publish"], button:has-text("发布")',
        },
    ),
    Platform.JUEJIN: PlatformConfig(
        name="掘金",
        url="https://juejin.cn",
        editor_url="https://juejin.cn/editor/drafts/new",
        login_url="https://juejin.cn/login",
        selectors={
            "title": '[class*="title-input"], input[placeholder*="标题"]',
            "content": '[class*="CodeMirror"], [contenteditable="true"]',
            "publish": '[class*="publish-btn"], button:has-text("发布")',
        },
    ),
    Platform.JIANSHU: PlatformConfig(
        name="简书",
        url="https://www.jianshu.com",
        editor_url="https://www.jianshu.com/writer",
        login_url="https://www.jianshu.com/sign_in",
        selectors={
            "title": '[class*="title-input"], input[placeholder*="标题"]',
            "content": '[class*="editor"], [contenteditable="true"]',
            "publish": '[class*="publish"], button:has-text("发布")',
        },
    ),
    Platform.ZHIHU: PlatformConfig(
        name="知乎",
        url="https://www.zhihu.com",
        editor_url="https://zhuanlan.zhihu.com/write",
        login_url="https://www.zhihu.com/signin",
        selectors={
            "title": '[class*="WriteIndex-titleInput"], input[placeholder*="标题"]',
            "content": '[class*="WriteIndex-content"], [contenteditable="true"]',
            "publish": '[class*="PublishPanel-button"], button:has-text("发布")',
        },
    ),
    Platform.TOUTIAO: PlatformConfig(
        name="头条号",
        url="https://mp.toutiao.com",
        editor_url="https://mp.toutiao.com/profile_v4/graphic/publish",
        login_url="https://sso.toutiao.com",
        selectors={
            "title": '[class*="title-input"], input[placeholder*="标题"]',
            "content": '[class*="editor"], [contenteditable="true"]',
            "publish": '[class*="publish"], button:has-text("发布")',
        },
    ),
    Platform.CNBLOGS: PlatformConfig(
        name="博客园",
        url="https://www.cnblogs.com",
        editor_url="https://i.cnblogs.com/posts/edit",
        login_url="https://account.cnblogs.com/signin",
        selectors={
            "title": '#post-title, input[name="title"]',
            "content": '#Editor_Edit_EditorBody, [contenteditable="true"]',
            "publish": '#btn_post_publish, button:has-text("发布")',
        },
    ),
    Platform.SEGMENTFAULT: PlatformConfig(
        name="SegmentFault",
        url="https://segmentfault.com",
        editor_url="https://segmentfault.com/write",
        login_url="https://segmentfault.com/user/login",
        selectors={
            "title": '[class*="title"], input[placeholder*="标题"]',
            "content": '[class*="editor"], [contenteditable="true"]',
            "publish": '[class*="submit"], button:has-text("发布")',
        },
    ),
    Platform.OSCHINA: PlatformConfig(
        name="开源中国",
        url="https://www.oschina.net",
        editor_url="https://my.oschina.net/u/new-blog",
        login_url="https://www.oschina.net/home/login",
        selectors={
            "title": '[class*="title-input"], input[placeholder*="标题"]',
            "content": '[class*="editor"], [contenteditable="true"]',
            "publish": '[class*="publish"], button:has-text("发布")',
        },
    ),
    Platform.CTO51: PlatformConfig(
        name="51CTO",
        url="https://blog.51cto.com",
        editor_url="https://blog.51cto.com/blogger/publish",
        login_url="https://home.51cto.com/login",
        selectors={
            "title": '[class*="title"], input[name="title"]',
            "content": '[class*="editor"], [contenteditable="true"]',
            "publish": '[class*="publish"], button:has-text("发布")',
        },
    ),
    Platform.INFOQ: PlatformConfig(
        name="InfoQ",
        url="https://www.infoq.cn",
        editor_url="https://www.infoq.cn/write",
        login_url="https://www.infoq.cn/login",
        selectors={
            "title": '[class*="title"], input[placeholder*="标题"]',
            "content": '[class*="editor"], [contenteditable="true"]',
            "publish": '[class*="publish"], button:has-text("发布")',
        },
    ),
    Platform.MPWEIXIN: PlatformConfig(
        name="微信公众号",
        url="https://mp.weixin.qq.com",
        editor_url="https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit",
        login_url="https://mp.weixin.qq.com/",
        selectors={
            "title": '#title, input[name="title"]',
            "content": '#edui1_iframeholder, [contenteditable="true"]',
            "publish": '#js_send, button:has-text("发送")',
        },
    ),
    Platform.TXCLOUD: PlatformConfig(
        name="腾讯云开发者社区",
        url="https://cloud.tencent.com/developer",
        editor_url="https://cloud.tencent.com/developer/article/write",
        login_url="https://cloud.tencent.com/login",
        selectors={
            "title": '[class*="title"], input[placeholder*="标题"]',
            "content": '[class*="editor"], [contenteditable="true"]',
            "publish": '[class*="publish"], button:has-text("发布")',
        },
    ),
    Platform.ALICLOUD: PlatformConfig(
        name="阿里云开发者社区",
        url="https://developer.aliyun.com",
        editor_url="https://developer.aliyun.com/article/new",
        login_url="https://account.aliyun.com/login/login.htm",
        selectors={
            "title": '[class*="title"], input[placeholder*="标题"]',
            "content": '[class*="editor"], [contenteditable="true"]',
            "publish": '[class*="publish"], button:has-text("发布")',
        },
    ),
}


class PublishersPlugin(DecoratorPlugin):
    """Multi-platform content publishing plugin.

    This plugin provides tools for publishing content to various
    Chinese blogging and content platforms through browser automation.

    Note: Publishing requires active login sessions on target platforms.
    Use the login tools to authenticate before publishing.
    """

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, config: PluginConfig | None = None) -> None:
        super().__init__(config)

    @property
    def name(self) -> str:
        return "publishers"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Multi-platform blog publishing (CSDN, Juejin, Zhihu, etc.)"

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

    async def _publish_to_platform(
        self,
        platform: Platform,
        title: str,
        content: str,
        tags: list[str] | None = None,
        debug_host: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Internal method to publish content to a platform."""
        platform_config = PLATFORM_CONFIGS.get(platform)
        if not platform_config:
            return {
                "published": False,
                "error": f"Unknown platform: {platform}",
            }

        browser_config = self._get_browser_config(debug_host)

        async def do_publish(session: BrowserSession) -> dict[str, Any]:
            # Navigate to editor
            await session.navigate(platform_config.editor_url)
            await asyncio.sleep(3)

            selectors = platform_config.selectors

            # Fill title
            try:
                await session.fill(selectors["title"], title)
            except Exception as e:
                return {
                    "published": False,
                    "error": f"Failed to fill title: {e}",
                }

            # Fill content
            try:
                # Try to paste content into editor
                await session.click(selectors["content"])
                await asyncio.sleep(0.5)

                # For contenteditable elements
                await session.evaluate(f"""
                    (content) => {{
                        const editor = document.querySelector('{selectors["content"]}');
                        if (editor) {{
                            if (editor.tagName === 'TEXTAREA') {{
                                editor.value = content;
                            }} else {{
                                editor.innerHTML = content;
                            }}
                        }}
                    }}
                """)
            except Exception as e:
                return {
                    "published": False,
                    "error": f"Failed to fill content: {e}",
                }

            # If dry_run, don't click publish
            if dry_run:
                return {
                    "published": False,
                    "dry_run": True,
                    "message": f"Content prepared on {platform_config.name}. Review and publish manually.",
                    "platform": platform.value,
                    "title": title,
                }

            # Click publish
            try:
                await session.click(selectors["publish"])
                await asyncio.sleep(3)

                return {
                    "published": True,
                    "platform": platform.value,
                    "title": title,
                    "message": f"Content published to {platform_config.name}",
                }
            except Exception as e:
                return {
                    "published": False,
                    "error": f"Failed to publish: {e}",
                }

        return await run_with_browser(do_publish, browser_config)

    # =========================================================================
    # Individual Platform Publishing Tools
    # =========================================================================

    @tool(description="Publish content to CSDN")
    async def publish_to_csdn(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to CSDN (csdn.net).

        CSDN is one of the largest developer communities in China.
        """
        result = await self._publish_to_platform(
            Platform.CSDN, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to Juejin (掘金)")
    async def publish_to_juejin(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to Juejin (掘金).

        Juejin is a popular technical community for developers.
        """
        result = await self._publish_to_platform(
            Platform.JUEJIN, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to Jianshu (简书)")
    async def publish_to_jianshu(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to Jianshu (简书).

        Jianshu is a writing platform for all kinds of content.
        """
        result = await self._publish_to_platform(
            Platform.JIANSHU, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to Zhihu (知乎)")
    async def publish_to_zhihu(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to Zhihu Zhuanlan (知乎专栏).

        Zhihu is China's largest Q&A platform with article publishing.
        """
        result = await self._publish_to_platform(
            Platform.ZHIHU, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to Toutiao (头条号)")
    async def publish_to_toutiao(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to Toutiao (头条号).

        Toutiao is one of the most popular news and content apps in China.
        """
        result = await self._publish_to_platform(
            Platform.TOUTIAO, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to CNBlogs (博客园)")
    async def publish_to_cnblogs(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to CNBlogs (博客园).

        CNBlogs is a developer-focused blogging platform.
        """
        result = await self._publish_to_platform(
            Platform.CNBLOGS, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to SegmentFault")
    async def publish_to_segmentfault(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to SegmentFault.

        SegmentFault is a developer Q&A and blogging platform.
        """
        result = await self._publish_to_platform(
            Platform.SEGMENTFAULT, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to OSChina (开源中国)")
    async def publish_to_oschina(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to OSChina (开源中国).

        OSChina is a platform focused on open source projects.
        """
        result = await self._publish_to_platform(
            Platform.OSCHINA, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to 51CTO")
    async def publish_to_cto51(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to 51CTO.

        51CTO is a technical community for IT professionals.
        """
        result = await self._publish_to_platform(
            Platform.CTO51, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to InfoQ")
    async def publish_to_infoq(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to InfoQ China.

        InfoQ is a global technical news and knowledge platform.
        """
        result = await self._publish_to_platform(
            Platform.INFOQ, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to WeChat Official Account (微信公众号)")
    async def publish_to_mpweixin(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in HTML")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to WeChat Official Account (微信公众号).

        Note: WeChat requires HTML content, not Markdown.
        """
        result = await self._publish_to_platform(
            Platform.MPWEIXIN, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to Tencent Cloud Developer Community (腾讯云)")
    async def publish_to_txcloud(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to Tencent Cloud Developer Community.

        The developer community for Tencent Cloud services.
        """
        result = await self._publish_to_platform(
            Platform.TXCLOUD, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    @tool(description="Publish content to Alibaba Cloud Developer Community (阿里云)")
    async def publish_to_alicloud(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
    ) -> dict[str, Any]:
        """Publish article to Alibaba Cloud Developer Community.

        The developer community for Alibaba Cloud services.
        """
        result = await self._publish_to_platform(
            Platform.ALICLOUD, title, content, tags, debug_host, dry_run
        )
        return {"success": True, "data": result}

    # =========================================================================
    # Batch Publishing Tools
    # =========================================================================

    @tool(description="Publish content to multiple platforms at once")
    async def publish_batch(
        self,
        title: Annotated[str, Field(description="Article title")],
        content: Annotated[str, Field(description="Article content in Markdown")],
        platforms: Annotated[
            list[str],
            Field(description="List of platforms to publish to")
        ],
        tags: Annotated[list[str] | None, Field(description="Article tags")] = None,
        debug_host: Annotated[str | None, Field(description="Browser debug host")] = None,
        dry_run: Annotated[bool, Field(description="Preview without publishing")] = True,
        delay_between: Annotated[int, Field(description="Delay between platforms in seconds", ge=1, le=60)] = 5,
    ) -> dict[str, Any]:
        """Publish content to multiple platforms in batch.

        Sequentially publishes to each specified platform with
        a delay between operations.

        Args:
            title: Article title
            content: Article content in Markdown format
            platforms: List of platform names (csdn, juejin, zhihu, etc.)
            tags: Optional tags for the article
            debug_host: Browser debug host for remote connection
            dry_run: If True, prepare content without publishing
            delay_between: Seconds to wait between platform operations

        Returns:
            Results for each platform
        """
        results = {}
        successful = 0
        failed = 0

        for platform_name in platforms:
            try:
                platform = Platform(platform_name.lower())
            except ValueError:
                results[platform_name] = {
                    "success": False,
                    "error": f"Unknown platform: {platform_name}",
                }
                failed += 1
                continue

            result = await self._publish_to_platform(
                platform, title, content, tags, debug_host, dry_run
            )

            results[platform_name] = result
            if result.get("published") or result.get("dry_run"):
                successful += 1
            else:
                failed += 1

            # Delay between platforms
            if platform_name != platforms[-1]:
                await asyncio.sleep(delay_between)

        return {
            "success": True,
            "data": {
                "results": results,
                "summary": {
                    "total": len(platforms),
                    "successful": successful,
                    "failed": failed,
                    "dry_run": dry_run,
                },
            },
        }

    @tool(description="List all supported publishing platforms")
    async def list_platforms(self) -> dict[str, Any]:
        """List all supported publishing platforms.

        Returns information about each platform including
        name, URL, and status.
        """
        platforms = []
        for platform, config in PLATFORM_CONFIGS.items():
            platforms.append({
                "id": platform.value,
                "name": config.name,
                "url": config.url,
                "editor_url": config.editor_url,
            })

        return {
            "success": True,
            "data": {
                "platforms": platforms,
                "count": len(platforms),
            },
        }
