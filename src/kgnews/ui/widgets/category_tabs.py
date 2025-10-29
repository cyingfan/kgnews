"""CategoryTabs widget for navigating between news categories."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import TabbedContent, TabPane, Label
from textual.widget import Widget

from kgnews.models import Category


class CategoryTabs(TabbedContent):
    """Widget for displaying category tabs with keyboard navigation.

    Provides tabbed navigation between news categories with Tab/Shift+Tab
    keyboard shortcuts and wraparound support.
    """

    class CategoryChanged(Message):
        """Message sent when the active category tab changes."""

        def __init__(self, category_id: str) -> None:
            """Initialize the message.

            Args:
                category_id: The ID of the newly active category (without 'tab-' prefix)
            """
            self.category_id = category_id
            super().__init__()

    BINDINGS = [
        Binding("tab", "next_tab", "Next tab", show=False, priority=True),
        Binding("shift+tab", "previous_tab", "Previous tab", show=False, priority=True),
        Binding("left", "previous_tab", "Previous tab", show=False, priority=True),
        Binding("right", "next_tab", "Next tab", show=False, priority=True),
    ]

    def __init__(self, *args, **kwargs):
        """Initialize the CategoryTabs widget."""
        super().__init__(*args, **kwargs)
        self._tab_ids: list[str] = []
        self._tab_to_category: dict[
            str, str
        ] = {}  # Maps sanitized tab_id to original category name

    def add_tab(self, category: Category) -> None:
        """Add a new category tab.

        Args:
            category: Category to create tab for
        """
        # Use stable category name as tab ID (prefix with 'tab-' for valid Textual ID)
        # Sanitize name to remove invalid ID characters like |, (), spaces
        safe_name = (
            category.name.replace("|", "_")
            .replace("(", "_")
            .replace(")", "_")
            .replace(" ", "_")
        )
        tab_id = f"tab-{safe_name}"
        self._tab_ids.append(tab_id)
        self._tab_to_category[tab_id] = category.name  # Store mapping to original name

        # Create a TabPane with just the category's display name
        # The content will be shown in the separate StoryList widget below
        tab_pane = TabPane(category.display_name, id=tab_id)

        # Add the tab
        self.add_pane(tab_pane)

        # Mount an empty label as placeholder to avoid showing TabPane ID
        tab_pane.mount(Label(""))

    def action_next_tab(self) -> None:
        """Navigate to the next tab with wraparound."""
        if not self._tab_ids:
            return

        # Get current tab index
        current_id = self.active

        try:
            current_index = self._tab_ids.index(current_id)
        except ValueError:
            # If current tab not found, go to first
            current_index = -1

        # Calculate next index with wraparound
        next_index = (current_index + 1) % len(self._tab_ids)
        next_id = self._tab_ids[next_index]

        # Activate the next tab
        self.active = next_id

        # Post custom message with original category name (not sanitized tab_id)
        category_name = self._tab_to_category.get(next_id, next_id)
        self.post_message(self.CategoryChanged(category_name))

    def action_previous_tab(self) -> None:
        """Navigate to the previous tab with wraparound."""
        if not self._tab_ids:
            return

        # Get current tab index
        current_id = self.active

        try:
            current_index = self._tab_ids.index(current_id)
        except ValueError:
            # If current tab not found, go to last
            current_index = 0

        # Calculate previous index with wraparound
        prev_index = (current_index - 1) % len(self._tab_ids)
        prev_id = self._tab_ids[prev_index]

        # Activate the previous tab
        self.active = prev_id

        # Post custom message with original category name (not sanitized tab_id)
        category_name = self._tab_to_category.get(prev_id, prev_id)
        self.post_message(self.CategoryChanged(category_name))
