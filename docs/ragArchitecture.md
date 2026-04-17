# Mutual Fund FAQ Assistant - Detailed RAG Architecture

## 1) Goal and Design Principles

Build a **facts-only** Retrieval-Augmented Generation (RAG) assistant for mutual fund FAQs that:
- answers objective, verifiable questions **grounded in a curated corpus** (see **§2.1 In-scope corpus**),
- refuses advisory/non-factual prompts,
- always returns concise responses (<= 3 sentences),
- includes exactly one citation URL and a "last updated" footer,
- supports multiple independent chat threads concurrently.

Core principles:
- **Compliance first**: no advice, no comparisons, no inferred recommendations.
- **Grounded outputs**: every factual answer must come from retrieved evidence.
- **Deterministic formatting**: enforce output schema and post-generation checks.
- **Traceability**: each answer is linked to a single source and ingestion timestamp.

**Document map (keep in sync):**
- `problemStatement.md` — product requirements, compliance, deliverables.
- `ragChunkingEmbeddingVectorDb.md` — scrape → chunk → `bge-small-en-v1.5` → **ChromaDB (local)**.
- `edgeCases.md` — evaluation and regression catalog (IDs E1.x–E15.x).
- `.github/workflows/ingest-scheduled.yml` — **scheduler** (daily **09:15 UTC**) calling the Phase 1 scraping + index CLI.
- `phase3/mfr_phase3/` — **Phase 3** guardrails CLI (`python -m mfr_phase3`).
- `phase4/mfr_phase4/` — **Phase 4** FastAPI + UI (`python -m mfr_phase4`).
- `phase5/mfr_phase5/` — **Phase 5** eval + corpus stats + optional hybrid demo (`python -m mfr_phase5`).
- **Implementation order:** §16 phased plan below.

---

## 2) High-Level Architecture

### 2.1 In-scope corpus (current phase)

**Corpus:** Five HDFC scheme pages on **Groww** (HTML only). **No PDFs** are ingested in this phase; PDF support (factsheet / KIM / SID) is a future extension.

| Scheme (representative) | URL |
|-------------------------|-----|
| HDFC Mid Cap Fund – Direct – Growth | `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth` |
| HDFC Equity Fund – Direct – Growth | `https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth` |
| HDFC Focused Fund – Direct – Growth | `https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth` |
| HDFC ELSS Tax Saver – Direct – Growth | `https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth` |
| HDFC Large Cap Fund – Direct – Growth | `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth` |

**Citation rule for factual answers:** The single citation link should be the **Groww scheme URL** from which the supporting chunk was retrieved (one of the URLs above), unless the response path is **refusal / education-only**, in which case use one **AMFI or SEBI** educational link per the problem statement.

**Compliance note:** Groww pages are third-party presentation of fund data; the assistant remains **facts-only, no advice**. When the corpus expands to AMC-hosted documents, tighten allowlists and citations accordingly.

### 2.2 RAG stack (current phase)

| Stage | Technology / behavior |
|-------|---------------------|
| **Scraping / fetch** | HTTP GET per allowlisted URL; timeouts, retries; **respect `robots.txt` and rate limits**; optional polite `User-Agent` |
| **Parsing** | **HTML only** (DOM extraction, boilerplate removal); **no PDF pipeline** in v1 |
| **Chunking** | Section/paragraph-aware splits, overlap, table flattening; see `ragChunkingEmbeddingVectorDb.md` |
| **Embedding** | **`BAAI/bge-small-en-v1.5`** (same model for documents and queries) |
| **Vector database** | **ChromaDB, local persistence** (e.g. on-disk directory; optional local server) |
| **Retrieval** | Similarity search over Chroma + **metadata filters** (`scheme_slug`, `source_url`) |

Detailed parameters for chunking, embeddings, and Chroma collections are in **`docs/ragChunkingEmbeddingVectorDb.md`**.

### 2.3 Scheduler service and scraping service (operations)

| Component | Responsibility |
|-----------|----------------|
| **Scraping service** | Fetches **only** allowlisted registry URLs (`groww.in`, five scheme paths), parses HTML, normalizes text, hands off to chunking → embedding → Chroma upsert. Implemented as the **Phase 1** Python module `mfr_phase1` (CLI: `python -m mfr_phase1`). |
| **Scheduler service** | Triggers a fresh ingest on a fixed wall-clock schedule so the vector index reflects **latest** page content. **Implementation: GitHub Actions** (no separate daemon in v1). |

