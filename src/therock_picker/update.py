"""Check for and apply application updates via GitHub releases + pipx."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable, Optional

DEFAULT_REPO = "adjordje-amd/therock-picker"

_UNKNOWN_VERSION = "0.0.0"


def _http_get_json(url: str) -> dict[str, Any]:
    """Fetch `url` and parse its response body as JSON."""
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def current_version() -> str:
    """Return the installed package version, or a sentinel if not installed."""
    try:
        return version("therock-picker")
    except PackageNotFoundError:
        return _UNKNOWN_VERSION


def fetch_latest_version(
    fetch: Callable[[str], dict[str, Any]] = _http_get_json,
    repo: str = DEFAULT_REPO,
) -> Optional[str]:
    """Return the latest released version tag for `repo`, or None on failure.

    Args:
        fetch: Function to retrieve and JSON-decode a URL, injectable for
            testing without a real network call.
        repo: GitHub `owner/name` slug to query releases for.

    Returns:
        The latest release's tag name with any leading "v" stripped, or
        None if the release couldn't be fetched or parsed.
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        release = fetch(url)
        tag = release["tag_name"]
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError):
        return None
    return tag[1:] if tag.startswith("v") else tag


def is_newer(latest: str, current: str) -> bool:
    """Return True if `latest` is a newer version than `current`."""
    try:
        latest_parts = tuple(int(part) for part in latest.split("."))
        current_parts = tuple(int(part) for part in current.split("."))
    except ValueError:
        return latest != current and latest > current
    return latest_parts > current_parts


def perform_update(
    repo: str = DEFAULT_REPO,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> tuple[bool, str]:
    """Reinstall the app from `repo`'s default branch via pipx.

    Args:
        repo: GitHub `owner/name` slug to install from.
        runner: Function to execute the subprocess, injectable for testing.

    Returns:
        A `(success, output)` tuple; `output` combines stdout and stderr.
    """
    result = runner(
        ["pipx", "install", "--force", f"git+https://github.com/{repo}.git"],
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()
