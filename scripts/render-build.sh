#!/usr/bin/env bash
# Render build — installs deps, uses committed deploy/chroma_data, warms embedding cache.
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

export HF_HOME="${HF_HOME:-$(pwd)/.cache/huggingface}"
export TRANSFORMERS_CACHE="$HF_HOME"
export SENTENCE_TRANSFORMERS_HOME="$HF_HOME"
mkdir -p "$HF_HOME" data

"$PY" -m pip install --upgrade pip setuptools wheel
"$PY" -m pip install -r requirements.txt
"$PY" -m pip install .

if [[ ! -d deploy/chroma_data ]] || [[ -z "$(ls -A deploy/chroma_data 2>/dev/null)" ]]; then
  echo "WARN: deploy/chroma_data missing — running build-time ingest (slow; may OOM on Free)."
  "$PY" -m mfr_phase1 --chroma-path ./deploy/chroma_data || {
    echo "Build-time ingest failed. Commit deploy/chroma_data from your laptop (see deploy/README.md)." >&2
    exit 1
  }
else
  echo "Using committed deploy/chroma_data ($(du -sh deploy/chroma_data | cut -f1))"
fi

EMBEDDING_MODEL="${EMBEDDING_MODEL:-BAAI/bge-small-en-v1.5}"
echo "Warming embedding model: $EMBEDDING_MODEL"
"$PY" -c "from mfr_phase1.embedding import embed_texts; embed_texts(['warmup'], model_name='${EMBEDDING_MODEL}')"
echo "Render build complete."
