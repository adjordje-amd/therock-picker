# Changelog

## 0.2.0

### Added
- TheRock Picker: Textual app to browse and download AMD TheRock (ROCm) nightly build tarballs.
- Local tab: scan a directory for downloaded/extracted TheRock builds.
- Remote tab: list nightly builds from rocm.nightlies.amd.com, filter by GPU target (auto-detected via `rocminfo` when available), and download a selected build with progress reporting.
- App version shown in the header, next to the app name.
- In-app update check against GitHub Releases, shown as a banner when a newer version is available. Press `u` to self-update via `pipx install --force`; restart the app afterward to pick it up.