**Schedule:** The workflow **`.github/workflows/ingest-scheduled.yml`** runs **every day at 09:15 UTC** (`cron: '15 9 * * *'`). To run the same job at **09:15 IST (Asia/Kolkata)**, use **`45 3 * * *`** (UTC) instead. **`workflow_dispatch`** is enabled for manual runs.

**CI artifact:** The workflow uploads the persisted **`chroma_data/`** directory (and an ingest summary JSON) as **GitHub Actions artifacts** for download or downstream deployment. Ephemeral runners do not keep local disk between runs; production deployments should copy artifacts to durable storage or rebuild on the host.

**Compliance:** Scraping must respect **`robots.txt`**, rate limits, and site terms; the scraper uses a fixed **User-Agent** string (see `mfr_phase1.scrape`).

```text
                       +-----------------------------+
                       | In-scope Groww scheme URLs   |
                       | (5 HTML pages, no PDFs v1)   |
                       +-------------+---------------+
                                     |
                                     v
                    +----------------+----------------+
                    | Ingestion + Validation Pipeline |
                    | - URL allowlist/domain checks   |
                    | - HTML fetch + parse (scraping) |
                    | - Metadata extraction            |
                    +----------------+----------------+
                                     |
                                     v
                         +-----------+-----------+
                         | Chunking + Embedding  |
                         | bge-small-en-v1.5     |
                         | + Citation metadata   |
                         +-----------+-----------+
                                     |
                                     v
                   +-----------------+------------------+
                   | ChromaDB (local) + metadata |
                   | (chunk_id, scheme, source_url,    |
                   |  ingested_at)                     |
                   +-----------------+------------------+
                                     ^
                                     |
               +---------------------+----------------------+
               | Retrieval Orchestrator                     |
               | - Query classifier (factual/advisory)      |
               | - Chroma vector retrieval (+ filters)      |
               | - Optional: hybrid + rerank (Phase 5) |
               | - Context pack builder                     |
               +---------------------+----------------------+
                                     |
                                     v
                        +------------+------------+
                        | Answer Generator (LLM)  |
                        | + Policy Guardrails     |
                        +------------+------------+
                                     |
                                     v
                   +-----------------+------------------+
                   | Response Validator + Formatter     |
                   | - <=3 sentences                    |
                   | - exactly 1 citation               |
                   | - "Last updated..." footer         |
                   +-----------------+------------------+
                                     |
                                     v
                       +-------------+-------------+
                       | Minimal UI + Thread Store |
                       | Multi-conversation support |
                       +---------------------------+
```

---

## 3) Data Layer Architecture

### 3.1 Source Registry
Maintain a curated registry. **Current phase:** five Groww scheme URLs (§2.1). **Future:** expand toward 15–25 URLs (AMC, AMFI, SEBI) per the broader problem statement.

Registry fields:
- `source_id`
- `url`
- `domain` (must be in allowlist)
- `source_type` (`factsheet`, `KIM`, `SID`, `faq`, `amfi_guidance`, `sebi_guidance`, `statement_guide`, `tax_guide`)
- `scheme_name` (nullable for generic guidance pages)
- `amc_name`
- `category` (large-cap / flexi-cap / ELSS / etc.)
- `is_active`
- `last_crawled_at`
- `last_modified_at` (if available from HTTP headers/content)

### 3.2 Domain and URL Policy
**Current phase allowlist (ingestion):**
- `groww.in` — **only** the five mutual-fund scheme paths listed in §2.1 (deny all other paths by default).

**Allowlist for refusal / educational links (no ingestion required):**
- `amfiindia.com`, `sebi.gov.in` (and other official regulator/education pages as approved).

**Future corpus expansion:**
- AMC official domains, AMFI/SEBI document URLs, etc., with the same strict allowlist + registry pattern.

Reject:
- any URL not in the registry; aggregators and blogs outside policy.

### 3.3 Parsing and Normalization
**Current phase:**
- **HTML only:** scheme detail pages on Groww (structured sections, tables, key metrics).

**Future:**
- PDF documents (factsheet, KIM, SID) when the project adds a PDF extraction stage.

Normalization output:
- clean text blocks,
- tables converted to key-value text rows (especially for expense ratio/exit load/min SIP),
- section headers retained as metadata.

### 3.4 Metadata Schema per Chunk
Each chunk must store:
- `chunk_id`, `doc_id`, `source_id`,
- `source_url` (canonical URL),
- `scheme_name`, `amc_name`, `source_type`,
- `section_title`,
- `effective_date` (if found in document),
- `ingested_at`,
- `content_hash` (for dedupe/versioning).

