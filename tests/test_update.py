"""Tests for update.py's version check and self-update logic."""

from __future__ import annotations

import subprocess

import pytest

from therock_picker.update import fetch_latest_version, is_newer, perform_update


def _fake_fetch(response: dict) -> callable:
    def fetch(url: str) -> dict:
        return response

    return fetch


def _raising_fetch(exc: Exception) -> callable:
    def fetch(url: str) -> dict:
        raise exc

    return fetch


class TestFetchLatestVersion:
    def test_strips_leading_v(self) -> None:
        fetch = _fake_fetch({"tag_name": "v1.2.3"})
        assert fetch_latest_version(fetch=fetch) == "1.2.3"

    def test_keeps_tag_without_leading_v(self) -> None:
        fetch = _fake_fetch({"tag_name": "1.2.3"})
        assert fetch_latest_version(fetch=fetch) == "1.2.3"

    def test_returns_none_on_network_error(self) -> None:
        import urllib.error

        fetch = _raising_fetch(urllib.error.URLError("no network"))
        assert fetch_latest_version(fetch=fetch) is None

    def test_returns_none_on_missing_tag_name(self) -> None:
        fetch = _fake_fetch({"unexpected": "shape"})
        assert fetch_latest_version(fetch=fetch) is None


class TestIsNewer:
    @pytest.mark.parametrize(
        "latest,current,expected",
        [
            ("0.2.0", "0.1.0", True),
            ("1.0.0", "1.0.0", False),
            ("0.1.0", "0.2.0", False),
            ("0.1.10", "0.1.9", True),
        ],
    )
    def test_dotted_versions(
        self, latest: str, current: str, expected: bool
    ) -> None:
        assert is_newer(latest, current) is expected

    def test_falls_back_to_string_compare_on_unparsable_version(self) -> None:
        assert is_newer("beta", "alpha") is True


class TestPerformUpdate:
    def test_success_returns_true_with_output(self) -> None:
        def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(
                args=(), returncode=0, stdout="installed package", stderr=""
            )

        success, output = perform_update(runner=runner)
        assert success is True
        assert output == "installed package"

    def test_failure_returns_false_with_combined_output(self) -> None:
        def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(
                args=(), returncode=1, stdout="", stderr="pipx not found"
            )

        success, output = perform_update(runner=runner)
        assert success is False
        assert "pipx not found" in output
