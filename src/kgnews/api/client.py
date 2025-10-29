"""API client for Kagi News."""

import logging
from datetime import datetime

import httpx

from kgnews.models import Category, Story

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors."""

    pass


class APITimeoutError(APIError):
    """Exception raised when API request times out."""

    pass


class APIResponseError(APIError):
    """Exception raised when API returns invalid or malformed response."""

    pass


class APIClient:
    """Async client for Kagi News API.

    Fetches news categories and stories from the latest batch.
    """

    BASE_URL = "https://news.kagi.com"
    TIMEOUT = 10.0  # 10 seconds

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        """Initialize API client.

        Args:
            base_url: Base URL for API (defaults to https://news.kagi.com)
            timeout: Request timeout in seconds (defaults to 10.0)
        """
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout or self.TIMEOUT

    async def get_latest_batch(self) -> dict:
        """Fetch latest batch information.

        Returns:
            Dictionary containing batch metadata including:
            - id: Batch UUID
            - createdAt: Creation timestamp
            - totalCategories: Number of categories
            - totalClusters: Number of story clusters
            - totalArticles: Number of articles

        Raises:
            APITimeoutError: If request times out
            APIResponseError: If response is malformed or invalid
            APIError: For other API errors
        """
        endpoint = f"{self.base_url}/api/batches/latest"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                data = response.json()

            # Validate response has required fields
            if "id" not in data:
                raise APIResponseError("Invalid response format: missing batch id")

            logger.info(f"Fetched latest batch: {data.get('id')}")
            return data

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise APITimeoutError(
                f"Request to {endpoint} timed out after {self.timeout}s"
            ) from e

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            raise APIError(f"HTTP {e.response.status_code}: {e}") from e

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise APIError(f"Failed to connect to {endpoint}: {e}") from e

        except (ValueError, KeyError) as e:
            logger.error(f"Failed to parse response: {e}")
            raise APIResponseError(f"Malformed API response: {e}") from e

    async def get_categories(self) -> list[Category]:
        """Fetch available news categories from the latest batch.

        Returns:
            List of Category objects

        Raises:
            APITimeoutError: If request times out
            APIResponseError: If response is malformed or invalid
            APIError: For other API errors
        """
        endpoint = f"{self.base_url}/api/batches/latest/categories"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                data = response.json()

            # Extract categories array from response
            categories_data = data.get("categories", [])

            if not isinstance(categories_data, list):
                raise APIResponseError(
                    "Invalid response format: categories is not a list"
                )

            # Parse each category
            categories = []
            for cat_data in categories_data:
                try:
                    # Map API fields to our Category model
                    category_dict = {
                        "id": cat_data.get("id"),
                        "name": cat_data.get("categoryId"),
                        "display_name": cat_data.get("categoryName"),
                    }
                    category = Category.from_api_response(category_dict)
                    categories.append(category)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse category: {e}")
                    continue

            logger.info(f"Fetched {len(categories)} categories")
            return categories

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise APITimeoutError(
                f"Request to {endpoint} timed out after {self.timeout}s"
            ) from e

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            raise APIError(f"HTTP {e.response.status_code}: {e}") from e

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise APIError(f"Failed to connect to {endpoint}: {e}") from e

        except (ValueError, KeyError) as e:
            logger.error(f"Failed to parse response: {e}")
            raise APIResponseError(f"Malformed API response: {e}") from e

    async def get_stories(
        self, category_id: str, limit: int = 12
    ) -> tuple[list[Story], str]:
        """Fetch stories for a category from the latest batch.

        Args:
            category_id: Category UUID (from Category.id field)
            limit: Maximum number of stories to return (1-100, default 12)

        Returns:
            Tuple of (list of Story objects, batch ID)

        Raises:
            APITimeoutError: If request times out
            APIResponseError: If response is malformed or invalid
            APIError: For other API errors
        """
        # Validate limit
        limit = max(1, min(100, limit))

        endpoint = (
            f"{self.base_url}/api/batches/latest/categories/{category_id}/stories"
        )
        params = {"limit": limit}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()

            # Extract batch ID and stories array from response
            batch_id = data.get("batchId", "")
            stories_data = data.get("stories", [])

            if not isinstance(stories_data, list):
                raise APIResponseError("Invalid response format: stories is not a list")

            # Parse each story
            stories = []
            for story_data in stories_data:
                try:
                    # Map API story cluster to our Story model
                    # Use the first article from the cluster for URL, source, and date
                    articles = story_data.get("articles", [])
                    if not articles:
                        logger.warning("Story has no articles, skipping")
                        continue

                    first_article = articles[0]

                    # Build story dictionary for our model
                    story_dict = {
                        "id": story_data.get(
                            "id", str(story_data.get("cluster_number", "unknown"))
                        ),
                        "title": story_data.get("title"),
                        "url": first_article.get("link"),
                        "source": first_article.get("domain"),
                        "published_at": first_article.get("date"),
                        "excerpt": story_data.get("short_summary"),
                    }

                    story = Story.from_api_response(story_dict)
                    stories.append(story)

                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse story: {e}")
                    continue

            logger.info(
                f"Fetched {len(stories)} stories for category {category_id} (batch: {batch_id})"
            )
            return stories, batch_id

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise APITimeoutError(
                f"Request to {endpoint} timed out after {self.timeout}s"
            ) from e

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            raise APIError(f"HTTP {e.response.status_code}: {e}") from e

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise APIError(f"Failed to connect to {endpoint}: {e}") from e

        except (ValueError, KeyError) as e:
            logger.error(f"Failed to parse response: {e}")
            raise APIResponseError(f"Malformed API response: {e}") from e
