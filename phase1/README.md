# Phase 1 — Source registry, scraping, chunking, embedding, Chroma

**Goal:** Deterministic index from the five allowlisted Groww scheme pages (`docs/ragArchitecture.md` §16).

## Package

Python package **`mfr_phase1`** lives under this folder (`phase1/mfr_phase1/`). Install from repo root:

```bash
pip install -e .
```

## CLI (scraping + index build)

```bash
python -m mfr_phase1 --chroma-path ./chroma_data
```

Options:

- `--chroma-path` — Chroma persist directory (default: `./chroma_data`).
- `--collection` — Collection name (default: `mutual_fund_faq_groww_v1`).
- `--model` — Sentence Transformers model id (default: `BAAI/bge-small-en-v1.5`).
- `--dry-run` — Fetch and chunk only; no embeddings or Chroma writes.

## What it does

1. **Source registry** — Five HDFC Groww URLs; allowlist enforced before any HTTP GET.
2. **Scraping service** — `httpx` fetch with retries, timeouts, polite `User-Agent`; HTML → normalized text (`scrape.py`).
3. **Chunking** — Heading/paragraph-aware splits, table flattening, overlap (`chunking.py`); see `docs/ragChunkingEmbeddingVectorDb.md` §2.
4. **Embedding** — `BAAI/bge-small-en-v1.5` via Sentence Transformers (`embedding.py`).
5. **Vector DB** — Chroma persistent client; per-URL delete then upsert to avoid orphan chunks (`vectorstore.py`).

## Scheduling

Daily refresh is **not** implemented inside this package: **GitHub Actions** calls this same CLI (see `.github/workflows/ingest-scheduled.yml` and `docs/ragArchitecture.md` §2.3).

## Exit criteria

- [ ] Non-empty Chroma collection after a successful run.
- [ ] Chunks present for all five `source_url` values.
- [ ] Metadata includes `ingested_at` (ISO-8601) for footer use in later phases.
