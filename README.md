# TheRock Picker

Terminal UI (Textual) to browse local and remote AMD [TheRock](https://github.com/ROCm/TheRock) (ROCm) nightly build tarballs, download one, extract it, and mark it as the active version via a symlink.

## Features

- **Local tab** — scans a `versions/` directory for downloaded (`.tar.gz`) and extracted builds, and lets you pick one as the active version.
- **Remote tab** — lists nightly tarballs from both AMD indexes ([2026-08-23 and later](https://nightly.repo.amd.com/rocm/core/tarball/) and [2026-08-22 and earlier](https://rocm.nightlies.amd.com/tarball-multi-arch/)), filterable by GPU target and platform (auto-detected via `rocminfo` when available), with download + extract + progress reporting. Downloads use the host that published that night's tarball.

## Install

Requires [pipx](https://pipx.pypa.io/stable/installation/).

```bash
./install.sh
```

This uses [pipx](https://pipx.pypa.io/) to install the app into its own isolated venv and expose the `therock-picker` command on your `PATH` (e.g. `~/.local/bin`) — no need to activate a venv to run it afterward.

## Usage

```bash
therock-picker
```

- **TheRock path** (top input): root directory for builds. Defaults to `~/therock`, persisted in `~/.config/therock-picker/config.json` (or `%APPDATA%\therock-picker` on Windows). Contains a `versions/` subdirectory for downloads/extractions and a `selected` symlink pointing at the active version.
- **Local tab**: click **Scan directory** to list builds already in `versions/`, select a row, click **Select** to point the `selected` symlink at an extracted build.
- **Remote tab**: builds load automatically on startup; filter by GPU/platform, select a row, click **Download** to fetch, extract, and activate it (updates the `selected` symlink automatically).
- Press `q` to quit.

### Using the selected build

Point `ROCM_PATH` at the `selected` symlink, and prepend its `bin`/`lib` to `PATH`/`LD_LIBRARY_PATH`, so ROCm tools pick up the active build. Add to your shell rc file (e.g. `~/.zshrc`):

```bash
export ROCM_PATH=$HOME/therock/selected
export PATH=$ROCM_PATH/bin:$PATH
export LD_LIBRARY_PATH=$ROCM_PATH/lib:$ROCM_PATH/lib64:$LD_LIBRARY_PATH
```

(adjust `$HOME/therock` if you configured a different TheRock path).

## Development

```bash
pip install -e ".[test]"
pytest
```

Package layout: `src/therock_picker/` — `models.py` (build parsing), `remote.py` (fetch/download), `local.py` (directory scan/symlink), `gpu_detect.py` (GPU detection), `config.py` (settings), `app.py` (Textual UI).
