"""Persist user settings (the TheRock root path)."""

from __future__ import annotations

import json
import os
from pathlib import Path

_APP_DIR_NAME = "therock-picker"
DEFAULT_THEROCK_PATH = str(Path.home() / "therock")


def _config_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / _APP_DIR_NAME
    return Path.home() / ".config" / _APP_DIR_NAME


def _config_file() -> Path:
    return _config_dir() / "config.json"


def _load_config() -> dict:
    try:
        data = json.loads(_config_file().read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_config_key(key: str, value: str) -> None:
    config_file = _config_file()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    data = _load_config()
    data[key] = value
    config_file.write_text(json.dumps(data))


def load_therock_path() -> str:
    """Return the configured TheRock root path (default ~/therock).

    Contains a `versions/` subdirectory (downloads are extracted there)
    and a `selected` symlink pointing at the active version.
    """
    path = _load_config().get("therock_path")
    return path if isinstance(path, str) else DEFAULT_THEROCK_PATH


def save_therock_path(path: str) -> None:
    """Persist `path` as the TheRock root path for future runs."""
    _save_config_key("therock_path", path)