---

## 4) Indexing and Retrieval Design

### 4.1 Chunking Strategy
**Authoritative v1 parameters:** `ragChunkingEmbeddingVectorDb.md` §2 (heading-aware splits, ~512-character / ~256–384 token target chunks, 64–128 character overlap, table flattening).

At a high level:
- section-aware splitting (do not break key table rows),
- optional promotion of critical fields into atomic lines inside chunks (expense ratio, exit load, SIP minimum, riskometer, benchmark).

### 4.2 Embedding Strategy
- **Model:** `BAAI/bge-small-en-v1.5` for **both** indexed chunks and **live queries** (same preprocessing rules).
- **Store:** vectors + document text + metadata in **ChromaDB (local)**.
- **Normalization:** L2-normalize embeddings if using cosine similarity (see `ragChunkingEmbeddingVectorDb.md`).
- Keep a copy of chunk text and metadata for deterministic filtering, citation URLs, and re-embedding if the model changes.

### 4.3 Retrieval (phased)
**Phase 2 (minimum):** Chroma **vector similarity** only + **metadata filters** (`scheme_slug`, `source_url`). Sufficient for five pages and bootstrapping.

**Phase 5 (optional hardening):** **Hybrid** retrieval:
1. **Candidate generation**: vector similarity + lexical search (BM25/keyword) over the same chunk texts.
2. **Reranking**: cross-encoder or lightweight reranker on top-k.

Final top-k (e.g., 3–5) should prioritize:
- exact scheme match,
- recent/official source type priority,
- high factual density,
- numeric/structured answer confidence.

### 4.4 Metadata Filters
Apply filters before or during retrieval:
- **scheme** / `scheme_slug` matching the five Groww pages,
- `source_url` when the user names a specific fund,
- future: `source_type` when the corpus includes FAQs and regulator pages (e.g., statement download -> help/guidance URLs).

---

## 5) Query Understanding and Policy Routing

### 5.1 Query Classifier
Classify input as:
- `factual_supported`
- `advisory_refuse`
- `out_of_scope_refuse`
- `performance_related_limited` (return **in-scope scheme page** link only, e.g. the relevant Groww URL)

Classifier signals:
- advisory terms ("should I invest", "better fund", "recommend"),
- comparative language ("best", "top", "better than"),
- return forecasting or performance ranking requests.

### 5.2 Routing Logic
- `factual_supported` -> retrieval + generation path.
- `advisory_refuse` / `out_of_scope_refuse` -> refusal template + educational link (AMFI/SEBI).
- `performance_related_limited` -> short neutral response + **Groww scheme page** citation only (no return calculations or comparisons).

---

## 6) Answer Generation Architecture

### 6.1 Prompt Contract
System instructions enforce:
- answer only from supplied context,
- no assumptions if evidence is missing,
- max 3 sentences,
- no advice/recommendation/comparison,
- include only one source citation URL,
- append footer exactly:
  - `Last updated from sources: <date>`

### 6.2 Structured Output Schema
Generate in strict JSON internally:
- `answer_text`
- `citation_url`
- `last_updated_date`
- `response_type` (`factual` | `refusal` | `limited_performance`)

Then render user-facing text from schema. This prevents formatting drift.

### 6.3 Citation Selection Rule
From retrieved chunks, select exactly one citation using priority:
1. chunk directly containing answer fact,
2. most recent effective/ingested document,
3. highest relevance rerank score.

### 6.4 Post-Generation Validation
Validation checks:
- <= 3 sentences in `answer_text`,
- exactly one URL present,
- footer present and date parseable,
- no advisory phrases,
- content grounded in retrieved chunks.

If validation fails:
- run one constrained regeneration pass,
- else return safe fallback refusal with educational link.

---

## 7) Refusal and Safety Guardrails

### 7.1 Refusal Templates
Use fixed refusal styles:
- polite, concise,
- explain facts-only boundary,
- provide one educational official link.

Example template:
- "I can help only with factual mutual fund information from official sources, and cannot provide investment advice. You can refer to this AMFI investor education page: <link>. Last updated from sources: <date>"

### 7.2 Privacy Controls
Input scanner blocks or redacts sensitive fields (if accidentally entered):
- PAN, Aadhaar, account number patterns, OTP-like numeric strings,
- phone/email patterns.

