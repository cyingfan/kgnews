"""Configuration data model for Kagi News Reader."""

from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration.

    Attributes:
        selected_categories: List of category IDs selected by the user
        theme: Theme name from Textual's available themes
    """

    selected_categories: list[str]
    theme: str = "textual-dark"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "selected_categories": self.selected_categories,
            "theme": self.theme,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary.

        Args:
            data: Dictionary from JSON deserialization

        Returns:
            Config instance

        Raises:
            ValueError: If data is invalid
        """
        try:
            selected_categories = data.get("selected_categories", [])

            # Ensure it's a list
            if not isinstance(selected_categories, list):
                raise ValueError("selected_categories must be a list")

            # Ensure all items are strings
            selected_categories = [str(cat) for cat in selected_categories]

            # Get theme with default fallback
            theme = data.get("theme", "textual-dark")
            if not isinstance(theme, str):
                theme = "textual-dark"

            return cls(selected_categories=selected_categories, theme=theme)

        except (TypeError, AttributeError) as e:
            raise ValueError(f"Invalid configuration data: {e}")

    @classmethod
    def default(cls) -> "Config":
        """Create default configuration.

        Returns:
            Config with sensible defaults (empty category list)
        """
        # Start with empty list - user will be prompted to configure
        # This is better UX than pre-selecting categories they may not want
        return cls(selected_categories=[])
