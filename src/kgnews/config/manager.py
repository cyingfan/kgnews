"""Configuration management for Kagi News Reader."""

import json
import logging
from pathlib import Path

from kgnews.models import Config

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages user configuration persistence.

    Handles loading and saving user preferences to config.json,
    with graceful error handling for missing or corrupted files.
    """

    def __init__(self, config_path: Path | str | None = None):
        """Initialize ConfigManager.

        Args:
            config_path: Path to config file. Defaults to config.json in project root.
        """
        if config_path is None:
            # Default to config.json in project root
            self.config_path = Path("config.json")
        else:
            self.config_path = Path(config_path)

        self._config: Config | None = None

    def load(self) -> Config:
        """Load configuration from config.json.

        Returns default config if file is missing or corrupted.

        Returns:
            Config instance
        """
        # Return cached config if already loaded
        if self._config is not None:
            return self._config

        # Check if file exists
        if not self.config_path.exists():
            logger.info(f"Config file not found at {self.config_path}, using defaults")
            self._config = Config.default()
            return self._config

        try:
            # Read and parse JSON
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Create Config from dictionary
            self._config = Config.from_dict(data)
            logger.info(f"Loaded configuration from {self.config_path}")
            return self._config

        except json.JSONDecodeError as e:
            logger.warning(
                f"Corrupted config file at {self.config_path}: {e}. Using defaults."
            )
            self._config = Config.default()
            return self._config

        except (ValueError, OSError) as e:
            logger.warning(
                f"Error loading config from {self.config_path}: {e}. Using defaults."
            )
            self._config = Config.default()
            return self._config

    def save(self, config: Config) -> None:
        """Save configuration to config.json.

        Creates the file if it doesn't exist.

        Args:
            config: Config instance to save
        """
        try:
            # Ensure parent directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write JSON with pretty formatting
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

            # Update cached config
            self._config = config
            logger.info(f"Saved configuration to {self.config_path}")

        except (OSError, TypeError) as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            raise

    def get_selected_categories(self) -> list[str]:
        """Get list of selected category IDs.

        Returns:
            List of category IDs
        """
        config = self.load()
        return config.selected_categories

    def set_selected_categories(self, categories: list[str]) -> None:
        """Set selected categories and save.

        Args:
            categories: List of category IDs to select
        """
        config = self.load()
        config.selected_categories = categories
        self.save(config)

    def get_theme(self) -> str:
        """Get current theme.

        Returns:
            Theme name
        """
        config = self.load()
        return config.theme

    def set_theme(self, theme: str) -> None:
        """Set theme and save.

        Args:
            theme: Theme name to set
        """
        config = self.load()
        config.theme = theme
        self.save(config)
