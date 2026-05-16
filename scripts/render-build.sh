#!/usr/bin/env bash
# Render build — avoids YAML eating `pip install .` and empty `pip install` errors.
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "No python interpreter found" >&2
  exit 1
fi

"$PY" -m pip install --upgrade pip setuptools wheel
"$PY" -m pip install -r requirements.txt
"$PY" -m pip install .
