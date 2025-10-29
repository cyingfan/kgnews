"""Main screen for displaying categorized news."""

import logging

from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Label, Static

from kgnews.api import APIClient, APIError
from kgnews.cache import CacheManager
from kgnews.config import ConfigManager
from kgnews.models import Category, Story
from kgnews.ui.widgets import CategoryTabs, StoryList

logger = logging.getLogger(__name__)


class MainScreen(Screen):
    """Main application screen showing categorized news.

    Displays news stories organized by category in a tabbed interface.
    """

    BINDINGS = [
        ("c", "show_config", "Configure"),
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, *args, **kwargs):
        """Initialize the MainScreen."""
        super().__init__(*args, **kwargs)
        self.api_client = APIClient()
        self.config_manager = ConfigManager()
        self.cache_manager = CacheManager()
        self.categories: list[Category] = []
        self.stories_by_category: dict[str, list[Story]] = {}
        self.current_batch_id: str | None = None
        self._category_tabs: CategoryTabs | None = None
        self._story_list: StoryList | None = None
        self._loading_label: Label | None = None

    def compose(self) -> ComposeResult:
        """Compose the main screen layout."""
        with Vertical():
            # Loading label (will be hidden after loading)
            self._loading_label = Label("Loading...", id="loading")
            yield self._loading_label

            # Category tabs (will be populated in on_mount)
            self._category_tabs = CategoryTabs(id="category-tabs")
            yield self._category_tabs

            # Story list
            self._story_list = StoryList(id="story-list")
            yield self._story_list

            # Footer with keyboard shortcuts
            yield Footer()

    async def _load_stories(self) -> None:
        """Load or refresh stories for all configured categories.

        Uses caching strategy: checks cache first, fetches from API if needed.
        """
        if not self.categories:
            return

        import asyncio

        # Step 1: Get latest batch information
        self._loading_label.update("Checking for latest news batch...")
        self._loading_label.display = True

        batch_info = await self.api_client.get_latest_batch()
        self.current_batch_id = batch_info.get("id")

        if not self.current_batch_id:
            logger.error("No batch ID returned from API")
            self._show_error("Failed to load news: No batch information available")
            return

        # Step 2 & 3: Load cached stories and check against current batch
        self._loading_label.update("Loading cached stories...")
        categories_to_fetch = []

        for category in self.categories:
            # Use stable category.name for caching (not UUID id which changes per batch)
            cached_stories = self.cache_manager.get_cached_stories(
                category.name, self.current_batch_id
            )

            if cached_stories is not None:
                # Step 3: Use cached stories if they match current batch
                # Store by name (stable) not id (changes per batch)
                self.stories_by_category[category.name] = cached_stories
                logger.info(f"Using cached stories for category {category.name}")
            else:
                # Step 4: Mark category for fetching if no cache match
                categories_to_fetch.append(category)

        # Fetch stories for categories without cache
        if categories_to_fetch:
            self._loading_label.update(
                f"Fetching stories for {len(categories_to_fetch)} categories..."
            )

            async def fetch_category_stories(
                category: Category,
            ) -> tuple[str, list[Story], str]:
                """Fetch stories for a single category."""
                try:
                    # API requires UUID id, but we return stable name for dict key
                    stories, batch_id = await self.api_client.get_stories(category.id)
                    return (category.name, stories, batch_id)
                except APIError as e:
                    logger.error(f"Failed to fetch stories for {category.name}: {e}")
                    return (category.name, [], "")

            # Fetch all stories concurrently
            results = await asyncio.gather(
                *[fetch_category_stories(cat) for cat in categories_to_fetch]
            )

            # Store results and save to cache
            for category_name, stories, batch_id in results:
                if stories:
                    # Use stable category name as key
                    self.stories_by_category[category_name] = stories
                    # Step 4: Save fetched stories to cache (using stable name)
                    self.cache_manager.save_stories(category_name, batch_id, stories)

        # Clean up old cache files from previous batches
        self.cache_manager.clear_old_caches(self.current_batch_id)

        # Hide loading label
        self._loading_label.display = False

    async def on_mount(self) -> None:
        """Load data when screen is mounted."""
        try:
            # Load configuration
            config = self.config_manager.load()
            selected_category_ids = config.selected_categories

            # Check if any categories are configured
            if not selected_category_ids:
                self._show_empty_state(
                    "No categories configured. Press 'c' to configure."
                )
                return

            # Fetch all available categories from API
            self._loading_label.update("Fetching categories...")
            all_categories = await self.api_client.get_categories()

            # Filter to only selected categories (match by stable name, not UUID id)
            self.categories = [
                cat for cat in all_categories if cat.name in selected_category_ids
            ]

            if not self.categories:
                logger.warning(f"No matching categories found for selected IDs")
                self._show_empty_state(
                    "Selected categories not found. Press 'c' to reconfigure."
                )
                return

            # Create tabs for each category
            for category in self.categories:
                self._category_tabs.add_tab(category)

            # Load stories using the reusable method
            await self._load_stories()

            # Show stories for the first category
            if self.categories:
                first_category = self.categories[0]
                first_stories = self.stories_by_category.get(first_category.name, [])
                self._story_list.set_stories(first_stories)

        except APIError as e:
            logger.error(f"API error during screen load: {e}")
            self._show_error(f"Failed to load news: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during screen load: {e}")
            self._show_error(f"An error occurred: {e}")

    def on_category_tabs_category_changed(
        self, message: CategoryTabs.CategoryChanged
    ) -> None:
        """Handle category tab changes to update story list.

        Args:
            message: CategoryChanged message from CategoryTabs
        """
        category_id = message.category_id

        # Find matching category and update story list
        for category in self.categories:
            if category.name == category_id:
                stories = self.stories_by_category.get(category.name, [])
                if self._story_list:
                    self._story_list.set_stories(stories)
                break

    def on_key(self, event: events.Key) -> None:
        """Handle key events to manage focus and navigation.

        Args:
            event: Key event
        """
        # Handle tab switching keys - always delegate to CategoryTabs
        if event.key in ("tab", "shift_tab", "left", "right"):
            if self._category_tabs:
                # Prevent the default behavior
                event.prevent_default()
                event.stop()

                # Manually trigger the appropriate action
                if event.key == "tab" or event.key == "right":
                    self._category_tabs.action_next_tab()
                elif event.key == "shift_tab" or event.key == "left":
                    self._category_tabs.action_previous_tab()
                return

        # If up or down arrow is pressed, ensure story list has focus
        if event.key in ("up", "down"):
            if self._story_list and self._story_list.can_focus:
                self._story_list.focus()
                # Don't prevent default - let the ListView handle the navigation

    def _show_empty_state(self, message: str) -> None:
        """Show an empty state message.

        Args:
            message: Message to display
        """
        if self._loading_label:
            self._loading_label.display = False

        if self._story_list:
            self._story_list.set_stories([])

        if self._loading_label:
            self._loading_label.update(message)
            self._loading_label.display = True

    def _show_error(self, message: str) -> None:
        """Show an error message.

        Args:
            message: Error message to display
        """
        if self._loading_label:
            self._loading_label.update(f"Error: {message}")
            self._loading_label.display = True

        if self._story_list:
            self._story_list.set_stories([])

    async def action_refresh(self) -> None:
        """Refresh stories for all categories.

        Checks for latest batch and uses caching strategy to load stories.
        """
        try:
            await self._load_stories()

            # Update the display with the currently active tab's stories
            if self._category_tabs and self._category_tabs.active:
                active_tab_id = self._category_tabs.active
                active_category_id = (
                    active_tab_id.replace("tab-", "", 1)
                    if active_tab_id.startswith("tab-")
                    else active_tab_id
                )
                stories = self.stories_by_category.get(active_category_id, [])
                if self._story_list:
                    self._story_list.set_stories(stories)

        except APIError as e:
            logger.error(f"API error during refresh: {e}")
            self._show_error(f"Failed to refresh news: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during refresh: {e}")
            self._show_error(f"An error occurred: {e}")

    def action_show_config(self) -> None:
        """Show configuration screen and reload if config was saved."""
        # Run in a worker to allow push_screen_wait
        self.run_worker(self._show_config_and_reload())

    async def _show_config_and_reload(self) -> None:
        """Worker method to show config screen and reload if config was saved."""
        from kgnews.ui.screens import ConfigScreen

        # Push config screen and wait for result
        result = await self.app.push_screen_wait(ConfigScreen())

        # If config was saved (result is True), reload this screen
        if result:
            logger.info("Configuration saved, reloading main screen")

            # Reload configuration
            config = self.config_manager.load()
            selected_category_ids = config.selected_categories

            # Clear current state
            self.categories = []
            self.stories_by_category = {}

            # Clear all tabs
            if self._category_tabs:
                # Remove all existing tabs by clearing the internal state
                self._category_tabs._tab_ids = []
                self._category_tabs._tab_to_category = {}
                # Clear the TabbedContent panes
                self._category_tabs.clear_panes()

            # Reload categories and stories
            try:
                # Check if any categories are configured
                if not selected_category_ids:
                    self._show_empty_state(
                        "No categories configured. Press 'c' to configure."
                    )
                    return

                # Fetch all available categories from API
                self._loading_label.update("Fetching categories...")
                self._loading_label.display = True
                all_categories = await self.api_client.get_categories()

                # Filter to only selected categories
                self.categories = [
                    cat for cat in all_categories if cat.name in selected_category_ids
                ]

                if not self.categories:
                    logger.warning(f"No matching categories found for selected IDs")
                    self._show_empty_state(
                        "Selected categories not found. Press 'c' to reconfigure."
                    )
                    return

                # Create tabs for each category
                for category in self.categories:
                    self._category_tabs.add_tab(category)

                # Load stories
                await self._load_stories()

                # Show stories for the first category
                if self.categories:
                    first_category = self.categories[0]
                    first_stories = self.stories_by_category.get(
                        first_category.name, []
                    )
                    self._story_list.set_stories(first_stories)

            except APIError as e:
                logger.error(f"API error during reload: {e}")
                self._show_error(f"Failed to reload news: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during reload: {e}")
                self._show_error(f"An error occurred: {e}")

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
