# Test Plan: TheRock TUI

## Summary

**Change:** Textual TUI to scan a local directory for TheRock builds and to browse/download remote nightly TheRock tarballs.
**PR:** N/A (no git repo in this project yet)

## What to Test

### Automated Tests

No unit tests requested at this time (user opted to skip). If added later:

| Test | Description | Status |
|------|-------------|--------|
| `test_parse_therock_filename_*` | Parses well-formed filenames, rejects non-matching ones | ⬜ |
| `test_scan_local_directory_*` | Finds tarballs and extracted dirs, ignores unrelated files | ⬜ |
| `test_fetch_remote_builds_*` | Parses embedded JSON listing via injected fetch function | ⬜ |
| `test_download_build_*` | Streams to disk, invokes progress callback, via injected/mocked `urlopen` | ⬜ |
| `test_detect_local_gfx_target_*` | Parses gfx target from injected command output; None on failure | ⬜ |

### Manual Verification

| # | Scenario | Steps | Expected Result | ✓ |
|---|----------|-------|-----------------|---|
| 1 | Local scan — mixed contents | 1. Create dir with a `therock-dist-linux-gfx1100-dgpu-<ver>.tar.gz` file and a `therock-dist-linux-gfx1100-tests-<ver>` dir → 2. Enter path in directory field → 3. Local tab → Scan | Both rows listed, correctly tagged "downloaded" / "extracted" | ✅ |
| 2 | Local scan — bad path | Enter a non-existent path → Scan | Status shows "Not a directory: ..." | ⬜ |
| 3 | Remote listing loads | Launch app, switch to Remote tab | Table populates with real nightly builds shortly after mount | ✅ |
| 4 | GPU auto-detect | Launch app on a machine with `rocminfo` on PATH | GFX filter defaults to detected target if present in the remote list, else "All" | ✅ (verified `rocminfo` detection itself; exact-match-to-filter-bucket depends on chip vs. family naming, see Notes) |
| 5 | GFX filter | Change the GFX filter dropdown | Remote table re-renders to only matching rows | ⬜ |
| 6 | Download | Select a remote row → Download | Progress bar advances; status shows destination path on completion | ⬜ (chunking/progress verified against a mocked HTTP response; not exercised against a real multi-GB tarball — see Notes) |
| 7 | Download failure | Disconnect network or use bad path, then Download | Status shows "Download failed: ..." without crashing the app | ⬜ |

## Regression Check

N/A — new project, no prior features.

## Notes

- Remote tarballs are multi-GB; CI/manual runs should not perform full downloads. The mocked-response check (chunk writing + progress callback + final file size) stands in for a live download.
- GPU auto-detection returns the exact chip (e.g. `gfx1201`), but the remote index sometimes buckets several chips under a family wildcard (e.g. `gfx120X`). When they don't match exactly, the filter correctly falls back to "All" rather than mismatching silently.
- Requires `textual` (declared in `pyproject.toml`); install via `pip install -e .` (or `.[test]` if tests are added later).
