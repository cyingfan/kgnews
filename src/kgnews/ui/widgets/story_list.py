"""StoryList widget for displaying news stories."""

from textual.binding import Binding
from textual.widgets import Label, ListItem, ListView, Static

from kgnews.models import Story


class StoryList(ListView):
    """Widget for displaying a scrollable list of news stories.

    Extends Textual's ListView for built-in scrolling and arrow key navigation.
    Supports Enter to expand/collapse story details.
    """

    BINDINGS = [
        Binding("enter", "toggle_story", "Toggle Details", show=False),
        # Note: up/down are handled by ListView's built-in navigation
    ]

    def __init__(self, *args, **kwargs):
        """Initialize the StoryList widget."""
        super().__init__(*args, **kwargs)
        self._stories: list[Story] = []
        self._expanded_stories: set[str] = set()  # Track expanded story IDs

    def set_stories(self, stories: list[Story]) -> None:
        """Update the displayed stories.

        Args:
            stories: List of Story objects to display
        """
        self._stories = stories
        self._expanded_stories.clear()  # Reset expansion state

        # Clear existing items
        self.clear()

        if not stories:
            # Show empty state message
            empty_item = ListItem(Label("No stories available"))
            self.append(empty_item)
            return

        # Add each story as a list item
        for i, story in enumerate(stories):
            list_item = self._create_story_item(story, i)
            self.append(list_item)

    def _create_story_item(self, story: Story, index: int) -> ListItem:
        """Create a ListItem for a story.

        Args:
            story: Story to create item for
            index: Index in the story list

        Returns:
            ListItem widget
        """
        is_expanded = story.id in self._expanded_stories

        if is_expanded:
            # Show expanded view with all details
            content = self._create_expanded_content(story)
        else:
            # Show collapsed view (single line) - use Static for text wrapping
            content = Static(story.format_display())
            content.styles.width = "100%"

        # Don't set ID to avoid conflicts when switching tabs
        list_item = ListItem(content)
        list_item.story_data = story
        list_item.story_index = index
        return list_item

    def _create_expanded_content(self, story: Story) -> Static:
        """Create expanded content showing all story details.

        Args:
            story: Story to show details for

        Returns:
            Static widget with formatted story details and text wrapping
        """
        # Build multi-line content using Rich markup
        time_str = story._format_time(story.published_at)

        lines = [
            f"[bold]{story.title}[/bold]",
            f"[dim]Source: {story.source} | {time_str}[/dim]",
            f"[dim]URL: {story.url}[/dim]",
        ]

        # Add excerpt/summary if available
        if story.excerpt:
            lines.append("")  # Blank line
            lines.append(f"[italic]{story.excerpt}[/italic]")

        lines.append("")  # Blank line
        lines.append("[dim]Press Enter to collapse[/dim]")

        # Join all lines into a single Static widget with wrapping enabled
        content_text = "\n".join(lines)
        widget = Static(content_text)
        widget.styles.width = "100%"
        return widget

    def action_toggle_story(self) -> None:
        """Toggle expansion of the currently selected story."""
        if not self._stories:
            return

        # Get the currently highlighted item
        selected_index = self.index
        if selected_index is None or selected_index >= len(self._stories):
            return

        story = self._stories[selected_index]

        # Toggle expansion state
        if story.id in self._expanded_stories:
            self._expanded_stories.remove(story.id)
        else:
            self._expanded_stories.add(story.id)

        # Refresh the display
        self._refresh_story_item(selected_index)

    def _refresh_story_item(self, index: int) -> None:
        """Refresh a single story item to show its current state.

        Args:
            index: Index of the story to refresh
        """
        if index >= len(self._stories):
            return

        # Rebuild the entire list to refresh the selected item
        # This is simpler and more reliable than trying to update individual items
        current_index = self.index
        self.clear()

        for i, story in enumerate(self._stories):
            list_item = self._create_story_item(story, i)
            self.append(list_item)

        # Restore selection - call_after_refresh ensures highlight is preserved
        self.call_after_refresh(self._restore_index, current_index)

    def _restore_index(self, index: int) -> None:
        """Restore the selection index after refresh.

        Args:
            index: Index to restore
        """
        self.index = index
