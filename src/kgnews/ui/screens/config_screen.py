"""Configuration screen for selecting news categories."""

import logging

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Label, Select, Static

from kgnews.api import APIClient, APIError
from kgnews.config import ConfigManager
from kgnews.models import Category

logger = logging.getLogger(__name__)


class ConfigScreen(Screen):
    """Configuration screen for selecting news categories.

    Allows users to select which categories to display in the main screen.
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    #category-container {
        height: 1fr;
        margin: 1 0;
        overflow-y: auto;
        scrollbar-size: 2 1;
    }

    #category-container:focus {
        border: solid $accent;
    }

    .category-row {
        height: auto;
        padding: 0 1;
    }

    #theme-section {
        height: auto;
        padding: 1;
        margin: 1 0;
        border: solid $primary;
    }

    #theme-select {
        width: 100%;
        margin: 0 0 1 0;
    }

    #button-row {
        dock: bottom;
        height: auto;
        padding: 1;
        align: center middle;
    }

    Checkbox {
        width: 1fr;
        min-width: 25;
    }

    Checkbox.highlighted {
        background: $accent 20%;
        border: solid $accent;
    }
    """

    def __init__(self, *args, **kwargs):
        """Initialize the ConfigScreen."""
        super().__init__(*args, **kwargs)
        self.api_client = APIClient()
        self.config_manager = ConfigManager()
        self.categories: list[Category] = []
        self.checkboxes: dict[str, Checkbox] = {}
        self._container: VerticalScroll | None = None
        self._loading_label: Label | None = None
        self._theme_select: Select | None = None
        self._original_theme: str | None = None  # Store original theme for cancel

        # Available themes from the app
        self.available_themes = [
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

    def compose(self) -> ComposeResult:
        """Compose the configuration screen layout."""
        with Vertical():
            yield Label("Configure News Categories", id="title")

            # Loading label (will be hidden after loading)
            self._loading_label = Label("Loading categories...", id="loading")
            yield self._loading_label

            # Scrollable container for checkboxes (rows added dynamically in on_mount)
            self._container = VerticalScroll(id="category-container", can_focus=True)
            yield self._container

            # Theme selection section
            with Vertical(id="theme-section"):
                yield Label("Theme")
                # Create options as tuples of (label, value)
                theme_options = [(name, name) for name in self.available_themes]
                yield Select(
                    options=theme_options,
                    value="textual-dark",
                    id="theme-select",
                    allow_blank=False,
                )

            # Buttons
            with Horizontal(id="button-row"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", id="cancel-btn")

            # Footer with keyboard shortcuts
            yield Footer()

    async def on_mount(self) -> None:
        """Load categories and current selections when screen is mounted."""
        try:
            # Fetch available categories from API
            self.categories = await self.api_client.get_categories()

            # Load current selections from config
            config = self.config_manager.load()
            selected_ids = set(config.selected_categories)

            # Store original theme for cancel functionality
            self._original_theme = config.theme

            # Set theme select based on current theme
            current_theme = config.theme
            theme_select = self.query_one("#theme-select", Select)
            if current_theme in self.available_themes:
                theme_select.value = current_theme

            # Hide loading label
            if self._loading_label:
                self._loading_label.display = False

            # Create checkboxes in rows of 3
            if self._container:
                COLUMNS_PER_ROW = 3
                current_row = None

                for i, category in enumerate(self.categories):
                    # Create a new row every COLUMNS_PER_ROW items
                    if i % COLUMNS_PER_ROW == 0:
                        current_row = Horizontal(classes="category-row")
                        await self._container.mount(current_row)

                    # Check if this category is currently selected (use stable name, not UUID id)
                    is_selected = category.name in selected_ids

                    # Create checkbox - disable individual focus, navigation handled by container
                    # Sanitize category name for use as ID (remove invalid characters like |, (), spaces)
                    safe_id = (
                        category.name.replace("|", "_")
                        .replace("(", "_")
                        .replace(")", "_")
                        .replace(" ", "_")
                    )
                    checkbox = Checkbox(
                        category.display_name,
                        value=is_selected,
                        id=f"cat-{safe_id}",
                    )
                    checkbox.can_focus = False

                    # Store reference to checkbox (use stable name as key)
                    self.checkboxes[category.name] = checkbox

                    # Mount checkbox to current row
                    if current_row:
                        await current_row.mount(checkbox)

                # Initialize highlighting for the first category
                if self.categories:
                    self._current_category_index = 0
                    self._highlight_category(0)

        except APIError as e:
            logger.error(f"Failed to fetch categories: {e}")
            if self._loading_label:
                self._loading_label.update(f"Error loading categories: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading config screen: {e}")
            if self._loading_label:
                self._loading_label.update(f"An error occurred: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button pressed event
        """
        if event.button.id == "save-btn":
            self._save_config()
        elif event.button.id == "cancel-btn":
            self._cancel()

    def _save_config(self) -> None:
        """Save selected categories and theme, then dismiss screen."""
        try:
            # Collect checked category IDs
            selected_ids = [
                category_id
                for category_id, checkbox in self.checkboxes.items()
                if checkbox.value
            ]

            # Get selected theme
            theme_select = self.query_one("#theme-select", Select)
            theme = theme_select.value if theme_select.value else "textual-dark"

            # Load config, update both fields, and save
            config = self.config_manager.load()
            config.selected_categories = selected_ids
            config.theme = theme
            self.config_manager.save(config)

            logger.info(
                f"Saved configuration with {len(selected_ids)} categories and theme '{theme}'"
            )

            # Dismiss screen with success result
            self.dismiss(True)

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            # Still dismiss but with failure result
            self.dismiss(False)

    def _cancel(self) -> None:
        """Cancel configuration and dismiss screen without saving."""
        logger.info("Configuration cancelled")

        # Restore original theme if it was changed
        if self._original_theme and hasattr(self.app, "_apply_theme"):
            self.app._apply_theme(self._original_theme)
            logger.info(f"Restored original theme: {self._original_theme}")

        self.dismiss(False)

    def action_save(self) -> None:
        """Action to save configuration (triggered by Ctrl+S)."""
        self._save_config()

    def action_cancel(self) -> None:
        """Action to cancel configuration (triggered by Escape)."""
        self._cancel()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle theme selection changes to immediately apply theme preview.

        Args:
            event: Select changed event
        """
        # Check if this is the theme select
        if event.select.id == "theme-select" and event.value:
            # Apply theme immediately for preview
            theme_name = str(event.value)
            if hasattr(self.app, "_apply_theme"):
                self.app._apply_theme(theme_name)
                logger.info(f"Applied theme preview: {theme_name}")

    def on_key(self, event: events.Key) -> None:
        """Handle key events for proper navigation.

        Tab/Shift+Tab: Navigate between sections (categories, theme, buttons)
        Arrow keys: Navigate within sections (checkboxes, select options)
        Space/Enter: Toggle checkbox when category container is focused

        Args:
            event: Key event
        """
        # Check if category container has focus
        focused = self.focused
        if focused == self._container:
            # Handle arrow keys to navigate through checkboxes
            if event.key in ("up", "down", "left", "right"):
                self._navigate_checkboxes(event.key)
                event.prevent_default()
                event.stop()
            # Handle space/enter to toggle the currently highlighted checkbox
            elif event.key in ("space", "enter"):
                self._toggle_current_checkbox()
                event.prevent_default()
                event.stop()

    def _navigate_checkboxes(self, direction: str) -> None:
        """Navigate through checkboxes with arrow keys.

        Args:
            direction: Direction to navigate (up, down, left, right)
        """
        if not self.categories:
            return

        # Get current highlighted category index
        if not hasattr(self, "_current_category_index"):
            self._current_category_index = 0

        # Calculate new index based on direction
        COLUMNS_PER_ROW = 3
        current = self._current_category_index
        total = len(self.categories)

        if direction == "right":
            current = min(current + 1, total - 1)
        elif direction == "left":
            current = max(current - 1, 0)
        elif direction == "down":
            current = min(current + COLUMNS_PER_ROW, total - 1)
        elif direction == "up":
            current = max(current - COLUMNS_PER_ROW, 0)

        self._current_category_index = current
        self._highlight_category(current)

    def _highlight_category(self, index: int) -> None:
        """Highlight a category checkbox.

        Args:
            index: Index of category to highlight
        """
        if index < 0 or index >= len(self.categories):
            return

        # Remove previous highlights
        for category in self.categories:
            checkbox = self.checkboxes.get(category.name)
            if checkbox:
                checkbox.remove_class("highlighted")

        # Add highlight to current
        category = self.categories[index]
        checkbox = self.checkboxes.get(category.name)
        if checkbox:
            checkbox.add_class("highlighted")
            # Scroll to make it visible with faster animation
            checkbox.scroll_visible(animate=False)

    def _toggle_current_checkbox(self) -> None:
        """Toggle the currently highlighted checkbox."""
        if not hasattr(self, "_current_category_index"):
            return

        index = self._current_category_index
        if index < 0 or index >= len(self.categories):
            return

        category = self.categories[index]
        checkbox = self.checkboxes.get(category.name)
        if checkbox:
            checkbox.value = not checkbox.value
