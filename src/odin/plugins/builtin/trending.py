"""Trending plugin for Odin.

This plugin provides tools for mining hot topics and trending
content from multiple sources including GitHub, Hacker News,
Reddit, and Product Hunt.

Tools:
- trending_mine_hot_topics: Mine hot tech topics from multiple sources
- trending_get_random_topic: Get a random trending topic
- trending_mark_topic_published: Mark a topic as published
- trending_mark_topic_in_progress: Mark a topic as in progress
- trending_search_topics: Search topics with filters
- trending_get_statistics: Get topic statistics
"""

from __future__ import annotations

import asyncio
import hashlib
import random
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import Field

from odin.decorators import tool
from odin.plugins import DecoratorPlugin, PluginConfig
from odin.utils.http_client import AsyncHTTPClient


class TopicSource(str, Enum):
    """Topic source identifiers."""
    GITHUB_TRENDING = "github_trending"
    HACKER_NEWS = "hacker_news"
    REDDIT_PROGRAMMING = "reddit_programming"
    PRODUCT_HUNT = "product_hunt"


class TopicStatus(str, Enum):
    """Topic status values."""
    DISCOVERED = "discovered"
    IN_PROGRESS = "in_progress"
    PUBLISHED = "published"


class TrendingPlugin(DecoratorPlugin):
    """Hot topics mining and management plugin.

    This plugin provides tools for discovering trending tech topics
    from multiple sources and managing their publication status.
    """

    # Tech keywords for filtering
    TECH_KEYWORDS = {
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "llm", "gpt", "claude", "openai", "anthropic", "chatgpt",
        "python", "javascript", "typescript", "rust", "go", "java",
        "react", "vue", "angular", "node.js", "docker", "kubernetes",
        "blockchain", "web3", "crypto", "nft", "defi",
        "cloud", "aws", "azure", "gcp", "serverless",
        "devops", "ci/cd", "github", "gitlab", "vscode",
        "api", "rest", "graphql", "microservices",
        "database", "sql", "nosql", "redis", "mongodb",
        "framework", "library", "open source", "startup",
        "tech", "technology", "software", "development",
        "programming", "coding", "developer", "engineering",
    }

    def __init__(self, config: PluginConfig | None = None) -> None:
        super().__init__(config)
        self._http_client: AsyncHTTPClient | None = None
        # In-memory topic storage (would use database in production)
        self._topics: dict[str, dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return "trending"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Hot topics mining from GitHub, Hacker News, Reddit, and Product Hunt"

    async def initialize(self) -> None:
        """Initialize plugin."""
        await super().initialize()
        self._http_client = AsyncHTTPClient(timeout=30)

    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self._http_client:
            await self._http_client.close()
        await super().shutdown()

    def _generate_topic_id(self, title: str, source: str) -> str:
        """Generate unique topic ID from title and source."""
        content = f"{source}:{title}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _is_tech_related(self, text: str) -> bool:
        """Check if text contains tech-related keywords."""
        if not text:
            return False
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.TECH_KEYWORDS)

    def _calculate_score(self, data: dict[str, Any], source: str) -> int:
        """Calculate trending score based on source-specific metrics."""
        score = 0

        if source == TopicSource.GITHUB_TRENDING:
            score += data.get("stars", 0) // 100
            score += data.get("stars_today", 0) * 10

        elif source == TopicSource.HACKER_NEWS:
            score += data.get("score", 0)
            score += data.get("descendants", 0) // 10

        elif source == TopicSource.REDDIT_PROGRAMMING:
            score += data.get("score", 0) // 10
            score += data.get("num_comments", 0)

        elif source == TopicSource.PRODUCT_HUNT:
            score += data.get("votes_count", 0)
            score += data.get("comments_count", 0) * 2

        return score

    async def _mine_github_trending(self) -> list[dict[str, Any]]:
        """Mine trending repos from GitHub."""
        topics = []

        try:
            url = "https://gh-trending-api.de.a.run.app/repositories"
            response = await self._http_client.get(url, params={"since": "daily"})

            if response.get("ok"):
                repos = response.get("json", [])
                for repo in repos[:15]:
                    description = repo.get("description", "")
                    if self._is_tech_related(description) or self._is_tech_related(repo.get("language", "")):
                        topics.append({
                            "title": f"{repo.get('name', '')} - {description[:100]}",
                            "short_title": repo.get("name", ""),
                            "description": description,
                            "source": TopicSource.GITHUB_TRENDING,
                            "source_url": repo.get("url", ""),
                            "trending_score": self._calculate_score({
                                "stars": repo.get("stars", 0),
                                "stars_today": repo.get("starsToday", repo.get("currentPeriodStars", 0)),
                            }, TopicSource.GITHUB_TRENDING),
                            "metadata": {
                                "language": repo.get("language"),
                                "stars": repo.get("stars", 0),
                                "forks": repo.get("forks", 0),
                            },
                        })
        except Exception:
            pass

        return topics

    async def _mine_hacker_news(self) -> list[dict[str, Any]]:
        """Mine top stories from Hacker News."""
        topics = []

        try:
            # Get top stories
            url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            response = await self._http_client.get(url)

            if response.get("ok"):
                story_ids = response.get("json", [])[:30]

                # Fetch story details concurrently
                async def fetch_story(story_id: int) -> dict[str, Any] | None:
                    try:
                        story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                        resp = await self._http_client.get(story_url)
                        if resp.get("ok"):
                            return resp.get("json")
                    except Exception:
                        pass
                    return None

                stories = await asyncio.gather(*[fetch_story(sid) for sid in story_ids])

                for story in stories:
                    if not story:
                        continue

                    title = story.get("title", "")
                    if self._is_tech_related(title):
                        topics.append({
                            "title": title,
                            "short_title": title[:50],
                            "description": title,
                            "source": TopicSource.HACKER_NEWS,
                            "source_url": story.get("url", f"https://news.ycombinator.com/item?id={story.get('id')}"),
                            "trending_score": self._calculate_score({
                                "score": story.get("score", 0),
                                "descendants": story.get("descendants", 0),
                            }, TopicSource.HACKER_NEWS),
                            "metadata": {
                                "score": story.get("score", 0),
                                "comments": story.get("descendants", 0),
                                "by": story.get("by"),
                            },
                        })
        except Exception:
            pass

        return topics[:15]

    async def _mine_reddit_programming(self) -> list[dict[str, Any]]:
        """Mine hot posts from programming subreddits."""
        topics = []
        subreddits = ["programming", "python", "javascript", "rust", "golang"]

        try:
            for subreddit in subreddits:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json"
                headers = {"User-Agent": "Odin/1.0"}

                try:
                    response = await self._http_client.get(url, headers=headers)
                    if response.get("ok"):
                        data = response.get("json", {})
                        posts = data.get("data", {}).get("children", [])

                        for post in posts[:5]:
                            post_data = post.get("data", {})
                            title = post_data.get("title", "")

                            if self._is_tech_related(title):
                                topics.append({
                                    "title": title,
                                    "short_title": title[:50],
                                    "description": post_data.get("selftext", "")[:200] or title,
                                    "source": TopicSource.REDDIT_PROGRAMMING,
                                    "source_url": f"https://reddit.com{post_data.get('permalink', '')}",
                                    "trending_score": self._calculate_score({
                                        "score": post_data.get("score", 0),
                                        "num_comments": post_data.get("num_comments", 0),
                                    }, TopicSource.REDDIT_PROGRAMMING),
                                    "metadata": {
                                        "subreddit": subreddit,
                                        "score": post_data.get("score", 0),
                                        "comments": post_data.get("num_comments", 0),
                                    },
                                })
                except Exception:
                    continue

        except Exception:
            pass

        return topics[:15]

    async def _mine_product_hunt(self) -> list[dict[str, Any]]:
        """Mine trending products from Product Hunt."""
        topics = []

        try:
            # Using unofficial API endpoint
            url = "https://api.producthunt.com/v2/api/graphql"
            # Note: This would need authentication for production use
            # For now, we skip this source if not configured
        except Exception:
            pass

        return topics

    @tool(description="Mine hot tech topics from multiple sources")
    async def trending_mine_hot_topics(
        self,
        sources: Annotated[
            list[str] | None,
            Field(description="Sources to mine from (github_trending, hacker_news, reddit_programming, product_hunt)")
        ] = None,
        limit: Annotated[
            int,
            Field(description="Maximum number of topics to return", ge=1, le=50)
        ] = 10,
        exclude_published: Annotated[
            bool,
            Field(description="Exclude already published topics")
        ] = True,
    ) -> dict[str, Any]:
        """Mine hot tech topics from multiple sources.

        Aggregates trending content from GitHub, Hacker News, Reddit,
        and Product Hunt, filters for tech relevance, and ranks by
        engagement metrics.
        """
        try:
            if not self._http_client:
                await self.initialize()

            # Determine which sources to mine
            source_funcs = {
                "github_trending": self._mine_github_trending,
                "hacker_news": self._mine_hacker_news,
                "reddit_programming": self._mine_reddit_programming,
            }

            if sources is None:
                sources = list(source_funcs.keys())

            # Mine from all sources concurrently
            tasks = []
            for source in sources:
                if source in source_funcs:
                    tasks.append(source_funcs[source]())

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Aggregate topics
            all_topics = []
            source_counts = {}

            for result in results:
                if isinstance(result, list):
                    for topic in result:
                        source = topic.get("source", "unknown")
                        source_counts[source] = source_counts.get(source, 0) + 1
                        all_topics.append(topic)

            # Deduplicate by content hash
            seen_hashes = set()
            unique_topics = []
            for topic in all_topics:
                content_hash = self._generate_topic_id(
                    topic.get("title", ""),
                    topic.get("source", ""),
                )
                if content_hash not in seen_hashes:
                    seen_hashes.add(content_hash)
                    topic["content_hash"] = content_hash
                    unique_topics.append(topic)

            # Filter published if requested
            if exclude_published:
                unique_topics = [
                    t for t in unique_topics
                    if t.get("content_hash") not in self._topics
                    or self._topics[t["content_hash"]].get("status") != TopicStatus.PUBLISHED
                ]

            # Sort by score and limit
            unique_topics.sort(
                key=lambda x: x.get("trending_score", 0),
                reverse=True,
            )
            final_topics = unique_topics[:limit]

            # Save to internal storage
            for topic in final_topics:
                topic_id = topic.get("content_hash")
                if topic_id and topic_id not in self._topics:
                    self._topics[topic_id] = {
                        **topic,
                        "status": TopicStatus.DISCOVERED,
                        "discovered_at": datetime.utcnow().isoformat(),
                    }

            return {
                "success": True,
                "data": {
                    "topics": final_topics,
                    "count": len(final_topics),
                    "total_discovered": len(all_topics),
                    "source_distribution": source_counts,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Get a random trending topic")
    async def trending_get_random_topic(
        self,
        exclude_published: Annotated[
            bool,
            Field(description="Exclude already published topics")
        ] = True,
    ) -> dict[str, Any]:
        """Get a random trending topic from discovered topics.

        Weighted towards higher-scoring topics.
        """
        try:
            # Filter topics
            available = list(self._topics.values())

            if exclude_published:
                available = [
                    t for t in available
                    if t.get("status") != TopicStatus.PUBLISHED
                ]

            if not available:
                # Try to mine new topics
                mine_result = await self.trending_mine_hot_topics(limit=20)
                if mine_result.get("success"):
                    available = mine_result.get("data", {}).get("topics", [])

            if not available:
                return {
                    "success": True,
                    "data": None,
                    "message": "No topics available",
                }

            # Sort by score and pick from top 20
            available.sort(key=lambda x: x.get("trending_score", 0), reverse=True)
            top_topics = available[:20]

            selected = random.choice(top_topics)

            return {
                "success": True,
                "data": selected,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Mark a topic as published")
    async def trending_mark_topic_published(
        self,
        topic_id: Annotated[
            int | None,
            Field(description="Topic ID (database ID)")
        ] = None,
        content_hash: Annotated[
            str | None,
            Field(description="Content hash of the topic")
        ] = None,
        publication_platform: Annotated[
            str,
            Field(description="Platform where topic was published")
        ] = "default",
        publication_url: Annotated[
            str | None,
            Field(description="URL of the published content")
        ] = None,
        notes: Annotated[
            str | None,
            Field(description="Publication notes")
        ] = None,
    ) -> dict[str, Any]:
        """Mark a topic as published.

        Updates the topic status to prevent re-selection.
        """
        try:
            if not content_hash:
                return {
                    "success": False,
                    "error": "content_hash is required",
                }

            if content_hash not in self._topics:
                return {
                    "success": False,
                    "error": f"Topic not found: {content_hash}",
                }

            self._topics[content_hash].update({
                "status": TopicStatus.PUBLISHED,
                "published_at": datetime.utcnow().isoformat(),
                "publication_platform": publication_platform,
                "publication_url": publication_url,
                "notes": notes,
            })

            return {
                "success": True,
                "data": {
                    "content_hash": content_hash,
                    "status": TopicStatus.PUBLISHED,
                    "message": "Topic marked as published",
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Mark a topic as in progress")
    async def trending_mark_topic_in_progress(
        self,
        topic_id: Annotated[
            int | None,
            Field(description="Topic ID")
        ] = None,
        content_hash: Annotated[
            str | None,
            Field(description="Content hash of the topic")
        ] = None,
        notes: Annotated[
            str | None,
            Field(description="Progress notes")
        ] = None,
    ) -> dict[str, Any]:
        """Mark a topic as in progress.

        Indicates the topic is being worked on.
        """
        try:
            if not content_hash:
                return {
                    "success": False,
                    "error": "content_hash is required",
                }

            if content_hash not in self._topics:
                return {
                    "success": False,
                    "error": f"Topic not found: {content_hash}",
                }

            self._topics[content_hash].update({
                "status": TopicStatus.IN_PROGRESS,
                "started_at": datetime.utcnow().isoformat(),
                "notes": notes,
            })

            return {
                "success": True,
                "data": {
                    "content_hash": content_hash,
                    "status": TopicStatus.IN_PROGRESS,
                    "message": "Topic marked as in progress",
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Search topics with filters")
    async def trending_search_topics(
        self,
        keyword: Annotated[
            str | None,
            Field(description="Search keyword")
        ] = None,
        category: Annotated[
            str | None,
            Field(description="Filter by category")
        ] = None,
        source: Annotated[
            str | None,
            Field(description="Filter by source (github_trending, hacker_news, etc.)")
        ] = None,
        status: Annotated[
            str | None,
            Field(description="Filter by status (discovered, in_progress, published)")
        ] = None,
        limit: Annotated[
            int,
            Field(description="Maximum results", ge=1, le=100)
        ] = 20,
    ) -> dict[str, Any]:
        """Search and filter topics.

        Allows searching through discovered topics with various filters.
        """
        try:
            results = list(self._topics.values())

            # Apply filters
            if keyword:
                keyword_lower = keyword.lower()
                results = [
                    t for t in results
                    if keyword_lower in t.get("title", "").lower()
                    or keyword_lower in t.get("description", "").lower()
                ]

            if source:
                results = [
                    t for t in results
                    if t.get("source") == source
                ]

            if status:
                results = [
                    t for t in results
                    if t.get("status") == status
                ]

            # Sort by score
            results.sort(key=lambda x: x.get("trending_score", 0), reverse=True)
            results = results[:limit]

            return {
                "success": True,
                "data": {
                    "topics": results,
                    "count": len(results),
                    "filters": {
                        "keyword": keyword,
                        "category": category,
                        "source": source,
                        "status": status,
                    },
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Get topic statistics")
    async def trending_get_statistics(self) -> dict[str, Any]:
        """Get statistics about discovered topics.

        Returns counts by source, status, and other metrics.
        """
        try:
            topics = list(self._topics.values())

            # Count by source
            by_source = {}
            for t in topics:
                source = t.get("source", "unknown")
                by_source[source] = by_source.get(source, 0) + 1

            # Count by status
            by_status = {}
            for t in topics:
                status = t.get("status", TopicStatus.DISCOVERED)
                by_status[status] = by_status.get(status, 0) + 1

            # Average score
            scores = [t.get("trending_score", 0) for t in topics]
            avg_score = sum(scores) / len(scores) if scores else 0

            return {
                "success": True,
                "data": {
                    "total_topics": len(topics),
                    "by_source": by_source,
                    "by_status": by_status,
                    "average_score": round(avg_score, 2),
                    "published_count": by_status.get(TopicStatus.PUBLISHED, 0),
                    "in_progress_count": by_status.get(TopicStatus.IN_PROGRESS, 0),
                    "available_count": by_status.get(TopicStatus.DISCOVERED, 0),
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
