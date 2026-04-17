# Chunking, Embedding, and Vector Database Architecture

This document specifies how raw page text becomes searchable vectors for the Mutual Fund FAQ assistant. It aligns with the **current project scope**: **HTML-only** corpus (no PDFs in v1), **five in-scope scheme pages on Groww**, **embedding model `BAAI/bge-small-en-v1.5`**, and **ChromaDB running locally** for persistence and similarity search.

For the full system (ingestion, retrieval orchestration, guardrails, UI, **phased delivery**), see **`ragArchitecture.md`** §16. For **evaluation** scenarios (ingest/chunk/embed/Chroma failures), see **`edgeCases.md`** (E6–E8).

---

## 0) Alignment with `problemStatement.md` and `ragArchitecture.md`

| `problemStatement.md` topic | How this doc + `ragArchitecture.md` satisfy it (v1) |
|-----------------------------|--------------------------------------------------------|
| Curated corpus | **Five Groww scheme URLs** ingested as HTML only; registry + allowlist in `ragArchitecture.md` §2.1, §3.2. |
| Official AMC / AMFI / SEBI sources | **Target state** in problem statement; **v1** uses Groww as referenced UI context—**refusal/education** links use AMFI/SEBI. Expansion = add AMC/AMFI/SEBI URLs and PDFs in later phases. |
| Facts-only, one citation, footer | Chunk metadata supplies `source_url` and `ingested_at` for citation + “last updated”; formatter in main architecture §6. |
| No PDFs (project choice v1) | No PDF stage here; PDF = future new collection per §6 below. |
| Category diversity (3–5 schemes) | Five HDFC schemes (large-cap, mid-cap, focused, equity, ELSS) per `ragArchitecture.md` §2.1 table. |

**Single source of truth:** Numeric chunking defaults live in **§2.2** below; `ragArchitecture.md` §4.1 **references** this section—avoid duplicating conflicting numbers there.

---

## 1) Pipeline Overview

```text
 Groww scheme URL |
         v
  +--------------+
  | Fetch HTML   |  HTTP GET, timeouts, retries, respect robots.txt
  +------+-------+
         |
         v
  +--------------+
  | Parse DOM    |  Strip nav/ads/chrome; keep main content + headings
  +------+-------+
         |
         v
  +--------------+
  | Normalize    |  Plain text, tables -> lines; dedupe whitespace
  +------+-------+
         |
         v
  +--------------+
  | Chunk        |  Character/token windows + overlap + metadata
  +------+-------+
         |
         v
  +--------------+
  | Embed        |  bge-small-en-v1.5 (same model for docs & queries)
  +------+-------+
         |
         v
  +--------------+
  | Upsert       |  Chroma collection + ids + metadata
  +--------------+
```

**Invariant:** Every chunk stored in Chroma carries enough metadata to (a) filter by scheme, (b) cite the canonical Groww URL, and (c) record ingest time for the “last updated” footer.

### 1.1 Scheduled refresh (scraping service + scheduler)

Fresh vectors require **re-running** this pipeline after pages change. **Scheduler:** **GitHub Actions** runs **daily at 09:15 UTC** and invokes the same **scraping service** as local dev (`python -m mfr_phase1`); see **`ragArchitecture.md` §2.3** and **`.github/workflows/ingest-scheduled.yml`**. The workflow uploads **`chroma_data/`** as an artifact. For **09:15 IST (Asia/Kolkata)**, use cron **`45 3 * * *`** (UTC).

---

## 2) Chunking Architecture

### 2.1 Goals

- Preserve **scheme-specific** facts (expense ratio, exit load, min SIP, benchmark, riskometer, etc.) inside retrievable units.
- Avoid splitting mid-sentence where possible; prefer **paragraph and section** boundaries.
- Keep chunks small enough for precise retrieval but large enough for context (typical RAG sweet spot for small embedding models).

### 2.2 Recommended parameters (v1)

