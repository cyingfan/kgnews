"""Category data model for Kagi News."""

from dataclasses import dataclass


@dataclass
class Category:
    """Represents a news category.

    Attributes:
        id: Batch-specific UUID for the category (changes with each batch)
        name: Stable category identifier (e.g., "tech", "science") - use this for matching
        display_name: Human-readable category name for display (e.g., "Technology", "Science")
    """

    id: str
    name: str
    display_name: str

    @classmethod
    def from_api_response(cls, data: dict) -> "Category":
        """Create Category from API JSON response.

        Args:
            data: API response dictionary

        Returns:
            Category instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Validate required fields
            required_fields = ["id", "name", "display_name"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

            return cls(
                id=str(data["id"]),
                name=str(data["name"]),
                display_name=str(data["display_name"]),
            )

        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")
        except (TypeError, AttributeError) as e:
            raise ValueError(f"Invalid data structure: {e}")
