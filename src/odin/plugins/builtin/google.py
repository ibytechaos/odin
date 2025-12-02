"""Google plugin for Odin.

This plugin provides tools for Google services integration,
primarily Google Custom Search API for image search.

Tools:
- google_image_search: Search for images using Google Custom Search API
"""


import asyncio
import os
from typing import Annotated, Any, Literal

from pydantic import Field

from odin.decorators import tool
from odin.plugins import DecoratorPlugin, PluginConfig
from odin.utils.http_client import AsyncHTTPClient


class GooglePlugin(DecoratorPlugin):
    """Google services integration plugin.

    This plugin provides tools for interacting with Google services,
    including the Custom Search API for image search.

    Requires:
    - GOOGLE_CUSTOM_SEARCH_API_KEY environment variable
    - GOOGLE_CUSTOM_SEARCH_ENGINE_ID environment variable
    """

    SEARCH_API_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, config: PluginConfig | None = None) -> None:
        super().__init__(config)
        self._api_key: str | None = None
        self._search_engine_id: str | None = None
        self._http_client: AsyncHTTPClient | None = None

    @property
    def name(self) -> str:
        return "google"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Google services integration (Custom Search API)"

    async def initialize(self) -> None:
        """Initialize plugin with API credentials."""
        await super().initialize()
        self._api_key = (
            self.config.settings.get("google_api_key")
            or os.environ.get("GOOGLE_CUSTOM_SEARCH_API_KEY")
        )
        self._search_engine_id = (
            self.config.settings.get("google_search_engine_id")
            or os.environ.get("GOOGLE_CUSTOM_SEARCH_ENGINE_ID")
        )
        self._http_client = AsyncHTTPClient(timeout=30)

    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self._http_client:
            await self._http_client.close()
        await super().shutdown()

    def _validate_credentials(self) -> tuple[bool, str | None]:
        """Validate API credentials are configured."""
        if not self._api_key:
            return False, "Google Custom Search API key not configured"
        if not self._search_engine_id:
            return False, "Google Custom Search Engine ID not configured"
        return True, None

    @tool(description="Search for images using Google Custom Search API")
    async def google_image_search(
        self,
        queries: Annotated[
            list[str],
            Field(description="List of search queries")
        ],
        num_images_per_query: Annotated[
            int,
            Field(description="Number of images per query", ge=1, le=10)
        ] = 5,
        safe_search: Annotated[
            Literal["active", "moderate", "off"],
            Field(description="Safe search setting")
        ] = "active",
        image_size: Annotated[
            Literal["icon", "small", "medium", "large", "xlarge", "xxlarge", "huge"],
            Field(description="Image size filter")
        ] = "large",
    ) -> dict[str, Any]:
        """Search for images using Google Custom Search API.

        Performs batch image search for multiple queries and returns
        filtered, high-quality results.

        Args:
            queries: List of search terms
            num_images_per_query: Max images per query (1-10)
            safe_search: Content filtering level
            image_size: Minimum image size

        Returns:
            Search results with images grouped by query
        """
        try:
            # Validate credentials
            valid, error = self._validate_credentials()
            if not valid:
                return {
                    "success": False,
                    "error": error,
                }

            if not self._http_client:
                await self.initialize()

            # Size mapping for API
            size_mapping = {
                "icon": "ICON",
                "small": "SMALL",
                "medium": "MEDIUM",
                "large": "LARGE",
                "xlarge": "XLARGE",
                "xxlarge": "XXLARGE",
                "huge": "HUGE",
            }

            results = {}
            total_images = 0
            successful_queries = 0

            # Process queries with rate limiting
            semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests

            async def search_single(query: str) -> tuple[str, list[dict[str, Any]]]:
                async with semaphore:
                    try:
                        params = {
                            "key": self._api_key,
                            "cx": self._search_engine_id,
                            "q": query,
                            "searchType": "image",
                            "num": num_images_per_query,
                            "safe": safe_search,
                        }

                        # Add size filter
                        if image_size in size_mapping:
                            params["imgSize"] = size_mapping[image_size]

                        response = await self._http_client.get(
                            self.SEARCH_API_URL,
                            params=params,
                        )

                        if not response.get("ok"):
                            return query, []

                        data = response.get("json", {})
                        items = data.get("items", [])

                        # Process and filter results
                        images = []
                        for item in items:
                            image_info = item.get("image", {})
                            width = image_info.get("width", 0)
                            height = image_info.get("height", 0)
                            byte_size = image_info.get("byteSize", 0)

                            # Quality filters
                            if width > 0 and height > 0 and (width < 300 or height < 300):
                                continue
                            if 0 < byte_size < 10240:  # Skip < 10KB
                                continue

                            images.append({
                                "title": item.get("title", ""),
                                "url": item.get("link", ""),
                                "display_link": item.get("displayLink", ""),
                                "snippet": item.get("snippet", ""),
                                "thumbnail_url": image_info.get("thumbnailLink", ""),
                                "width": width,
                                "height": height,
                                "file_format": image_info.get("fileFormat", ""),
                                "byte_size": byte_size,
                                "context_url": image_info.get("contextLink", ""),
                            })

                        return query, images

                    except Exception:
                        return query, []

            # Execute all searches
            tasks = [search_single(q) for q in queries[:10]]  # Limit to 10 queries
            search_results = await asyncio.gather(*tasks)

            for query, images in search_results:
                results[query] = {
                    "query": query,
                    "image_count": len(images),
                    "images": images,
                }
                if images:
                    successful_queries += 1
                    total_images += len(images)

            return {
                "success": True,
                "data": {
                    "total_queries": len(queries),
                    "successful_queries": successful_queries,
                    "total_images": total_images,
                    "queries": results,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
