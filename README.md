# Mutual Fund RAG

Facts-only mutual fund FAQ assistant (RAG), implemented **phase by phase** per `docs/ragArchitecture.md`.

## Layout

| Path | Purpose |
|------|---------|
| `docs/` | Problem statement, architecture, edge cases |
| `phase0/` | Environment and repo bootstrap |
| `phase1/` | Ingestion: registry, **scraping**, chunking, **BGE-small** embeddings, **ChromaDB** |
| `phase2/` | CLI RAG + Groq (`mfr_phase2`) |
| `phase3/` | Guardrails CLI (`mfr_phase3`) |
| `phase4/` | **FastAPI + UI** (`mfr_phase4`) |
| `phase5/` | Eval, corpus stats, optional BM25+RRF demo (`mfr_phase5`) |

## Quick start (Phase 1 index)

```bash
cd /path/to/MutualFundRAG
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e .
python -m mfr_phase1 --chroma-path ./chroma_data
```

**Note:** Dependencies pin **`numpy<2`** for compatibility with current **PyTorch** wheels used by `sentence-transformers`. Use **Python 3.9+** (3.10+ recommended).

## Phase 2 — Ask questions (Groq LLM)

**You need a Groq API key only for Phase 2 factual answers** (not for Phase 1 indexing).

```bash
cp .env.example .env
# Set GROQ_API_KEY in .env (see .env.example)

python -m mfr_phase2 "What is the expense ratio for HDFC Mid Cap Fund?"
```

See **`phase2/README.md`** for routes, env vars, and CLI options.

## Phase 3 — Guardrails (recommended CLI)

PII redaction, expanded routing, AMFI/SEBI refusal links:

```bash
python -m mfr_phase3 "What is the minimum SIP for HDFC ELSS?"
```

See **`phase3/README.md`**.

## Phase 4 — Web API + UI

```bash
python -m mfr_phase4
```

Open **http://127.0.0.1:8000/** — chat UI, `POST /v1/chat/respond`, thread storage (SQLite). See **`phase4/README.md`**.

## Phase 5 — Evaluation and hybrid demo

```bash
python -m mfr_phase5 eval
python -m mfr_phase5 corpus-stats
pip install -e ".[phase5]"   # optional rank-bm25
python -m mfr_phase5 hybrid-demo "expense ratio mid cap"
```

See **`phase5/README.md`**.

This runs the **scraping service** (fetch allowlisted Groww URLs), then chunks, embeds with `BAAI/bge-small-en-v1.5`, and upserts into a **local Chroma** persist directory.

## Scheduled refresh (GitHub Actions)

A workflow runs **daily at 09:15 UTC** (see workflow file for **IST** option), executes the same pipeline, and uploads the `chroma_data` directory as an artifact. See `docs/ragArchitecture.md` §2.3.

## Compliance

Facts-only; no investment advice. v1 corpus: five Groww scheme pages (HTML). See `docs/problemStatement.md`.
