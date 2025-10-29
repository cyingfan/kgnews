"""Cache manager for news stories."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from kgnews.models import Story

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching of news stories by category and batch ID.

    Stories are cached in the system's temp directory, organized by category and batch.
    """

    CACHE_DIR = Path(tempfile.gettempdir()) / "kaginews_cache"

    def __init__(self, cache_dir: Path | None = None):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for cache storage (defaults to /tmp/kaginews_cache)
        """
        self.cache_dir = cache_dir or self.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, category_id: str, batch_id: str) -> Path:
        """Get cache file path for a category and batch.

        Args:
            category_id: Category UUID
            batch_id: Batch UUID

        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{category_id}_{batch_id}.json"

    def get_cached_stories(self, category_id: str, batch_id: str) -> list[Story] | None:
        """Retrieve cached stories for a category and batch.

        Args:
            category_id: Category UUID
            batch_id: Batch UUID

        Returns:
            List of Story objects if cache exists and is valid, None otherwise
        """
        cache_path = self._get_cache_path(category_id, batch_id)

        if not cache_path.exists():
            logger.debug(f"No cache found for category {category_id}, batch {batch_id}")
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate cache structure
            if not isinstance(data, dict) or "stories" not in data:
                logger.warning(f"Invalid cache format in {cache_path}")
                return None

            # Parse stories from cache
            stories = []
            for story_data in data["stories"]:
                try:
                    story = Story.from_api_response(story_data)
                    stories.append(story)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse cached story: {e}")
                    continue

            logger.info(
                f"Loaded {len(stories)} stories from cache for category {category_id}"
            )
            return stories

        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read cache file {cache_path}: {e}")
            return None

    def save_stories(
        self, category_id: str, batch_id: str, stories: list[Story]
    ) -> None:
        """Save stories to cache.

        Args:
            category_id: Category UUID
            batch_id: Batch UUID
            stories: List of Story objects to cache
        """
        cache_path = self._get_cache_path(category_id, batch_id)

        try:
            # Convert stories to serializable format
            stories_data = []
            for story in stories:
                story_dict = {
                    "id": story.id,
                    "title": story.title,
                    "url": story.url,
                    "source": story.source,
                    "published_at": story.published_at.isoformat(),
                    "excerpt": story.excerpt,
                }
                stories_data.append(story_dict)

            # Save to cache
            cache_data = {
                "batch_id": batch_id,
                "category_id": category_id,
                "stories": stories_data,
            }

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            logger.info(
                f"Cached {len(stories)} stories for category {category_id}, batch {batch_id}"
            )

        except (OSError, TypeError) as e:
            logger.error(f"Failed to save cache to {cache_path}: {e}")

    def clear_old_caches(self, current_batch_id: str) -> None:
        """Remove cache files from previous batches.

        Args:
            current_batch_id: The current batch ID to keep
        """
        if not self.cache_dir.exists():
            return

        try:
            removed_count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                # Check if file name contains the current batch ID
                if current_batch_id not in cache_file.name:
                    cache_file.unlink()
                    removed_count += 1

            if removed_count > 0:
                logger.info(f"Removed {removed_count} old cache files")

        except OSError as e:
            logger.error(f"Failed to clear old caches: {e}")
