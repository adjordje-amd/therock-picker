# Feature: TheRock TUI (download & select AMD TheRock/ROCm builds)

## Context
Working dir `/home/amd/work/TheRockTui` empty, no git repo. User wants Python TUI to:
- browse a **local directory**, scan it for already-downloaded/extracted TheRock builds
- browse **remote nightly builds** (rocm.nightlies.amd.com) and download a selected one

Confirmed via user Q&A:
- Artifact type: **tarballs** (`therock-dist-*.tar.gz`), not pip/deb/rpm
- GPU target: **auto-detect + manual override**
- TUI framework: **Textual**

## Research findings (verified live)
- Remote index page `https://rocm.nightlies.amd.com/tarball-multi-arch/` is server-rendered HTML with a `<script>` block containing `const files = [{"name": "...", "mtime": 1785...}, ...]` — a plain JSON array, no JS execution/headless browser needed. Fetch with `urllib.request`, regex out the JSON, `json.loads`.
- Filename shape (verified against ~4100 real entries):
  `therock-dist-{platform}-{gfx_target}-{variant?}-{version}.tar.gz`
  - `platform`: `linux` | `windows`
  - `gfx_target`: e.g. `gfx1100`, `gfx110X`, `gfx94X`, `gfx950`, `multiarch`
  - `variant`: optional, 0+ hyphen-joined words (`all`, `dgpu`, `dcgpu`, `tests`, `dgpu-tests`, ...) — NOT fixed-arity
  - `version`: semver + optional nightly suffix, e.g. `7.15.0a20260630`
  - Robust parse: strip `therock-dist-` prefix and `.tar.gz` suffix, split remaining on `-`; first token = platform, last token = version, second token = gfx_target, any tokens in between joined with `-` = variant (empty variant allowed).
- Other index URLs exist for whl/deb/rpm/asan but are out of scope per user's artifact choice.

## Package layout
```
TheRockTui/
├── pyproject.toml
├── src/therock_tui/
│   ├── __init__.py
│   ├── __main__.py        # entry point, launches App
│   ├── models.py           # TheRockBuild dataclass + filename parser (pure, testable)
│   ├── remote.py           # fetch/parse remote index, filter/sort, streaming download w/ progress callback
│   ├── local.py            # scan a directory for local tarballs/extracted builds matching the same pattern
│   ├── gpu_detect.py       # best-effort local gfx target detection (rocminfo, fallback None)
│   └── app.py              # Textual App wiring Local/Remote screens together
└── tests/
    ├── test_models.py
    ├── test_remote.py
    ├── test_local.py
    └── test_gpu_detect.py
```

## Design details

**models.py**
- `TheRockBuild` frozen dataclass: `platform: str`, `gfx_target: str`, `variant: str`, `version: str`, `filename: str`, `mtime: float | None`
- `parse_therock_filename(name: str) -> TheRockBuild | None` — pure function implementing the parse rule above. Returns `None` for non-matching names (e.g. windows multiarch-tests entries, unrelated files) so callers can filter with `filter(None, ...)`.

**remote.py**
- `DEFAULT_INDEX_URL = "https://rocm.nightlies.amd.com/tarball-multi-arch/"`
- `fetch_remote_builds(fetch: Callable[[str], str] = _http_get, index_url: str = DEFAULT_INDEX_URL) -> list[TheRockBuild]` — injectable fetch function for testability (no real network in unit tests); extracts the `const files = [...]` JSON via regex, parses each entry with `parse_therock_filename`, drops unmatched.
- `download_build(build: TheRockBuild, dest_dir: Path, index_url: str, on_progress: Callable[[int, int], None] | None) -> Path` — streams via `urllib.request.urlopen`, writes chunks to `dest_dir / build.filename`, invokes progress callback with (bytes_read, total_bytes).

**local.py**
- `scan_local_directory(path: Path) -> list[TheRockBuild]` — non-recursive scan of `*.tar.gz` in `path` matched through `parse_therock_filename`; also detects extracted directories whose name (minus `.tar.gz`) matches the pattern, marking them distinctly (extra field or separate list) so UI can show "downloaded" vs "extracted".

**gpu_detect.py**
- `detect_local_gfx_target(run: Callable[[list[str]], str] = _run_subprocess) -> str | None` — runs `rocminfo`, regex-searches for `gfx[0-9a-fA-F]+`, returns first match or `None` on failure (binary missing, non-AMD system, etc). Injectable `run` for testability.

**app.py**
- Textual `App` with `TabbedContent`: **Local** tab and **Remote** tab.
  - Shared directory `Input` widget (path used both as scan target and download destination).
  - Local tab: "Scan" button → populates a `DataTable` from `scan_local_directory`.
  - Remote tab: on mount, background worker calls `fetch_remote_builds`; results in a `DataTable` (columns: version, gfx_target, variant, platform, date), filterable by gfx target (`Select` widget defaulting to `detect_local_gfx_target()` result if it matches an available target, else "All") and sorted by mtime descending. Selecting a row + pressing "Download" runs `download_build` in a threaded worker, updating a `ProgressBar`.

## Dependencies
`textual` only (stdlib covers networking/tarfile/regex/json). Add `pyproject.toml` with console-script entry point `therock-tui`.

## Tasks
- [x] Scaffold `pyproject.toml` + package skeleton
- [x] Implement `models.py` (dataclass + parser)
- [x] Implement `gpu_detect.py`
- [x] Implement `local.py`
- [x] Implement `remote.py` (fetch/parse/filter/sort + download w/ progress)
- [x] Implement `app.py` (Textual UI: Local tab, Remote tab, shared dir input, download+progress)
- [x] Implement `__main__.py`
- [x] Manual run verification (`python -m therock_tui`) — verified headless via `App.run_test()`: local scan found both a downloaded tarball and an extracted dir in a scratch dir; remote fetch loaded 4098 real builds with 19 gfx-filter options; `rocminfo` auto-detected `gfx1201` on this machine; `download_build` chunking/progress verified against a mocked HTTP response (real tarballs are multi-GB, unsuitable for a live smoke download)
- [ ] Ask user about unit tests (per `programming-python` / `planning-feature` skill) — `test_models.py`, `test_remote.py` (mocked fetch), `test_local.py`, `test_gpu_detect.py` (mocked subprocess)

## Notes
- No git repo currently in this directory — skip PR workflow; just implement in place. If user later wants git init/commit, handle separately.
- Version selection UI shows nightly date-stamped versions (e.g. `7.15.0a20260815`) since TheRock has no separate "stable release" tarball feed distinct from nightly per RELEASES.md.
