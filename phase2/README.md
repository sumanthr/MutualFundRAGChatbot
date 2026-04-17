# Phase 2 — Retrieval, Groq LLM answer, response formatting

**Goal:** Chroma **vector retrieval** + **Groq** chat completion + **validator** (architecture §4.3 Phase 2, §6).

## When you need `GROQ_API_KEY`

| Phase | Needs Groq API key? |
|-------|---------------------|
| **1** — Index (`python -m mfr_phase1`) | **No** — local `sentence-transformers` only |
| **2** — Chat (`python -m mfr_phase2`) | **Yes** — for **factual** RAG answers after retrieval |
| **2** — Advisory / empty-query / performance-limited (template paths) | **No** — handled without LLM |

Copy **`.env.example`** → **`.env`** and set **`GROQ_API_KEY`**. Optional: `GROQ_MODEL`, `CHROMA_PATH`, `CHROMA_COLLECTION`, `EMBEDDING_MODEL`.

## CLI

From repo root (after `pip install -e .`):

```bash
cp .env.example .env
# edit .env — set GROQ_API_KEY

python -m mfr_phase2 "What is the expense ratio for HDFC Mid Cap Fund?"
python -m mfr_phase2 --scheme-slug hdfc-mid-cap-fund-direct-growth -q "Minimum SIP amount?"
python -m mfr_phase2 --json "Exit load for HDFC Equity Fund"
```

Requires a non-empty **Phase 1** Chroma index at `CHROMA_PATH` (default `./chroma_data`).

## Package layout

| Module | Role |
|--------|------|
| `settings.py` | Loads `.env` (`python-dotenv`) |
| `routing.py` | Lightweight query route (advisory / performance / factual) |
| `retrieve.py` | Embed query + Chroma `query` |
| `groq_client.py` | Groq OpenAI-compatible `/chat/completions` |
| `prompts.py` | System + user prompt (JSON output, facts-only) |
| `validator.py` | Sentence count, citation in context, format |
| `respond.py` | `answer_query()` orchestration |

## Exit criteria (Phase 2)

- [ ] Factual question returns grounded answer + **one** Groww `source_url` + footer.
- [ ] Advisory question returns refusal + AMFI education link + footer **without** calling Groq.
- [ ] Performance-style question returns limited template + scheme page link.
- [ ] `GROQ_API_KEY` missing → clear error **only** on factual path needing LLM.

## Next

**Phase 3** — use **`python -m mfr_phase3`** for production-style guardrails (PII, expanded router, AMFI/SEBI refusal links). See `../phase3/README.md`.