Policy:
- do not store raw sensitive values in logs/history.

### 7.3 Allowed Content Boundary
Hard blocks:
- investment advice,
- fund recommendations,
- return predictions,
- comparative performance ranking.

For performance questions:
- neutral response + **scheme page** citation only (v1: Groww URL from corpus).

---

## 8) Conversation and Multi-Thread Support

### 8.1 Thread Model
Use identifiers:
- `user_id` (anonymous/session-level),
- `thread_id` (independent chat conversation),
- `message_id`.

Each thread stores:
- recent messages,
- retrieval traces (query, top chunks, selected citation),
- response type and validation result.

### 8.2 Context Handling per Thread
- Thread memory is isolated per `thread_id`.
- Retrieval query rewriting can use only that thread's history.
- No cross-thread context leakage.

### 8.3 Concurrency
- Stateless API layer + shared vector DB.
- Thread-safe persistence in relational DB (or key-value store).
- Async job queue for ingestion refresh (separate from chat serving path).

---

## 9) Minimal UI Architecture

UI components:
- welcome message,
- three example factual questions,
- input box,
- response card with:
  - short answer,
  - one source link,
  - last-updated footer,
- persistent disclaimer:
  - `Facts-only. No investment advice.`

Optional UX safeguards:
- pre-submit hint if prompt looks advisory,
- refusal response styled consistently.

---

## 10) API and Service Contracts

### 10.1 Chat API
`POST /v1/chat/respond`

Request:
- `thread_id`
- `query`
- optional `user_context` (non-PII only)

Response:
- `response_type`
- `answer_text`
- `citation_url`
- `last_updated_date`
- `disclaimer`

### 10.2 Source Management API
- `POST /v1/sources/register`
- `POST /v1/sources/reindex`
- `GET /v1/sources/status`

### 10.3 Observability API (internal)
- retrieval hit diagnostics,
- refusal rate,
- citation validity checks.

---

## 11) Monitoring, Evaluation, and QA

### 11.1 Core Metrics
- retrieval precision@k for factual queries,
- citation validity rate (URL reachable + source allowlist pass),
- policy compliance rate (no-advice violations),
- response format compliance (`<=3 sentences`, one citation, footer present),
- refusal correctness (advisory queries refused appropriately).

### 11.2 Test Set Design
Use **`docs/edgeCases.md`** as the master catalog (IDs E1.x–E15.x). Additionally cover:
- factual prompts by scheme and category,
- advisory prompts (should refuse),
- performance prompts (limited response path),
- ambiguous prompts requiring clarification/refusal.

### 11.3 Regression Suite
Automate tests for:
- formatting invariants,
- source allowlist enforcement,
- thread isolation behavior,
- stale citation detection.

---

## 12) Deployment Blueprint

Recommended components:
- **Scheduler:** **GitHub Actions** daily at **09:15 UTC** (see §2.3); runs the Phase 1 **scraping service** + indexer.
- `ingestion-worker` (same logical role as the **`mfr_phase1`** pipeline: **HTML fetch + parse** for allowlisted Groww URLs),
- `indexer-worker` (**chunk** with `bge-small-en-v1.5` → **upsert to local ChromaDB**),
- `chat-api` (Chroma query + generation + validation),
- `ui` (minimal web app),
- **ChromaDB (local on-disk)** + optional `metadata-db` (Postgres/SQLite) for threads and ingest audit.

Deployment practices:
- **daily scheduled re-ingestion at 09:15 UTC** via GitHub Actions (adjust cron for IST if needed—§2.3),
- blue-green deploy for chat-api,
- secure secret management for model/provider keys,
- audit logs for policy events (without sensitive user data).

---

## 13) Failure Modes and Fallbacks

Potential failure and handling:
- **No relevant context found** -> safe "information not found in official corpus" response + one official help link.
- **Citation URL broken** -> fallback to next best retrieved source or refusal.
- **Model output policy violation** -> block + regenerate under stricter template.
- **Source parsing error** -> mark source unhealthy; alert and keep previous valid indexed version.

---

## 14) Suggested Tech Stack (Lightweight)

- Backend: Python FastAPI (recommended for Sentence Transformers + Chroma)
- **Vector DB: ChromaDB (local persistent client or local server)**
- **Embeddings: `BAAI/bge-small-en-v1.5`** via Sentence Transformers (or compatible runtime)
- **Ingestion:** `httpx` / `requests` + **HTML** parsing (`BeautifulSoup`, `trafilatura`, or `readability`-style extraction)
- Reranker: optional cross-encoder for factual accuracy boosts
- PDF: **not in v1**; add `pypdf` / `pdfplumber` when PDFs are in scope
- Frontend: simple React/Vue static interface
- Storage: Postgres or SQLite (threads, ingest logs); Chroma holds vectors + chunk text

