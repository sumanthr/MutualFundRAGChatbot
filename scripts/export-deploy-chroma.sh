#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-$ROOT/chroma_data}"
DEST="$ROOT/deploy/chroma_data"
if [[ ! -d "$SRC" ]]; then
  echo "Missing source index: $SRC (run: python -m mfr_phase1 --chroma-path ./chroma_data)" >&2
  exit 1
fi
rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
cp -R "$SRC" "$DEST"
echo "Copied $SRC -> $DEST ($(du -sh "$DEST" | cut -f1))"
