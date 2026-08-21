"""Scan a local directory for TheRock builds (downloaded or extracted)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from therock_picker.models import TheRockBuild, parse_therock_filename


@dataclass(frozen=True)
class LocalEntry:
    """A TheRock build found on disk.

    Attributes:
        build: The parsed build metadata.
        path: Path to the tarball file or extracted directory.
        extracted: True if `path` is an extracted directory rather than
            a downloaded tarball.
    """

    build: TheRockBuild
    path: Path
    extracted: bool


def scan_local_directory(path: Path) -> list[LocalEntry]:
    """Scan `path` (non-recursively) for TheRock tarballs and extracted dirs.

    A downloaded tarball is any `*.tar.gz` file matching the TheRock naming
    pattern. An extracted build is a subdirectory whose name (as if it had
    a ".tar.gz" suffix) matches the same pattern.

    Args:
        path: Directory to scan.

    Returns:
        Matching entries, sorted by version string descending.
    """
    entries: list[LocalEntry] = []
    for child in path.iterdir():
        if child.is_file() and child.name.endswith(".tar.gz"):
            build = parse_therock_filename(
                child.name, mtime=child.stat().st_mtime
            )
            if build is not None:
                entries.append(LocalEntry(build, child, extracted=False))
        elif child.is_dir():
            build = parse_therock_filename(
                f"{child.name}.tar.gz", mtime=child.stat().st_mtime
            )
            if build is not None:
                entries.append(LocalEntry(build, child, extracted=True))

    entries.sort(key=lambda entry: entry.build.version, reverse=True)
    return entries


def update_symlink(target: Path, link: Path) -> Path:
    """Repoint `link` at `target`, replacing it if it already exists.

    A symlink is filesystem state rather than a shell environment variable,
    so it stays visible to any other process without needing to be
    re-exported or sourced.

    Args:
        target: Directory the symlink should point to (an extracted build).
        link: Path where the symlink itself should live.

    Returns:
        `link`, for convenience chaining.
    """
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target, target_is_directory=True)
    return link


def versions_dir(therock_path: Path) -> Path:
    """The subdirectory of `therock_path` where downloads are extracted."""
    return therock_path / "versions"


def selected_link(therock_path: Path) -> Path:
    """The symlink under `therock_path` pointing at the selected version."""
    return therock_path / "selected"
