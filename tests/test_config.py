"""Tests for config.py's TheRock root path load/save normalization."""

from __future__ import annotations

from pathlib import Path

import pytest

from therock_picker import config


@pytest.fixture(autouse=True)
def _isolated_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "_config_dir", lambda: tmp_path)
    return tmp_path


class TestSaveTherockPath:
    def test_strips_leading_and_trailing_whitespace(self) -> None:
        config.save_therock_path(" /home/user/therock")

        assert config.load_therock_path() == "/home/user/therock"

    def test_strips_surrounding_whitespace(self) -> None:
        config.save_therock_path("  /home/user/therock  \n")

        assert config.load_therock_path() == "/home/user/therock"


class TestLoadTherockPath:
    def test_strips_whitespace_from_previously_saved_raw_value(self, tmp_path: Path) -> None:
        config._save_config_key("therock_path", " /home/user/therock")

        assert config.load_therock_path() == "/home/user/therock"

    def test_falls_back_to_default_when_saved_value_is_blank(self) -> None:
        config._save_config_key("therock_path", "   ")

        assert config.load_therock_path() == config.DEFAULT_THEROCK_PATH

    def test_returns_default_when_nothing_saved(self) -> None:
        assert config.load_therock_path() == config.DEFAULT_THEROCK_PATH
