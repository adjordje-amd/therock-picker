"""Data model and filename parsing for TheRock distribution tarballs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

_PREFIX = "therock-dist-"
_SUFFIX = ".tar.gz"


@dataclass(frozen=True)
class TheRockBuild:
    """A single TheRock tarball build, parsed from its filename.

    Attributes:
        platform: Target OS, e.g. "linux" or "windows".
        gfx_target: GPU architecture target, e.g. "gfx1100", "gfx94X".
        variant: Optional build variant (e.g. "dgpu", "tests"); empty
            string when the filename carries none.
        version: Package version, e.g. "7.15.0a20260815".
        filename: Original tarball filename.
        mtime: Modification time as a Unix timestamp, if known.
    """

    platform: str
    gfx_target: str
    variant: str
    version: str
    filename: str
    mtime: Optional[float] = None


def parse_therock_filename(
    name: str, mtime: Optional[float] = None
) -> Optional[TheRockBuild]:
    """Parse a TheRock tarball filename into a `TheRockBuild`.

    Expected shape: `therock-dist-{platform}-{gfx_target}-{variant?}-{version}.tar.gz`
    where `variant` is zero or more hyphen-joined words. Returns None if
    `name` does not match this shape (e.g. unrelated files).

    Args:
        name: Tarball filename, e.g.
            "therock-dist-linux-gfx1100-dgpu-tests-7.15.0a20260815.tar.gz".
        mtime: Optional modification time to attach to the result.

    Returns:
        A `TheRockBuild`, or None if `name` doesn't match the expected shape.
    """
    if not (name.startswith(_PREFIX) and name.endswith(_SUFFIX)):
        return None

    body = name[len(_PREFIX) : -len(_SUFFIX)]
    parts = body.split("-")
    if len(parts) < 3:
        return None

    platform, gfx_target, *middle, version = parts
    variant = "-".join(middle)
    return TheRockBuild(
        platform=platform,
        gfx_target=gfx_target,
        variant=variant,
        version=version,
        filename=name,
        mtime=mtime,
    )
