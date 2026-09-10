"""Fetch and download TheRock nightly builds from the remote index."""

from __future__ import annotations

import http.client
import json
import re
import socket
import tarfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from therock_picker.models import TheRockBuild, parse_therock_filename

DEFAULT_INDEX_URL = "https://rocm.nightlies.amd.com/tarball-multi-arch/"

_FILES_RE = re.compile(r"const files = (\[.*?\]);", re.S)
_CHUNK_SIZE = 1 << 16
_READ_TIMEOUT = 60
_MAX_RETRIES = 5

# Transient network errors worth retrying (mid-transfer stalls, resets),
# as opposed to permanent errors like a 404.
_RETRYABLE_ERRORS = (TimeoutError, socket.timeout, http.client.IncompleteRead)


def _http_get(url: str) -> str:
    """Fetch `url` and return the response body as text."""
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def fetch_remote_builds(
    fetch: Callable[[str], str] = _http_get,
    index_url: str = DEFAULT_INDEX_URL,
) -> list[TheRockBuild]:
    """Fetch and parse the list of builds available at `index_url`.

    The index page embeds its file listing as a `const files = [...]`
    JSON array in an inline `<script>` block; this avoids needing a
    headless browser to execute any client-side rendering.

    Args:
        fetch: Function to retrieve a URL's body as text, injectable for
            testing without a real network call.
        index_url: The nightly tarball index page to fetch.

    Returns:
        Parsed builds, sorted by modification time descending (newest
        first). Entries whose filename doesn't match TheRock's naming
        pattern are silently dropped.

    Raises:
        ValueError: If the index page has no embedded file listing.
    """
    html = fetch(index_url)
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
            builds.append(build)

    builds.sort(key=lambda build: build.mtime or 0, reverse=True)
    return builds


def build_url(build: TheRockBuild, index_url: str = DEFAULT_INDEX_URL) -> str:
    """Return the direct download URL for `build`'s tarball."""
    return index_url.rstrip("/") + "/" + build.filename


def download_build(
    build: TheRockBuild,
    dest_dir: Path,
    index_url: str = DEFAULT_INDEX_URL,
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
        index_url: Index page whose directory also hosts the tarball.
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
    url = build_url(build, index_url)

    read = 0
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

    return dest_path


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
    """
    extract_to = dest_dir / archive_path.name[: -len(".tar.gz")]
    extract_to.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(extract_to, filter=getattr(tarfile, "data_filter", None))
    return extract_to
