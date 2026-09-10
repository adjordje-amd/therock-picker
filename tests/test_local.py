"""Tests for local.py's delete_entry."""

from __future__ import annotations

from pathlib import Path

from therock_picker.local import LocalEntry, delete_entry
from therock_picker.models import parse_therock_filename


def _entry(path: Path, extracted: bool) -> LocalEntry:
    build = parse_therock_filename(f"{path.name}.tar.gz" if extracted else path.name)
    assert build is not None
    return LocalEntry(build=build, path=path, extracted=extracted)


class TestDeleteEntry:
    def test_deletes_tarball_file(self, tmp_path: Path) -> None:
        tarball = tmp_path / "therock-dist-linux-gfx1100-6.0.0.tar.gz"
        tarball.write_bytes(b"fake tarball")

        delete_entry(_entry(tarball, extracted=False))

        assert not tarball.exists()

    def test_deletes_extracted_directory_tree(self, tmp_path: Path) -> None:
        build_dir = tmp_path / "therock-dist-linux-gfx1100-6.0.0"
        nested = build_dir / "lib" / "nested"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_text("data")

        delete_entry(_entry(build_dir, extracted=True))

        assert not build_dir.exists()
