"""Tests for built-in plugins."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os
from pathlib import Path

from odin.plugins import (
    BUILTIN_PLUGINS,
    ContentPlugin,
    GeminiPlugin,
    GitHubPlugin,
    GooglePlugin,
    PublishersPlugin,
    TrendingPlugin,
    XiaohongshuPlugin,
    get_all_builtin_plugins,
    get_builtin_plugin,
)


class TestBuiltinPluginRegistry:
    """Test the built-in plugin registry and utilities."""

    def test_builtin_plugins_registry(self):
        """Test that all expected plugins are in the registry."""
        expected_plugins = {
            "github",
            "xiaohongshu",
            "gemini",
            "google",
            "trending",
            "content",
            "publishers",
        }
        assert set(BUILTIN_PLUGINS.keys()) == expected_plugins

    def test_get_builtin_plugin(self):
        """Test getting a specific built-in plugin."""
        plugin = get_builtin_plugin("github")
        assert plugin is not None
        assert isinstance(plugin, GitHubPlugin)
        assert plugin.name == "github"

    def test_get_nonexistent_builtin_plugin(self):
        """Test getting a non-existent plugin returns None."""
        plugin = get_builtin_plugin("nonexistent")
        assert plugin is None

    def test_get_all_builtin_plugins(self):
        """Test getting all built-in plugins."""
        plugins = get_all_builtin_plugins()
        assert len(plugins) == 7
        plugin_names = {p.name for p in plugins}
        assert "github" in plugin_names
        assert "xiaohongshu" in plugin_names


class TestGitHubPlugin:
    """Test GitHubPlugin functionality."""

    @pytest.fixture
    def plugin(self):
        """Create a GitHubPlugin instance."""
        return GitHubPlugin()

    def test_plugin_properties(self, plugin):
        """Test plugin metadata properties."""
        assert plugin.name == "github"
        assert plugin.version == "1.0.0"
        assert "GitHub" in plugin.description

    @pytest.mark.asyncio
    async def test_get_tools(self, plugin):
        """Test that all expected tools are registered."""
        await plugin.initialize()
        tools = await plugin.get_tools()

        tool_names = {t.name for t in tools}
        expected_tools = {
            "github_discover_trending",
            "github_deep_analyze",
            "github_extract_images",
            "github_get_project_status",
            "github_generate_markdown",
        }
        assert expected_tools == tool_names

    @pytest.mark.asyncio
    async def test_tool_parameters(self, plugin):
        """Test tool parameters are properly defined."""
        await plugin.initialize()
        tools = await plugin.get_tools()

        discover_tool = next(t for t in tools if t.name == "github_discover_trending")
        param_names = {p.name for p in discover_tool.parameters}
        assert "language" in param_names
        assert "since" in param_names


class TestXiaohongshuPlugin:
    """Test XiaohongshuPlugin functionality."""

    @pytest.fixture
    def plugin(self):
        """Create a XiaohongshuPlugin instance."""
        return XiaohongshuPlugin()

    def test_plugin_properties(self, plugin):
        """Test plugin metadata properties."""
        assert plugin.name == "xiaohongshu"
        assert plugin.version == "1.0.0"
        assert "小红书" in plugin.description or "Xiaohongshu" in plugin.description

    @pytest.mark.asyncio
    async def test_get_tools(self, plugin):
        """Test that tools are registered."""
        await plugin.initialize()
        tools = await plugin.get_tools()

        # Should have 22 tools
        assert len(tools) == 22

        tool_names = {t.name for t in tools}
        # Check some key tools (using xiaohongshu_ prefix)
        assert "xiaohongshu_login_status" in tool_names
        assert "xiaohongshu_publish_content" in tool_names
        assert "xiaohongshu_list_feeds" in tool_names
        assert "xiaohongshu_search_feeds" in tool_names


class TestGeminiPlugin:
    """Test GeminiPlugin functionality."""

    @pytest.fixture
    def plugin(self):
        """Create a GeminiPlugin instance."""
        return GeminiPlugin()

    def test_plugin_properties(self, plugin):
        """Test plugin metadata properties."""
        assert plugin.name == "gemini"
        assert plugin.version == "1.0.0"
        assert "Gemini" in plugin.description

    @pytest.mark.asyncio
    async def test_get_tools(self, plugin):
        """Test that all expected tools are registered."""
        await plugin.initialize()
        tools = await plugin.get_tools()

        assert len(tools) == 1
        assert tools[0].name == "gemini_deep_research"


class TestGooglePlugin:
    """Test GooglePlugin functionality."""

    @pytest.fixture
    def plugin(self):
        """Create a GooglePlugin instance."""
        return GooglePlugin()

    def test_plugin_properties(self, plugin):
        """Test plugin metadata properties."""
        assert plugin.name == "google"
        assert plugin.version == "1.0.0"
        assert "Google" in plugin.description

    @pytest.mark.asyncio
    async def test_get_tools(self, plugin):
        """Test that all expected tools are registered."""
        await plugin.initialize()
        tools = await plugin.get_tools()

        assert len(tools) == 1
        assert tools[0].name == "google_image_search"

    @pytest.mark.asyncio
    async def test_image_search_without_credentials(self, plugin):
        """Test image search returns error without credentials."""
        await plugin.initialize()
        result = await plugin.execute_tool(
            "google_image_search",
            queries=["test query"],
        )
        assert result["success"] is False
        assert "not configured" in result["error"].lower()


class TestTrendingPlugin:
    """Test TrendingPlugin functionality."""

    @pytest.fixture
    def plugin(self):
        """Create a TrendingPlugin instance."""
        return TrendingPlugin()

    def test_plugin_properties(self, plugin):
        """Test plugin metadata properties."""
        assert plugin.name == "trending"
        assert plugin.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_tools(self, plugin):
        """Test that all expected tools are registered."""
        await plugin.initialize()
        tools = await plugin.get_tools()

        tool_names = {t.name for t in tools}
        expected_tools = {
            "trending_mine_hot_topics",
            "trending_get_random_topic",
            "trending_mark_topic_published",
            "trending_mark_topic_in_progress",
            "trending_search_topics",
            "trending_get_statistics",
        }
        assert expected_tools == tool_names

    @pytest.mark.asyncio
    async def test_get_statistics(self, plugin):
        """Test getting statistics."""
        await plugin.initialize()
        result = await plugin.execute_tool("trending_get_statistics")

        assert result["success"] is True
        assert "data" in result
        assert "total_topics" in result["data"]
        assert "by_status" in result["data"]


class TestContentPlugin:
    """Test ContentPlugin functionality."""

    @pytest.fixture
    def plugin(self):
        """Create a ContentPlugin instance."""
        return ContentPlugin()

    def test_plugin_properties(self, plugin):
        """Test plugin metadata properties."""
        assert plugin.name == "content"
        assert plugin.version == "1.0.0"
        assert "Obsidian" in plugin.description or "Content" in plugin.description

    @pytest.mark.asyncio
    async def test_get_tools(self, plugin):
        """Test that all expected tools are registered."""
        await plugin.initialize()
        tools = await plugin.get_tools()

        assert len(tools) == 1
        assert tools[0].name == "obsidian_save_file"

    def test_extract_title_from_frontmatter(self, plugin):
        """Test extracting title from YAML frontmatter."""
        content = """---