| Parameter | Suggested value | Rationale |
|-----------|-----------------|-----------|
| Primary split | By HTML heading hierarchy (`h1`–`h3`) then by paragraph | Matches how fund pages group facts |
| Max chunk size | **512** characters (approx.) or **~256–384 tokens** equivalent | Fits `bge-small-en-v1.5` context; keeps answers localized |
| Overlap | **64–128** characters or **~40–80** tokens equivalent | Reduces boundary loss for facts at section edges |
| Min chunk size | **80–120** characters | Drop or merge tiny fragments (e.g., lone labels) |
| Table handling | Flatten each table to lines: `Label: value` | Improves retrieval of numeric facts |

Adjust character limits after inspecting real Groww HTML; tokenizers differ, so treat token counts as approximate unless you measure with the model’s tokenizer.

### 2.3 Chunk metadata (required)

Attach to every chunk before embedding:

| Field | Description |
|-------|-------------|
| `chunk_id` | Stable id: hash(`source_url` + chunk index + `content_hash`) |
| `source_url` | Canonical scheme page URL (one of the five in-scope URLs) |
| `scheme_slug` | e.g. `hdfc-mid-cap-fund-direct-growth` |
| `fund_name` | Human-readable name if parsed |
| `section_title` | Nearest heading text |
| `chunk_index` | Order within document |
| `ingested_at` | ISO-8601 timestamp |
| `content_hash` | Hash of normalized chunk text |

Optional but useful:

| Field | Description |
|-------|-------------|
| `source_domain` | `groww.in` |
| `page_title` | `<title>` or main heading |

### 2.4 Deduplication and re-ingestion

- On each ingest run, compute `content_hash` per chunk.
- **Upsert** by `chunk_id` (or delete+insert for that `source_url` batch) so stale chunks do not accumulate.
- Store **`ingested_at`** at batch level for “Last updated from sources” in the assistant.

### 2.5 Query-time chunk use

- Retrieve top-k chunks (e.g. k=5–10) then **compress** to the best 3–5 for the LLM context window.
- Prefer chunks whose `scheme_slug` matches explicit user mention or thread context.

---

## 3) Embedding Architecture (`BAAI/bge-small-en-v1.5`)

### 3.1 Model choice