---

## 15) Traceable Requirement Mapping

- **Facts-only answers** -> classifier + policy routing + guardrails.
- **Source policy** -> **v1:** ingest allowlist = five **Groww** scheme URLs; citations from RAG = those URLs; **refusal/education** = **AMFI/SEBI** links per problem statement. **Future:** expand toward AMC/AMFI/SEBI document URLs (15–25) per `problemStatement.md`.
- **<= 3 sentences** -> output schema validator.
- **Exactly 1 citation** -> citation selector + formatter constraint.
- **Last-updated footer** -> metadata-driven footer renderer.
- **Refusal for advisory queries** -> refusal router and templates.
- **Minimal UI with disclaimer** -> fixed UI elements and response card.
- **Multiple chat threads** -> `thread_id`-scoped memory and storage.
- **Scraping → chunking → embedding → Chroma** -> see §2.2 and `ragChunkingEmbeddingVectorDb.md`.

---

## 16) Implementation Phases (finalized)

Phases are **sequential**: complete exit criteria before moving on. Chunking/embedding/Chroma details stay in **`ragChunkingEmbeddingVectorDb.md`**; evaluation cases in **`edgeCases.md`**.

### Phase 0 — Repository and environment

**Goal:** Runnable project skeleton, secrets pattern, no production data yet.

- Python project layout, dependency pins (`sentence-transformers`, `chromadb`, FastAPI or chosen stack).
- Config: allowlisted Groww URLs, Chroma persist path, model id `BAAI/bge-small-en-v1.5`.
- Document **known limitation**: v1 corpus is Groww HTML only (vs. problem statement’s broader “official” URL set).

**Exit criteria:** `README` stub with setup; app starts; no indexer required.

---

### Phase 1 — Source registry, scraping, chunking, embedding, Chroma

**Goal:** Deterministic **index** from the five Groww scheme pages.

- **Code layout:** `phase1/mfr_phase1/` — install from repo root with `pip install -e .`; run **`python -m mfr_phase1`** (scraping service + indexer). See `phase1/README.md`.
- Implement **source registry** (§3.1) with exactly the five URLs; enforce path allowlist on `groww.in`.
- **Fetch + parse** HTML (§3.3); handle failures per `edgeCases.md` E6.x.
- **Chunk** per `ragChunkingEmbeddingVectorDb.md` §2; attach metadata (`scheme_slug`, `source_url`, `ingested_at`, …).
- **Embed** with `bge-small-en-v1.5`; **upsert** to local Chroma collection (e.g. `mutual_fund_faq_groww_v1`).
- **Per-URL replace:** delete Chroma rows for that `source_url`, then add fresh chunks (no orphans).
- **Scheduler:** **GitHub Actions** **daily 09:15 UTC** — `.github/workflows/ingest-scheduled.yml` (§2.3). Manual: `workflow_dispatch` or local CLI.

**Exit criteria:** Non-empty Chroma collection; spot-check chunks for all five URLs; `ingested_at` available for footer; scheduled workflow green (or documented allowlist/network constraints).

---

### Phase 2 — Retrieval, LLM answer, response validator

**Goal:** End-to-end **chat** from indexed corpus with correct **format**.

- **Code layout:** `phase2/mfr_phase2/` — run **`python -m mfr_phase2 "…"`** after `pip install -e .`. See `phase2/README.md`.
- **LLM provider (v1):** **Groq** OpenAI-compatible Chat Completions. Configure **`GROQ_API_KEY`** (and optional **`GROQ_MODEL`**) in **`.env`** — copy from **`.env.example`**. **Phase 1 indexing does not use this key**; it is required only when Phase 2 needs to **generate a factual answer** from retrieved context (advisory / template paths skip Groq).
- **Retrieval:** Chroma vector query + **metadata filters** when scheme is known (§4.3 Phase 2 minimum).
- **Context pack:** top-k → trim to 3–5 chunks for LLM.
- **Prompt contract** (§6.1) + structured JSON output (§6.2).
- **Validator:** ≤3 sentences in `answer_text`, citation URL ∈ retrieved `source_url` set, formatted user message has **exactly one** citation line + footer `Last updated from sources: <date>` (§6.4, `edgeCases.md` E2.x). One **Groq retry** with stricter system prompt if validation fails.
- **Lightweight routing (preview of Phase 3):** obvious **advisory** / **performance** queries use fixed templates + AMFI or Groww links without LLM.

