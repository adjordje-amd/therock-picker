"""Tests for dual nightly-index fetch and merge."""

from __future__ import annotations

import json
from datetime import date

import pytest

from therock_picker.models import nightly_date
from therock_picker.remote import (
    CUTOVER_DATE,
    LEGACY_INDEX_URL,
    NEW_INDEX_URL,
    build_url,
    fetch_remote_builds,
)

_LEGACY_ONLY = "therock-dist-linux-gfx1100-dgpu-10.1.0a20260822.tar.gz"
_NEW_ONLY = "therock-dist-linux-gfx1100-dgpu-10.1.0a20260823.tar.gz"
_DUP_BEFORE = "therock-dist-linux-gfx1100-dgpu-10.1.0a20260821.tar.gz"
_DUP_ON_CUTOVER = "therock-dist-linux-gfx1100-dgpu-10.1.0a20260823.tar.gz"
_DUP_UNDATED = "therock-dist-linux-gfx1100-6.0.0.tar.gz"


def _index_html(filenames: list[str], mtime: float = 1.0) -> str:
    entries = [{"name": name, "mtime": mtime} for name in filenames]
    return f"<script>const files = {json.dumps(entries)};</script>"


def _fetch_for(pages: dict[str, str]):
    def fetch(url: str) -> str:
        if url not in pages:
            raise OSError(f"unexpected url: {url}")
        return pages[url]

    return fetch


class TestNightlyDate:
    def test_parses_a_yyyymmdd_suffix(self) -> None:
        assert nightly_date("10.1.0a20260823") == date(2026, 8, 23)

    def test_returns_none_without_suffix(self) -> None:
        assert nightly_date("6.0.0") is None

    def test_cutover_constant_is_aug_23(self) -> None:
        assert CUTOVER_DATE == date(2026, 8, 23)


class TestFetchRemoteBuilds:
    def test_legacy_only_filename_uses_legacy_url(self) -> None:
        result = fetch_remote_builds(
            fetch=_fetch_for(
                {
                    NEW_INDEX_URL: _index_html([]),
                    LEGACY_INDEX_URL: _index_html([_LEGACY_ONLY]),
                }
            )
        )

        assert result.warnings == []
        assert len(result.builds) == 1
        build = result.builds[0]
        assert build.filename == _LEGACY_ONLY
        assert build.index_url == LEGACY_INDEX_URL
        assert build_url(build) == LEGACY_INDEX_URL.rstrip("/") + "/" + _LEGACY_ONLY

    def test_new_only_filename_uses_new_url(self) -> None:
        result = fetch_remote_builds(
            fetch=_fetch_for(
                {
                    NEW_INDEX_URL: _index_html([_NEW_ONLY]),
                    LEGACY_INDEX_URL: _index_html([]),
                }
            )
        )

        assert result.warnings == []
        assert len(result.builds) == 1
        build = result.builds[0]
        assert build.filename == _NEW_ONLY
        assert build.index_url == NEW_INDEX_URL
        assert build_url(build) == NEW_INDEX_URL.rstrip("/") + "/" + _NEW_ONLY

    def test_duplicate_before_cutover_prefers_legacy(self) -> None:
        result = fetch_remote_builds(
            fetch=_fetch_for(
                {
                    NEW_INDEX_URL: _index_html([_DUP_BEFORE], mtime=2.0),
                    LEGACY_INDEX_URL: _index_html([_DUP_BEFORE], mtime=1.0),
                }
            )
        )

        assert [b.index_url for b in result.builds] == [LEGACY_INDEX_URL]
        assert result.builds[0].filename == _DUP_BEFORE

    def test_duplicate_on_cutover_prefers_new(self) -> None:
        result = fetch_remote_builds(
            fetch=_fetch_for(
                {
                    NEW_INDEX_URL: _index_html([_DUP_ON_CUTOVER], mtime=2.0),
                    LEGACY_INDEX_URL: _index_html([_DUP_ON_CUTOVER], mtime=1.0),
                }
            )
        )

        assert [b.index_url for b in result.builds] == [NEW_INDEX_URL]

    def test_duplicate_without_date_prefers_new(self) -> None:
        result = fetch_remote_builds(
            fetch=_fetch_for(
                {
                    NEW_INDEX_URL: _index_html([_DUP_UNDATED]),
                    LEGACY_INDEX_URL: _index_html([_DUP_UNDATED]),
                }
            )
        )

        assert result.builds[0].index_url == NEW_INDEX_URL

    def test_legacy_index_failure_returns_new_builds_with_warning(self) -> None:
        def fetch(url: str) -> str:
            if url == NEW_INDEX_URL:
                return _index_html([_NEW_ONLY])
            raise OSError("legacy down")

        result = fetch_remote_builds(fetch=fetch)

        assert len(result.builds) == 1
        assert result.builds[0].filename == _NEW_ONLY
        assert len(result.warnings) == 1
        assert "legacy index failed" in result.warnings[0]

    def test_new_index_failure_returns_legacy_builds_with_warning(self) -> None:
        def fetch(url: str) -> str:
            if url == LEGACY_INDEX_URL:
                return _index_html([_LEGACY_ONLY])
            raise OSError("new down")

        result = fetch_remote_builds(fetch=fetch)

        assert len(result.builds) == 1
        assert result.builds[0].filename == _LEGACY_ONLY
        assert len(result.warnings) == 1
        assert "new index failed" in result.warnings[0]

    def test_both_indexes_failing_raises(self) -> None:
        def fetch(url: str) -> str:
            raise OSError("down")

        with pytest.raises(ValueError, match="Could not fetch any nightly index"):
            fetch_remote_builds(fetch=fetch)
