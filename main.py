import logging
import sys

from interactive_console import InteractiveConsole

logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    console = InteractiveConsole()
    return console.run()


if __name__ == "__main__":
    sys.exit(main())