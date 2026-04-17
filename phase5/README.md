# Phase 5 — Evaluation, metrics, optional hybrid retrieval

**Goal:** `docs/ragArchitecture.md` §11, §16 Phase 5 — systematic checks against `docs/edgeCases.md`, corpus freshness signals, optional BM25 + RRF demo.

## Commands

```bash
pip install -e .

# Regression cases (bundled cases.json). Skips Groq-heavy cases if GROQ_API_KEY is unset.
python -m mfr_phase5 eval

# Run all cases including factual (needs GROQ_API_KEY + chroma index)
python -m mfr_phase5 eval --include-groq

# JSON report for CI
python -m mfr_phase5 eval --include-groq --json-out eval-report.json

# Chroma ingest timestamp range (stale-source awareness, §13)
python -m mfr_phase5 corpus-stats

# Optional: BM25 + vector fusion demo (install extra)
pip install -e ".[phase5]"
python -m mfr_phase5 hybrid-demo "expense ratio HDFC mid cap"
```

## What gets checked

- **Format:** footer date, single HTTP URL in `formatted_message`, ≤3 sentences in answer body, valid `citation_url`.
- **Expectations per case:** `route`, `response_type`, Groww vs regulatory host when specified.
- **Cases** live in **`mfr_phase5/cases.json`** (IDs mirror `docs/edgeCases.md` where possible).

## Re-ingestion

Scheduled ingest remains **GitHub Actions** (`.github/workflows/ingest-scheduled.yml`). Use **`corpus-stats`** after a run to confirm `ingested_at_max`.

## Limitations (v1 corpus)

- Five **Groww** scheme pages only; no AMC PDFs — document in project README / problem statement alignment.

## Next

Hardening: expand `cases.json`, add golden retrieval labels for precision@k, wire hybrid into production retrieval behind a flag if needed.