- **Model:** `BAAI/bge-small-en-v1.5` ([Hugging Face model card](https://huggingface.co/BAAI/bge-small-en-v1.5))
- **Role:** Dense semantic embeddings for **both** document chunks and **user queries**.
- **Properties (typical):** English-focused, small footprint, suitable for local CPU/GPU; **embedding dimension 384** (verify in your runtime with a single encode pass).

### 3.2 Implementation pattern

Use **Sentence Transformers** (or equivalent) for a single, consistent API:

- Load model once at indexer and API startup (or lazy-load with a process-level singleton).
- **Encode documents** in batches (e.g. 16–64 depending on RAM) during indexing.
- **Encode queries** one-by-one or in small batches at request time.

### 3.3 Normalization

- Apply **L2 normalization** on embeddings if your distance metric expects it. Chroma’s default similarity is often **cosine**; normalized vectors make cosine dot-product comparable to standard practice.
- **Same preprocessing** for corpus and queries: trim whitespace, collapse excessive newlines; do not apply aggressive stemming (let the model handle semantics).

### 3.4 Query instructions (optional)

Larger BGE models sometimes use instruction prefixes; **`bge-small-en-v1.5` is typically used without a special query prefix** in Sentence Transformers examples. If you add experimental prefixes, apply them **only** at query time and benchmark retrieval quality—do not mix prefixed queries with unprefixed document embeddings without re-embedding the corpus.

### 3.5 Performance notes

- **CPU:** acceptable for demo scale (five pages, hundreds of chunks).
- **GPU:** speeds up batch indexing and high QPS.
- Cache embeddings for unchanged chunks (via `content_hash`) to avoid recomputation on re-runs.

---

## 4) Vector Database Architecture (ChromaDB, local)

### 4.1 Why Chroma local

- **Embedded / local persistence** for development and lightweight deployment.
- **Metadata filtering** (e.g. `WHERE scheme_slug = ...`) combined with vector similarity.
- Simple Python client; fits a FastAPI-style stack.

### 4.2 Deployment shape

- Run Chroma **in-process** (default Python client with persistent directory) or **Chroma server** on `localhost` if you prefer separating processes.
- Persist data to a directory such as `./chroma_data` (gitignored) so indexes survive restarts.

### 4.3 Collection design

- **One collection** for this project is sufficient initially, e.g. `mutual_fund_faq_groww_v1`.
- **Document id:** use `chunk_id` (deterministic) for idempotent upserts.
- **Embedding:** store the 384-dimensional vector from `bge-small-en-v1.5` (confirm dimension in your environment).
- **Document field:** store raw chunk text (or a short preview + pointer; full text in metadata is fine for small corpora).

### 4.4 Metadata in Chroma

Store the chunk metadata listed in §2.3 so filters are possible:

- Example filter: `{"scheme_slug": "hdfc-elss-tax-saver-fund-direct-plan-growth"}`.
- Example filter: `{"source_url": "<exact Groww URL>"}`.

Keep metadata values **strings, numbers, or bools** per Chroma’s typing rules; avoid nested objects unless your client version supports them explicitly.

### 4.5 Similarity search

- Use **cosine distance** (or Chroma’s `l2` / `ip` as appropriate) consistently with whether you L2-normalize vectors.
- Typical query: `query_embeddings=[q_vec]`, `n_results=k`, `where={...}` for scheme scoping.

### 4.6 Operational concerns

- **Backup:** zip the persistence directory for reproducibility.
- **Versioning:** bump collection name (e.g. `_v2`) when you change chunking or embedding model—**never** mix vectors from different models in one collection.
- **Corruption / migration:** if the store corrupts, re-run ingest from source URLs (small corpus, fast recovery).

---

## 5) End-to-end consistency checklist

1. **One embedding model** for index and query: `bge-small-en-v1.5`.
2. **One Chroma collection** per embedding + chunking version.
3. Every chunk has **`source_url`** matching one of the five in-scope Groww pages (until corpus expands).
4. Re-ingest deletes or upserts so **orphan chunks** do not linger.
5. Log **ingest batch timestamp** for user-visible “last updated” strings.

---

## 6) Future extensions (out of Phase 1–2 core)

- **PDFs** (factsheet / KIM / SID): add a PDF text extraction stage; chunk with page + section metadata; **new collection** or version suffix because layout differs (problem statement corpus expansion).
- **Hybrid retrieval + reranking:** add BM25 (e.g. `rank_bm25`) over the same chunk texts; fuse with Chroma scores; optional cross-encoder on top-k — scheduled in **`ragArchitecture.md` §4.3 Phase 5** and **§16 Phase 5**.

---

## 7) Phased implementation mapping (synced with `ragArchitecture.md` §16)

| Phase | This document — deliverables |
|-------|------------------------------|
| **0** | Dependencies and config: Chroma persist path, model `BAAI/bge-small-en-v1.5`, allowlisted URL list in config (no index yet). |
| **1** | Full pipeline §1: fetch → parse → normalize → **chunk (§2)** → **embed (§3)** → **Chroma upsert (§4)**; §5 checklist; handle **E6–E8** in `edgeCases.md`. |
| **2** | Query-time: embed user query (§3); Chroma similarity + metadata `where` (§4.4–4.5); top-k §2.5. LLM answers use **Groq** (`GROQ_API_KEY` in `.env` — see `.env.example`); no change to chunking model unless retrieval audit requires it. |
| **3–4** | No change to core chunk/embed schema; Phase 3 wraps answers with PII sanitize + refusal link policy (`mfr_phase3`). Phase 4 exposes the same index via HTTP + optional `scheme_slug` filter. Ensure `ingested_at` and `source_url` exposed to the formatter for footer and citations. |
| **5** | Optional: **`mfr_phase5 hybrid-demo`** — BM25 + vector RRF over exported Chroma docs (`pip install -e ".[phase5]"`). Rebuild collection on chunking/embedding version change. Scheduled re-ingest remains **GitHub Actions** (§1.1 / `ragArchitecture.md` §2.3). Run **`mfr_phase5 corpus-stats`** for ingest freshness. |

This document is the reference for implementers wiring **chunking → `bge-small-en-v1.5` → ChromaDB** in the Mutual Fund RAG project.
