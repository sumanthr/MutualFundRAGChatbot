#!/usr/bin/env bash
# Local / cron-friendly runner for the full Phase 1 ingest pipeline:
# scrape registry URLs → extract Groww SSR facts → chunk → embed → Chroma upsert.
#
# Usage:
#   ./scripts/run-ingest-scheduled.sh              # full index
#   ./scripts/run-ingest-scheduled.sh --dry-run   # fetch + chunk only (no embeddings/Chroma)
#
# Logs:
#   logs/ingest-run-<UTC-timestamp>.log  — this run
#   logs/ingest-scheduler.log          — append-only master log
#   logs/ingest-summary-<UTC>.json     — machine-readable summary (unless INGEST_SUMMARY_JSON set)
#
# Env:
#   CHROMA_PATH          — default ./chroma_data
#   INGEST_SUMMARY_JSON  — override summary output path

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi

CHROMA_PATH="${CHROMA_PATH:-$ROOT/chroma_data}"
RUN_TS="$(date -u +"%Y-%m-%dT%H%M%SZ")"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
RUN_LOG="$LOG_DIR/ingest-run-${RUN_TS}.log"
MAIN_LOG="$LOG_DIR/ingest-scheduler.log"
SUMMARY_JSON="${INGEST_SUMMARY_JSON:-$LOG_DIR/ingest-summary-${RUN_TS}.json}"

EXTRA=()
if [[ "${1:-}" == "--dry-run" ]]; then
  EXTRA+=(--dry-run)
fi

banner() {
  echo "$@" | tee -a "$RUN_LOG" | tee -a "$MAIN_LOG"
}

banner "========================================================================"
banner "Ingest scheduler run — ${RUN_TS} (UTC)"
banner "Repo: ${ROOT}"
banner "Python: ${PYTHON}"
banner "Chroma path: ${CHROMA_PATH}"
banner "Pipeline: (1) scrape HTML (2) SSR key facts  (3) chunk"
banner "          (4) embeddings  (5) Chroma replace per source URL"
banner "========================================================================"

set +e
set -o pipefail
"$PYTHON" -m mfr_phase1 \
  --chroma-path "$CHROMA_PATH" \
  -v \
  --summary-json "$SUMMARY_JSON" \
  "${EXTRA[@]}" 2>&1 | tee -a "$RUN_LOG" | tee -a "$MAIN_LOG"
EXIT="${PIPESTATUS[0]}"
set -e

banner "========================================================================"
banner "Finished with exit code ${EXIT} at $(date -u +"%Y-%m-%dT%H:%M:%SZ") UTC"
banner "Summary JSON: ${SUMMARY_JSON}"
banner "This run log: ${RUN_LOG}"
banner "Master log (append): ${MAIN_LOG}"
banner "========================================================================"

exit "$EXIT"
