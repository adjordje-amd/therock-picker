"""Entry point for the TheRock Picker."""

import argparse
import sys

from therock_picker.app import TheRockApp
from therock_picker.update import (
    current_version,
    fetch_latest_version,
    is_newer,
    perform_update,
)


def _run_update() -> int:
    """Check for and apply an update; print progress and return an exit code."""
    print(f"Current version: {current_version()}")
    latest = fetch_latest_version()
    if latest is None:
        print("Could not check for updates (network error).")
        return 1
    if not is_newer(latest, current_version()):
        print("Already up to date.")
        return 0

    print(f"Updating to v{latest}...")
    success, output = perform_update()
    if not success:
        print(f"Update failed: {output}")
        return 1
    print(f"Updated to v{latest}.")
    return 0


def main() -> None:
    """Launch the TheRock Picker application, or handle --update."""
    parser = argparse.ArgumentParser(prog="therock-picker")
    parser.add_argument(
        "--update", action="store_true", help="Check for and install an update, then exit."
    )
    args = parser.parse_args()

    if args.update:
        sys.exit(_run_update())

    TheRockApp().run()


if __name__ == "__main__":
    main()
