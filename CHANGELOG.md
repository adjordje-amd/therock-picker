# Changelog

## 0.4.3

### Changed
- Remote tab merges AMD nightlies from both tarball indexes: `nightly.repo.amd.com` for 2026-08-23 onward and `rocm.nightlies.amd.com` for earlier builds, and downloads each tarball from the matching host.

## 0.4.2

### Fixed
- The TheRock root path (config file, TUI input) was not stripped of leading/trailing whitespace; a value like `" /home/user/therock"` was treated as a relative path, causing downloads/extraction to land under a bogus directory literally named `" "`. Path is now trimmed on load, save, and read from the TUI input.

## 0.4.1

### Fixed
- Extraction wrote directly into the final versioned directory; an interrupted extraction left a partial directory that was subsequently treated as a valid installed build. Extraction now happens in a temporary directory and is atomically renamed into place only on success.
- The delete confirmation dialog had a broken shape caused by `width: 100%` on its message inside an `auto`-width dialog (undefined percent basis); the dialog now has a fixed width.

### Changed
- Raised the per-read socket timeout from 60s to 300s to reduce retry churn on slow (but not dead) network stretches during large downloads.

## 0.4.0

### Changed
- Replaced the in-app update banner and `u` keybinding with a `--update` CLI flag (`therock-picker --update`) that checks GitHub Releases and self-updates via pipx, then exits.

## 0.3.1

### Fixed
- Extraction of official TheRock tarballs could fail with `... would link to ... which is outside the destination` because Python's strict `data_filter` rejected the tarballs' baked-in absolute symlinks; extraction now uses `fully_trusted_filter` since these are official AMD-published builds.

## 0.3.0

### Added
- Local tab: "Delete" button to remove a selected build's files from disk, behind a confirmation dialog.
- Remote tab: each build row shows a clickable direct-download URL for manual/out-of-band downloading.

### Fixed
- Downloads that were truncated by an early-closed connection were silently treated as complete, producing incomplete `.tar.gz` archives; downloads are now verified against `Content-Length` and retried/resumed if short.
- A failure to delete the source `.tar.gz` after extraction was incorrectly reported as "Extraction failed" and skipped updating the `selected` symlink; extraction success and tarball cleanup are now handled independently.

## 0.2.0

### Added
- TheRock Picker: Textual app to browse and download AMD TheRock (ROCm) nightly build tarballs.
- Local tab: scan a directory for downloaded/extracted TheRock builds.
- Remote tab: list nightly builds from rocm.nightlies.amd.com, filter by GPU target (auto-detected via `rocminfo` when available), and download a selected build with progress reporting.
- App version shown in the header, next to the app name.
- In-app update check against GitHub Releases, shown as a banner when a newer version is available. Press `u` to self-update via `pipx install --force`; restart the app afterward to pick it up.