title: My Test Title
date: 2024-01-01
---

# Content starts here
"""
        title = plugin._extract_title_from_markdown(content)
        assert title == "My Test Title"

    def test_extract_title_from_h1(self, plugin):
        """Test extracting title from H1 heading."""
        content = """# My H1 Title

Some content here
"""
        title = plugin._extract_title_from_markdown(content)
        assert title == "My H1 Title"

    def test_sanitize_filename(self, plugin):
        """Test filename sanitization."""
        assert plugin._sanitize_filename("test/file:name") == "test_file_name"
        assert plugin._sanitize_filename("  test  ") == "test"
        assert len(plugin._sanitize_filename("a" * 300)) <= 200

    @pytest.mark.asyncio
    async def test_save_file_to_nonexistent_vault(self, plugin):
        """Test saving to non-existent vault returns error."""
        await plugin.initialize()
        result = await plugin.execute_tool(
            "obsidian_save_file",
            content="# Test",
            vault_path="/nonexistent/vault/path",
        )
        assert result["success"] is False
        assert "does not exist" in result["error"]

    @pytest.mark.asyncio
    async def test_save_file_success(self, plugin):
        """Test successful file save."""
        await plugin.initialize()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await plugin.execute_tool(
                "obsidian_save_file",
                content="# Test Title\n\nSome content",
                vault_path=tmpdir,
                subfolder="notes",
                filename="test_file",
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["filename"] == "test_file.md"
            assert result["data"]["title"] == "Test Title"

            # Verify file was created
            file_path = Path(tmpdir) / "notes" / "test_file.md"
            assert file_path.exists()
            assert file_path.read_text() == "# Test Title\n\nSome content"


class TestPublishersPlugin:
    """Test PublishersPlugin functionality."""

    @pytest.fixture
    def plugin(self):
        """Create a PublishersPlugin instance."""
        return PublishersPlugin()

    def test_plugin_properties(self, plugin):
        """Test plugin metadata properties."""
        assert plugin.name == "publishers"
        assert plugin.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_tools(self, plugin):
        """Test that all expected tools are registered."""
        await plugin.initialize()
        tools = await plugin.get_tools()

        tool_names = {t.name for t in tools}
        # Should have platform tools + utility tools
        assert "publish_to_csdn" in tool_names
        assert "publish_to_juejin" in tool_names
        assert "publish_to_zhihu" in tool_names
        assert "publish_batch" in tool_names
        assert "list_platforms" in tool_names

    @pytest.mark.asyncio
    async def test_list_platforms(self, plugin):
        """Test listing available platforms."""
        await plugin.initialize()
        result = await plugin.execute_tool("list_platforms")

        assert result["success"] is True
        assert "data" in result
        platforms = result["data"]["platforms"]
        assert len(platforms) > 0

        # Check platform info structure (name field contains display name like "CSDN")
        csdn = next((p for p in platforms if p["id"] == "csdn"), None)
        assert csdn is not None
        assert "name" in csdn  # Display name like "CSDN"
        assert "url" in csdn


class TestSharedUtilities:
    """Test shared utility modules."""

    def test_progress_tracker_import(self):
        """Test progress tracker can be imported."""
        from odin.plugins.builtin.shared.progress import (
            ProgressTracker,
            ProgressStatus,
            progress_tracker,
        )

        assert progress_tracker is not None
        assert ProgressStatus.PENDING is not None

    def test_http_client_import(self):
        """Test HTTP client can be imported."""
        from odin.plugins.builtin.shared.http_client import (
            AsyncHTTPClient,
            HTTPClientError,
        )

        assert AsyncHTTPClient is not None
        assert HTTPClientError is not None

    def test_browser_import(self):
        """Test browser utilities can be imported."""
        from odin.plugins.builtin.shared.browser import (
            BrowserConfig,
            BrowserSession,
        )

        assert BrowserConfig is not None
        assert BrowserSession is not None


class TestProgressTracker:
    """Test ProgressTracker functionality."""

    def test_create_session(self):
        """Test creating a progress session."""
        from odin.plugins.builtin.shared.progress import ProgressTracker, ProgressStatus

        tracker = ProgressTracker()
        session_id = tracker.create_session(
            session_id="test-session",
            metadata={"type": "test"},
        )

        assert session_id == "test-session"
        session = tracker.get_session("test-session")
        assert session is not None
        assert session.status == ProgressStatus.PENDING
        assert session.metadata["type"] == "test"

    def test_add_event(self):
        """Test adding events to a session."""
        from odin.plugins.builtin.shared.progress import ProgressTracker

        tracker = ProgressTracker()
        tracker.create_session("test-session")
        tracker.add_event("test-session", "started", "Test started")

        session = tracker.get_session("test-session")
        assert len(session.events) == 1
        assert session.events[0].event_type == "started"
        assert session.events[0].message == "Test started"

    def test_set_status(self):
        """Test setting session status."""
        from odin.plugins.builtin.shared.progress import ProgressTracker, ProgressStatus

        tracker = ProgressTracker()
        tracker.create_session("test-session")
        tracker.set_status("test-session", ProgressStatus.RUNNING)

        session = tracker.get_session("test-session")
        assert session.status == ProgressStatus.RUNNING


class TestHTTPClient:
    """Test AsyncHTTPClient functionality."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test HTTP client initialization."""
        from odin.plugins.builtin.shared.http_client import AsyncHTTPClient

        client = AsyncHTTPClient(timeout=30)
        assert client.timeout == 30
        await client.close()

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test HTTP client as context manager."""
        from odin.plugins.builtin.shared.http_client import AsyncHTTPClient

        async with AsyncHTTPClient() as client:
            assert client is not None
