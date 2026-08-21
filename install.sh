#!/usr/bin/env bash
# Install TheRock tools as standalone commands on this system.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if ! command -v pipx >/dev/null 2>&1; then
    echo "pipx not found. Install it first: https://pipx.pypa.io/stable/installation/" >&2
    exit 1
fi

echo "Installing therock-picker (pipx)..."
pipx install --force .

echo
echo "Done. Run with:"
echo "  therock-picker"
