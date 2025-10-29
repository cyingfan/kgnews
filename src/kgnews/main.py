"""Main entry point for Kagi News Reader."""

import logging
import sys

from kgnews.app import KagiNewsApp

# Configure logging - only to file to avoid breaking TUI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("kaginews.log"),
    ],
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the Kagi News Reader application."""
    try:
        logger.info("Starting Kagi News Reader")
        app = KagiNewsApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nAn error occurred: {e}", file=sys.stderr)
        print("Please check kaginews.log for more details.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
