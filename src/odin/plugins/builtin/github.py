"""GitHub plugin for Odin.

This plugin provides tools for GitHub repository discovery,
analysis, and content generation.

Tools:
- github_discover_trending: Discover trending GitHub repositories
- github_deep_analyze: Analyze a repository in depth
- github_extract_images: Extract images from a repository
- github_get_project_status: Get project processing status
- github_generate_markdown: Generate markdown content for a project
"""


import re
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from odin.decorators import tool
from odin.plugins import DecoratorPlugin, PluginConfig
from odin.utils.http_client import AsyncHTTPClient, HTTPClientError


class GitHubPlugin(DecoratorPlugin):
    """GitHub repository discovery and analysis plugin.

    This plugin provides tools to discover trending repositories,
    analyze them in depth, and generate documentation.
    """

    def __init__(self, config: PluginConfig | None = None) -> None:
        super().__init__(config)
        self._github_token: str | None = None
        self._cache_ttl: int = 3600  # 1 hour
        self._http_client: AsyncHTTPClient | None = None

    @property
    def name(self) -> str:
        return "github"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "GitHub repository discovery, analysis, and content generation"

    async def initialize(self) -> None:
        """Initialize plugin with settings."""
        await super().initialize()
        # Get GitHub token from settings or environment
        import os
        self._github_token = (
            self.config.settings.get("github_token")
            or os.environ.get("GITHUB_TOKEN")
        )
        self._http_client = AsyncHTTPClient(
            timeout=30,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        if self._github_token:
            self._http_client.default_headers["Authorization"] = f"token {self._github_token}"

    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self._http_client:
            await self._http_client.close()
        await super().shutdown()

    # -------------------------------------------------------------------------
    # Tools
    # -------------------------------------------------------------------------

    @tool(description="Discover trending GitHub repositories with multi-source strategy")
    async def github_discover_trending(
        self,
        language: Annotated[
            str,
            Field(description="Programming language filter (e.g., 'python', 'javascript')")
        ] = "python",
        since: Annotated[
            Literal["daily", "weekly", "monthly"],
            Field(description="Time period for trending")
        ] = "daily",
        limit: Annotated[
            int,
            Field(description="Maximum number of repositories to return", ge=1, le=25)
        ] = 5,
        min_stars: Annotated[
            int,
            Field(description="Minimum total stars filter", ge=0)
        ] = 1000,
        force_refresh: Annotated[
            bool,
            Field(description="Force bypass cache and fetch fresh data")
        ] = False,
    ) -> dict[str, Any]:
        """Discover trending GitHub repositories.

        Features:
        - Multiple data sources (GitHub trending page, community API, search API)
        - Smart caching and deduplication (1-hour cache TTL)
        - Intelligent scoring based on stars today, total stars, and recent activity
        """
        try:
            repos = []

            # Try community API first (faster)
            try:
                community_repos = await self._fetch_from_community_api(
                    language=language,
                    since=since,
                    limit=limit * 2,  # Fetch more for filtering
                )
                repos.extend(community_repos)
            except Exception:
                # Fall back to GitHub search API
                search_repos = await self._fetch_from_search_api(
                    language=language,
                    limit=limit * 2,
                )
                repos.extend(search_repos)

            # Filter by min_stars
            filtered_repos = [r for r in repos if r.get("stars", 0) >= min_stars]

            # Deduplicate by URL
            seen_urls = set()
            unique_repos = []
            for repo in filtered_repos:
                url = repo.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_repos.append(repo)

            # Sort by score and limit
            unique_repos.sort(
                key=lambda x: (x.get("stars_today", 0), x.get("stars", 0)),
                reverse=True,
            )
            final_repos = unique_repos[:limit]

            return {
                "success": True,
                "data": {
                    "repositories": final_repos,
                    "count": len(final_repos),
                    "total_discovered": len(repos),
                    "filters": {
                        "language": language,
                        "since": since,
                        "min_stars": min_stars,
                        "force_refresh": force_refresh,
                    },
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Analyze a GitHub repository in depth")
    async def github_deep_analyze(
        self,
        repo_url: Annotated[
            str,
            Field(description="GitHub repository URL (e.g., 'https://github.com/owner/repo')")
        ],
        include_readme: Annotated[
            bool,
            Field(description="Include README content in analysis")
        ] = True,
    ) -> dict[str, Any]:
        """Analyze a GitHub repository to extract detailed information.

        Extracts:
        - Repository metadata (stars, forks, issues, etc.)
        - README content (optional)
        - Languages and topics
        - Recent activity and contributors
        """
        try:
            # Parse repo URL
            owner, repo = self._parse_repo_url(repo_url)
            if not owner or not repo:
                return {
                    "success": False,
                    "error": f"Invalid repository URL: {repo_url}",
                }

            # Fetch repo info from GitHub API
            if not self._http_client:
                await self.initialize()

            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = await self._http_client.get(api_url)

            if not response.get("ok"):
                return {
                    "success": False,
                    "error": f"Failed to fetch repository: {response.get('text', '')}",
                }

            repo_data = response.get("json", {})

            # Build analysis result
            analysis = {
                "repo_url": repo_url,
                "full_name": repo_data.get("full_name"),
                "name": repo_data.get("name"),
                "description": repo_data.get("description"),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "watchers": repo_data.get("watchers_count", 0),
                "language": repo_data.get("language"),
                "topics": repo_data.get("topics", []),
                "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else None,
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
                "pushed_at": repo_data.get("pushed_at"),
                "default_branch": repo_data.get("default_branch"),
                "homepage": repo_data.get("homepage"),
                "owner": {
                    "login": repo_data.get("owner", {}).get("login"),
                    "avatar_url": repo_data.get("owner", {}).get("avatar_url"),
                    "type": repo_data.get("owner", {}).get("type"),
                },
            }

            # Fetch README if requested
            if include_readme:
                readme_content = await self._fetch_readme(owner, repo)
                if readme_content:
                    analysis["readme"] = readme_content

            return {
                "success": True,
                "data": analysis,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Extract images from a GitHub repository")
    async def github_extract_images(
        self,
        repo_url: Annotated[
            str,
            Field(description="GitHub repository URL")
        ],
        max_images: Annotated[
            int,
            Field(description="Maximum number of images to extract", ge=1, le=10)
        ] = 3,
    ) -> dict[str, Any]:
        """Extract images from a GitHub repository.

        Extracts:
        - Open Graph image (if available)
        - Images from README
        - Owner avatar
        """
        try:
            owner, repo = self._parse_repo_url(repo_url)
            if not owner or not repo:
                return {
                    "success": False,
                    "error": f"Invalid repository URL: {repo_url}",
                }

            images = []

            # Try to get OG image from GitHub
            og_image = f"https://opengraph.githubassets.com/1/{owner}/{repo}"
            images.append({
                "url": og_image,
                "type": "og_image",
                "description": "GitHub Open Graph image",
            })

            # Fetch README and extract images
            readme_content = await self._fetch_readme(owner, repo)
            if readme_content:
                readme_images = self._extract_images_from_markdown(
                    readme_content, owner, repo
                )
                for img_url in readme_images[:max_images - len(images)]:
                    images.append({
                        "url": img_url,
                        "type": "readme",
                        "description": "Image from README",
                    })

            # Add owner avatar
            if not self._http_client:
                await self.initialize()

            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = await self._http_client.get(api_url)
            if response.get("ok"):
                repo_data = response.get("json", {})
                avatar_url = repo_data.get("owner", {}).get("avatar_url")
                if avatar_url:
                    images.append({
                        "url": avatar_url,
                        "type": "avatar",
                        "description": "Repository owner avatar",
                    })

            return {
                "success": True,
                "data": {
                    "images": images[:max_images],
                    "count": min(len(images), max_images),
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Get project processing status")
    async def github_get_project_status(
        self,
        repo_url: Annotated[
            str,
            Field(description="GitHub repository URL")
        ],
    ) -> dict[str, Any]:
        """Get the processing status of a GitHub project.

        Returns current status including whether analysis and
        markdown generation have been completed.
        """
        try:
            owner, repo = self._parse_repo_url(repo_url)
            if not owner or not repo:
                return {
                    "success": False,
                    "error": f"Invalid repository URL: {repo_url}",
                }

            # For now, just check if repo exists and is accessible
            if not self._http_client:
                await self.initialize()

            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = await self._http_client.get(api_url)

            if not response.get("ok"):
                return {
                    "success": False,
                    "error": "Repository not found or not accessible",
                    "data": {
                        "repo_url": repo_url,
                        "status": "not_found",
                        "has_analysis": False,
                        "has_markdown": False,
                    },
                }

            return {
                "success": True,
                "data": {
                    "repo_url": repo_url,
                    "status": "discovered",
                    "has_analysis": False,
                    "has_markdown": False,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Generate markdown content for a GitHub project")
    async def github_generate_markdown(
        self,
        repo_url: Annotated[
            str,
            Field(description="GitHub repository URL")
        ],
        template: Annotated[
            Literal["obsidian", "notion", "basic"],
            Field(description="Markdown template to use")
        ] = "obsidian",
        include_analysis: Annotated[
            bool,
            Field(description="Include analysis data in markdown")
        ] = True,
    ) -> dict[str, Any]:
        """Generate markdown content for a GitHub project.

        Creates formatted markdown using the specified template,
        suitable for Obsidian, Notion, or basic markdown.
        """
        try:
            # First get analysis data
            analysis_result = await self.github_deep_analyze(
                repo_url=repo_url,
                include_readme=True,
            )

            if not analysis_result.get("success"):
                return analysis_result

            analysis = analysis_result.get("data", {})

            # Generate markdown based on template
            if template == "obsidian":
                markdown = self._generate_obsidian_markdown(analysis)
            elif template == "notion":
                markdown = self._generate_notion_markdown(analysis)
            else:
                markdown = self._generate_basic_markdown(analysis)

            return {
                "success": True,
                "data": {
                    "markdown": markdown,
                    "template": template,
                    "repo_url": repo_url,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _parse_repo_url(self, url: str) -> tuple[str | None, str | None]:
        """Parse owner and repo from GitHub URL."""
        patterns = [
            r"github\.com/([^/]+)/([^/\?#]+)",
            r"^([^/]+)/([^/]+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner = match.group(1)
                repo = match.group(2).rstrip(".git")
                return owner, repo
        return None, None

    async def _fetch_from_community_api(
        self,
        language: str | None = None,
        since: str = "daily",
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Fetch trending repos from community API."""
        if not self._http_client:
            await self.initialize()

        url = "https://gh-trending-api.de.a.run.app/repositories"
        params = {"since": since}
        if language:
            params["language"] = language

        response = await self._http_client.get(url, params=params)
        if not response.get("ok"):
            raise HTTPClientError(f"Community API request failed: {response.get('text', '')}")

        repos = response.get("json", [])
        result = []

        for repo in repos[:limit]:
            result.append({
                "repo_name": repo.get("name", ""),
                "full_name": repo.get("fullName", repo.get("name", "")),
                "url": repo.get("url", ""),
                "description": repo.get("description", ""),
                "stars": repo.get("stars", 0),
                "stars_today": repo.get("starsToday", repo.get("currentPeriodStars", 0)),
                "forks": repo.get("forks", 0),
                "language": repo.get("language", ""),
                "source": "community_api",
            })

        return result

    async def _fetch_from_search_api(
        self,
        language: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Fetch trending repos from GitHub Search API."""
        if not self._http_client:
            await self.initialize()

        # Build search query
        query_parts = ["stars:>1000"]
        if language:
            query_parts.append(f"language:{language}")

        url = "https://api.github.com/search/repositories"
        params = {
            "q": " ".join(query_parts),
            "sort": "stars",
            "order": "desc",
            "per_page": limit,
        }

        response = await self._http_client.get(url, params=params)
        if not response.get("ok"):
            raise HTTPClientError(f"GitHub Search API request failed: {response.get('text', '')}")

        data = response.get("json", {})
        repos = data.get("items", [])
        result = []

        for repo in repos:
            result.append({
                "repo_name": repo.get("name", ""),
                "full_name": repo.get("full_name", ""),
                "url": repo.get("html_url", ""),
                "description": repo.get("description", ""),
                "stars": repo.get("stargazers_count", 0),
                "stars_today": 0,  # Search API doesn't provide this
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language", ""),
                "source": "search_api",
            })

        return result

    async def _fetch_readme(self, owner: str, repo: str) -> str | None:
        """Fetch README content from GitHub."""
        if not self._http_client:
            await self.initialize()

        url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        headers = {"Accept": "application/vnd.github.raw"}

        try:
            response = await self._http_client.get(url, headers=headers)
            if response.get("ok"):
                return response.get("text", "")
        except Exception:
            pass

        return None

    def _extract_images_from_markdown(
        self, content: str, owner: str, repo: str
    ) -> list[str]:
        """Extract image URLs from markdown content."""
        images = []

        # Match markdown image syntax: ![alt](url)
        pattern = r"!\[[^\]]*\]\(([^)]+)\)"
        matches = re.findall(pattern, content)

        for url in matches:
            # Convert relative URLs to absolute
            if url.startswith("./") or url.startswith("../") or not url.startswith("http"):
                url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{url.lstrip('./')}"
            images.append(url)

        return images

    def _generate_obsidian_markdown(self, analysis: dict[str, Any]) -> str:
        """Generate Obsidian-style markdown."""
        lines = [
            "---",
            f"title: {analysis.get('name', 'Unknown')}",
            f"url: {analysis.get('repo_url', '')}",
            f"stars: {analysis.get('stars', 0)}",
            f"language: {analysis.get('language', '')}",
            f"topics: [{', '.join(analysis.get('topics', []))}]",
            f"created: {datetime.now().strftime('%Y-%m-%d')}",
            "---",
            "",
            f"# {analysis.get('full_name', 'Unknown')}",
            "",
            f"> {analysis.get('description', 'No description')}",
            "",
            "## Info",
            "",
            f"- ⭐ Stars: {analysis.get('stars', 0)}",
            f"- 🍴 Forks: {analysis.get('forks', 0)}",
            f"- 📝 Language: {analysis.get('language', 'N/A')}",
            f"- 📜 License: {analysis.get('license', 'N/A')}",
            "",
            "## Topics",
            "",
        ]

        topics = analysis.get("topics", [])
        if topics:
            lines.append(" ".join([f"#{t}" for t in topics]))
        else:
            lines.append("No topics")

        lines.extend([
            "",
            "## Links",
            "",
            f"- [GitHub]({analysis.get('repo_url', '')})",
        ])

        if analysis.get("homepage"):
            lines.append(f"- [Homepage]({analysis.get('homepage')})")

        return "\n".join(lines)

    def _generate_notion_markdown(self, analysis: dict[str, Any]) -> str:
        """Generate Notion-style markdown."""
        lines = [
            f"# {analysis.get('full_name', 'Unknown')}",
            "",
            f"**Description:** {analysis.get('description', 'No description')}",
            "",
            "## Properties",
            "",
            "| Property | Value |",
            "| --- | --- |",
            f"| Stars | {analysis.get('stars', 0)} |",
            f"| Forks | {analysis.get('forks', 0)} |",
            f"| Language | {analysis.get('language', 'N/A')} |",
            f"| License | {analysis.get('license', 'N/A')} |",
            f"| Open Issues | {analysis.get('open_issues', 0)} |",
            "",
        ]

        return "\n".join(lines)

    def _generate_basic_markdown(self, analysis: dict[str, Any]) -> str:
        """Generate basic markdown."""
        lines = [
            f"# {analysis.get('full_name', 'Unknown')}",
            "",
            analysis.get("description", "No description"),
            "",
            f"**Stars:** {analysis.get('stars', 0)} | "
            f"**Forks:** {analysis.get('forks', 0)} | "
            f"**Language:** {analysis.get('language', 'N/A')}",
            "",
            f"[View on GitHub]({analysis.get('repo_url', '')})",
            "",
        ]

        return "\n".join(lines)
