"""Fetch and download TheRock nightly builds from the remote index."""

from __future__ import annotations

import http.client
import json
import re
import shutil
import socket
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Callable, Optional

from therock_picker.models import TheRockBuild, nightly_date, parse_therock_filename

NEW_INDEX_URL = "https://nightly.repo.amd.com/rocm/core/tarball/"
LEGACY_INDEX_URL = "https://rocm.nightlies.amd.com/tarball-multi-arch/"
CUTOVER_DATE = date(2026, 8, 23)

_FILES_RE = re.compile(r"const files = (\[.*?\]);", re.S)
_CHUNK_SIZE = 1 << 16
_READ_TIMEOUT = 300
_MAX_RETRIES = 5

# Transient network errors worth retrying (mid-transfer stalls, resets),
# as opposed to permanent errors like a 404.
_RETRYABLE_ERRORS = (TimeoutError, socket.timeout, http.client.IncompleteRead)


@dataclass(frozen=True)
class RemoteFetchResult:
    """Combined nightly listing from the new and/or legacy indexes."""

    builds: list[TheRockBuild]
    warnings: list[str]


def _http_get(url: str) -> str:
    """Fetch `url` and return the response body as text."""
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def _parse_index(html: str, index_url: str) -> list[TheRockBuild]:
    """Parse an index page's embedded `const files = [...]` listing."""
    match = _FILES_RE.search(html)
    if match is None:
        raise ValueError(
            f"Could not find embedded file listing in index page: {index_url}"
        )
    raw_entries = json.loads(match.group(1))

    builds = []
    for entry in raw_entries:
        build = parse_therock_filename(entry["name"], mtime=entry.get("mtime"))
        if build is not None:
            builds.append(replace(build, index_url=index_url))
    return builds


def _fetch_one_index(
    fetch: Callable[[str], str], index_url: str
) -> list[TheRockBuild]:
    """Fetch and parse a single nightly index page."""
    return _parse_index(fetch(index_url), index_url)


def _prefer_new_index(build: TheRockBuild) -> bool:
    """True if a filename collision should keep the new-index copy."""
    parsed = nightly_date(build.version)
    return parsed is None or parsed >= CUTOVER_DATE


def _merge_builds(
    new_builds: list[TheRockBuild], legacy_builds: list[TheRockBuild]
) -> list[TheRockBuild]:
    """Union listings; on filename collision pick host by cutover date."""
    by_filename: dict[str, TheRockBuild] = {}
    for build in new_builds:
        by_filename[build.filename] = build
    for build in legacy_builds:
        existing = by_filename.get(build.filename)
        if existing is None or not _prefer_new_index(build):
            by_filename[build.filename] = build

    builds = list(by_filename.values())
    builds.sort(key=lambda build: build.mtime or 0, reverse=True)
    return builds


def fetch_remote_builds(
    fetch: Callable[[str], str] = _http_get,
) -> RemoteFetchResult:
    """Fetch and merge nightly listings from the new and legacy indexes.

    Each index page embeds its file listing as a `const files = [...]`
    JSON array in an inline `<script>` block; this avoids needing a
    headless browser to execute any client-side rendering.

    Args:
        fetch: Function to retrieve a URL's body as text, injectable for
            testing without a real network call.

    Returns:
        Parsed builds (sorted newest first) plus per-index warnings when
        exactly one index could not be fetched. Entries whose filename
        doesn't match TheRock's naming pattern are silently dropped.

    Raises:
        ValueError: If neither index could be fetched.
    """
    warnings: list[str] = []
    results: dict[str, list[TheRockBuild]] = {}
    for label, index_url in (("new", NEW_INDEX_URL), ("legacy", LEGACY_INDEX_URL)):
        try:
            results[label] = _fetch_one_index(fetch, index_url)
        except (OSError, ValueError) as exc:
            warnings.append(f"{label} index failed: {exc}")

    if not results:
        raise ValueError(
            "Could not fetch any nightly index: " + "; ".join(warnings)
        )

    return RemoteFetchResult(
        builds=_merge_builds(results.get("new", []), results.get("legacy", [])),
        warnings=warnings,
    )


def build_url(build: TheRockBuild) -> str:
    """Return the direct download URL for `build`'s tarball."""
    index_url = build.index_url or NEW_INDEX_URL
    return index_url.rstrip("/") + "/" + build.filename


def download_build(
    build: TheRockBuild,
    dest_dir: Path,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """Download `build`'s tarball into `dest_dir`.

    Tarballs are multi-GB, so a mid-transfer stall is expected on a real
    network. Rather than let `urllib`'s per-read socket timeout kill the
    whole transfer, this resumes via HTTP Range requests (the server
    supports 206 Partial Content) and retries a bounded number of times.

    Args:
        build: The build to download.
        dest_dir: Destination directory; created if missing.
        on_progress: Optional callback invoked as `(bytes_read, total_bytes)`
            after each chunk; `total_bytes` is 0 if the server omitted
            Content-Length.

    Returns:
        Path to the downloaded tarball.

    Raises:
        OSError: If the download still fails after retrying.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / build.filename
    url = build_url(build)

    for attempt in range(1, _MAX_RETRIES + 1):
        resume_from = dest_path.stat().st_size if dest_path.exists() else 0
        request = urllib.request.Request(url)
        if resume_from:
            request.add_header("Range", f"bytes={resume_from}-")

        try:
            with urllib.request.urlopen(request, timeout=_READ_TIMEOUT) as response:
                resumed = resume_from and response.status == 206
                read = resume_from if resumed else 0
                total = read + int(response.headers.get("Content-Length", 0))

                with open(dest_path, "ab" if resumed else "wb") as out_file:
                    while True:
                        chunk = response.read(_CHUNK_SIZE)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        read += len(chunk)
                        if on_progress is not None:
                            on_progress(read, total)

            if total and read < total:
                # Connection closed early without raising; treat as a
                # transient failure so the next attempt resumes via Range.
                if attempt == _MAX_RETRIES:
                    raise OSError(
                        f"Download incomplete: got {read} of {total} bytes"
                    )
                continue
            return dest_path
        except _RETRYABLE_ERRORS:
            if attempt == _MAX_RETRIES:
                raise


def extract_build(archive_path: Path, dest_dir: Path) -> Path:
    """Extract a downloaded TheRock tarball into a version-named directory.

    TheRock tarballs contain a flat `bin/`, `lib/`, `share/`, ... layout
    with no wrapping directory, so the extraction target's name is the
    only reliable place to record which build it is; this uses the
    tarball's own filename (minus `.tar.gz`) for that directory.

    Args:
        archive_path: Path to the downloaded `.tar.gz` file.
        dest_dir: Directory the extraction directory is created under.

    Returns:
        Path to the extracted directory.

    Raises:
        OSError, tarfile.TarError: If extraction is interrupted; no
            partial directory is left behind in that case.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    extract_to = dest_dir / archive_path.name[: -len(".tar.gz")]

    tmp_dir = Path(tempfile.mkdtemp(dir=dest_dir, prefix=f".{extract_to.name}-"))
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            # TheRock tarballs are official AMD-published builds (trusted
            # source) and contain absolute symlinks baked in from the build
            # machine; the strict `data_filter` rejects those as escaping the
            # destination, so use `fully_trusted_filter` instead.
            tar.extractall(
                tmp_dir,
                filter=getattr(tarfile, "fully_trusted_filter", None),
            )
    except BaseException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

    if extract_to.exists():
        shutil.rmtree(extract_to)
    tmp_dir.rename(extract_to)
    return extract_to