**Exit criteria:** Manual smoke tests on expense ratio / exit load / benchmark per scheme; format checks pass; missing `GROQ_API_KEY` fails fast with a clear message on factual path only.

---

### Phase 3 — Query routing, refusals, performance-limited path, PII

**Goal:** **Policy-safe** behavior per `problemStatement.md`.

- **Code layout:** `phase3/mfr_phase3/` — run **`python -m mfr_phase3 "…"`** (wraps Phase 2 with guardrails). See `phase3/README.md`.
- **Classifier / router** (§5): `factual_supported`, `advisory_refuse`, `out_of_scope_refuse`, `performance_related_limited` — implemented in **`mfr_phase3.classifier`** (injection/off-topic, expanded advisory/performance; advisory precedence on multi-intent).
- **Refusal templates** with **one AMFI/SEBI** educational link + footer (§7.1) — **`mfr_phase3.education`** + `REFUSAL_EDUCATION_MODE` / `SEBI_INVESTOR_URL` in **`.env.example`**.
- **Performance queries:** unchanged Phase 2 behavior — no calculations; **one Groww scheme citation** (§5.2, §7.3).
- **PII:** detect/redact before retrieval/LLM; no logging of raw values (§7.2, E10.x) — **`mfr_phase3.pii`**.
- **Phase 2 integration:** `mfr_phase2.respond.answer_query(..., route_override=..., refusal_education_url=...)` so Phase 3 owns routing and education URL selection.

**Exit criteria:** `edgeCases.md` sections E3, E10, E13 spot-pass; refusal always includes education link.

---

### Phase 4 — API, multi-thread chat, minimal UI

**Goal:** Deliverables alignment: **threads + UI**.

- **Code layout:** `phase4/mfr_phase4/` — run **`python -m mfr_phase4`** (Uvicorn). See `phase4/README.md`.
- **API:** `POST /v1/chat/respond` (§10.1) with `thread_id`, `query`, optional `scheme_slug`, `user_context`. **`thread_id` omitted or unknown → server creates a new thread** and returns it (`edgeCases.md` E11.1). `GET /health`, `POST /v1/chat/threads` optional.
- **Thread store:** SQLite (`THREAD_DB_PATH`) — threads + message log; **scheme hint** persisted from Groww `citation_url` after factual replies for follow-ups (§8.2).
- **UI:** `GET /` serves minimal SPA: welcome, **three** example questions, disclaimer **“Facts-only. No investment advice.”** (§9, problem statement §4).
- **Engine:** responses produced via **`mfr_phase3`** (guardrails + RAG).

**Exit criteria:** Two parallel threads (e.g. two browsers / cleared session) with different schemes behave correctly (E11.x, E5.5).

---

### Phase 5 — Evaluation, monitoring, optional hybrid retrieval

**Goal:** Measurable quality and production hygiene.

- **Code layout:** `phase5/mfr_phase5/` — CLI **`python -m mfr_phase5`**. See `phase5/README.md`.
- **Eval:** `eval` subcommand runs **`cases.json`** (IDs aligned with **`docs/edgeCases.md`**): format checks (footer, single URL, ≤3 sentences), route/type expectations, Groww vs AMFI/SEBI citation rules. Cases that need Groq are **skipped** unless `GROQ_API_KEY` is set or **`--include-groq`** is passed. **`--json-out`** for CI artifacts.
- **Corpus / staleness:** `corpus-stats` reports Chroma **count** and **ingested_at** min/max sample (§13); pair with scheduled re-ingest (§2.3).
- **Optional hybrid:** `hybrid-demo` implements **BM25 + Chroma vector** lists fused with **RRF** (§4.3 Phase 5); requires **`pip install -e ".[phase5]"`** (`rank-bm25`). Not wired into production `retrieve` by default.
- **Metrics (§11.1):** eval summary reports **passed / failed / skipped**; extend `cases.json` for precision@k when gold chunk ids exist.

**Exit criteria:** `eval` green on policy + format suites (with `--include-groq` when LLM cases are in scope); limitations and AMC/schemes documented in README.

---

This architecture keeps the assistant lightweight while making policy compliance and factual reliability first-class system behaviors.
