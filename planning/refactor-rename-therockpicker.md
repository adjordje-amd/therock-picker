# Refactor: Rename project TheRockTui -> TheRockPicker

## Goal
Rename project/package/command from `therock-tui`/`therock_tui`/`TheRockTui` to `therock-picker`/`therock_picker`/`TheRockPicker`. Pure rename, no behavior change (except persisted config dir name, called out below).

## Code Smells Identified
N/A (pure rename, not a code-smell refactor).

## Refactoring Strategy
Mechanical find/replace across identifiers + directory rename. No design pattern or STL changes needed.

## Tasks
- [x] `git mv src/therock_tui src/therock_picker` (no git repo — plain `mv`)
- [x] Rename class `TheRockTuiApp` -> `TheRockPickerApp` in app.py, __main__.py
- [x] Update all `from therock_tui...`/`import therock_tui` to `therock_picker` in package files
- [x] pyproject.toml: `name`, console-script `therock-tui` -> `therock-picker`, `therock_tui.__main__:main` -> `therock_picker.__main__:main`
- [x] config.py: `_APP_DIR_NAME` "therock-tui" -> "therock-picker" (config dir moves; old settings at ~/.config/therock-tui won't carry over — acceptable for rename)
- [x] install.sh: update installed command name/messages
- [x] README.md: title, install/usage command references
- [x] Remove stale `src/therock_tui.egg-info` and `build/` (generated artifacts, regenerate on next install)
- [x] Update planning/docs-readme.md note if needed
- [ ] Verify: `pip install -e .` then `therock-picker --help`/run works (deferred — no venv rebuild requested)

## Testability Improvements
N/A

## Changelog
### Changed
- Renamed project from TheRock TUI to TheRock Picker (package `therock_tui` -> `therock_picker`, command `therock-tui` -> `therock-picker`).

## Notes
No git history to preserve via `git mv`; plain filesystem move used. CHANGELOG.md historical "Unreleased" entries left as-is except new rename entry appended.
