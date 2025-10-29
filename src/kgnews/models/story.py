"""Story data model for Kagi News."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar


@dataclass
class Story:
    """Represents a news story from Kagi News.

    Attributes:
        id: Unique identifier for the story
        title: Story headline
        url: Link to the full story
        source: News source/publisher
        published_at: Publication timestamp
        excerpt: Optional story excerpt/summary
    """

    id: str
    title: str
    url: str
    source: str
    published_at: datetime
    excerpt: str | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Story":
        """Create Story from API JSON response.

        Args:
            data: API response dictionary

        Returns:
            Story instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Validate required fields
            required_fields = ["id", "title", "url", "source", "published_at"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

            # Parse published_at - handle various datetime formats
            published_at = data["published_at"]
            if isinstance(published_at, str):
                # Try ISO format first
                try:
                    published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                except ValueError:
                    # Try parsing as timestamp if it's a numeric string
                    try:
                        published_at = datetime.fromtimestamp(float(published_at))
                    except (ValueError, TypeError):
                        raise ValueError(f"Invalid datetime format: {published_at}")
            elif isinstance(published_at, (int, float)):
                published_at = datetime.fromtimestamp(published_at)
            elif not isinstance(published_at, datetime):
                raise ValueError(f"Invalid datetime type: {type(published_at)}")

            return cls(
                id=str(data["id"]),
                title=str(data["title"]),
                url=str(data["url"]),
                source=str(data["source"]),
                published_at=published_at,
                excerpt=str(data["excerpt"]) if "excerpt" in data and data["excerpt"] else None,
            )

        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")
        except (TypeError, AttributeError) as e:
            raise ValueError(f"Invalid data structure: {e}")

    def format_display(self) -> str:
        """Format story for display in TUI.

        Returns:
            Formatted string with title, source, and timestamp
        """
        # Format timestamp as relative time or absolute
        time_str = self._format_time(self.published_at)

        # Truncate title if too long for better display
        max_title_length = 80
        display_title = self.title
        if len(display_title) > max_title_length:
            display_title = display_title[:max_title_length - 3] + "..."

        return f"{display_title} | {self.source} | {time_str}"

    def _format_time(self, dt: datetime) -> str:
        """Format datetime for display.

        Args:
            dt: Datetime to format

        Returns:
            Formatted time string
        """
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt

        # Show relative time for recent stories
        if diff.days == 0:
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60

            if hours == 0:
                if minutes == 0:
                    return "just now"
                return f"{minutes}m ago"
            return f"{hours}h ago"
        elif diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"{diff.days}d ago"
        else:
            # Show absolute date for older stories
            return dt.strftime("%Y-%m-%d")
