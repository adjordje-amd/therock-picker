"""Best-effort detection of local AMD GPU gfx targets."""

from __future__ import annotations

import re
import subprocess
from typing import Callable

# Real chip codes always have 3+ hex chars (e.g. "gfx1201", "gfx90a");
# this excludes rocminfo's 2-digit "generic" ISA fallback names (e.g.
# "gfx12-generic", "gfx10-3-generic").
_GFX_RE = re.compile(r"gfx[0-9a-fA-F]{3,}")


def _run_rocminfo(args: list[str]) -> str:
    """Run a command and return its stdout, or "" if it fails to run."""
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout


def detect_local_gfx_targets(
    run: Callable[[list[str]], str] = _run_rocminfo,
) -> list[str]:
    """Detect the local system's GPU gfx architectures via `rocminfo`.

    A machine may have more than one GPU (and thus more than one gfx
    target), e.g. an APU alongside a discrete card.

    Args:
        run: Command runner, injectable for testing. Receives an argv list
            and returns stdout as a string (empty on failure).

    Returns:
        Distinct gfx targets found (e.g. ["gfx1100", "gfx1201"]), in the
        order they first appear. Empty if `rocminfo` is unavailable or
        reports no gfx target.
    """
    output = run(["rocminfo"])
    return list(dict.fromkeys(_GFX_RE.findall(output)))


def gfx_bucket_matches(bucket: str, detected: str) -> bool:
    """Return whether a locally detected chip falls under a build's bucket.

    Remote builds are published per gfx-family "bucket" (e.g. "gfx110X"
    covers gfx1100, gfx1101, ...) as well as per exact chip (e.g. "gfx950",
    "gfx90a"). A wildcard bucket ends in "X"; matching then compares the
    shared prefix instead of requiring an exact string match.

    Args:
        bucket: A remote build's gfx_target, e.g. "gfx110X" or "gfx950".
        detected: A locally detected exact chip, e.g. "gfx1100".

    Returns:
        True if `detected` is covered by `bucket`.
    """
    if bucket == detected:
        return True
    if bucket.endswith("X"):
        return detected.startswith(bucket[:-1])
    return False
