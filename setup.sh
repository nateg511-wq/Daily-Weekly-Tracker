#!/usr/bin/env bash
# One-time setup: create a local venv and install dependencies. Idempotent.
set -euo pipefail
cd "$(dirname "$0")"
PY=python3
command -v "$PY" >/dev/null || { echo "python3 not found — install Python 3.10+"; exit 1; }
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' \
  || { echo "Python 3.10+ required (found $("$PY" -V))"; exit 1; }
[ -d .venv ] || "$PY" -m venv .venv
BIN=.venv/bin; [ -d .venv/Scripts ] && BIN=.venv/Scripts   # Git-Bash/Windows layout
"./$BIN/pip" install --quiet --upgrade pip
"./$BIN/pip" install --quiet -r requirements.txt
echo "Setup complete. Run: ./$BIN/python run.py all"
