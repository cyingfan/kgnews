"""Main application class for Kagi News Reader."""

import logging

from textual.app import App
from textual.binding import Binding

from kgnews.config import ConfigManager
from kgnews.ui.screens import ConfigScreen, MainScreen

logger = logging.getLogger(__name__)


class KagiNewsApp(App):
    """Main Textual application for Kagi News Reader.

    Orchestrates the main news display and configuration screens.
    """

    TITLE = "Kagi News Reader"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("c", "show_config", "Configure"),
    ]

    # Install screens
    SCREENS = {
        "main": MainScreen,
        "config": ConfigScreen,
    }

    # Available themes mapping to Textual's built-in themes
    AVAILABLE_THEMES = [
        "textual-dark",
        "textual-light",
        "nord",
        "gruvbox",
        "monokai",
        "dracula",
        "catppuccin-mocha",
        "catppuccin-latte",
        "solarized-light",
        "tokyo-night",
        "flexoki",
        "textual-ansi",
    ]

    def on_mount(self) -> None:
        """Initialize the application and navigate to main screen."""
        logger.info("Application starting")

        # Load and apply theme
        config_manager = ConfigManager()
        config = config_manager.load()
        self._apply_theme(config.theme)

        # Navigate to the main screen
        self.push_screen("main")

    def _apply_theme(self, theme_name: str) -> None:
        """Apply the specified theme.

        Args:
            theme_name: Name of theme to apply
        """
        # Validate theme is available, fallback to textual-dark
        if theme_name not in self.AVAILABLE_THEMES:
            theme_name = "textual-dark"

        self.theme = theme_name
        logger.info(f"Applied theme: {theme_name}")

    async def action_show_config(self) -> None:
        """Show the configuration screen."""
        logger.info("Opening configuration screen")

        # Push the config screen and wait for dismissal
        result = await self.push_screen_wait(ConfigScreen())

        # If config was saved (result is True), refresh the main screen
        if result:
            logger.info("Configuration saved, refreshing main screen")

            # Reload and apply theme
            config_manager = ConfigManager()
            config = config_manager.load()
            self._apply_theme(config.theme)

            # Pop current screen and push a fresh MainScreen
            self.pop_screen()
            self.push_screen("main")

    def action_quit(self) -> None:
        """Quit the application."""
        logger.info("Application exiting")
        self.exit()
