#!/usr/bin/env bash
# One-time setup on macOS, then launches the app.  Usage: bash setup-mac.sh
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null; then
  echo "Python 3.10+ is required. Install it from https://www.python.org/downloads/macos/ and run this again."
  exit 1
fi

python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e .

echo
echo "Setup done. Starting the app (next time run:  .venv/bin/apvd-gui )"
exec .venv/bin/apvd-gui
