# Phase 4 — HTTP API, multi-thread chat, minimal UI

**Goal:** `docs/ragArchitecture.md` §8–§10, §16 Phase 4: **`POST /v1/chat/respond`**, thread isolation, welcome + **three example questions** + disclaimer.

## Run the server

From repo root (after `pip install -e .` and Phase 1 index + `.env` with `GROQ_API_KEY`):

```bash
python -m mfr_phase4
```

Defaults: **`http://127.0.0.1:8000`** — open **`/`** for the UI.

Env (see **`.env.example`**): `API_HOST`, `API_PORT`, `THREAD_DB_PATH` (SQLite, default `./data/threads.sqlite3`).

## API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness |
| `POST` | `/v1/chat/threads` | Create empty thread (optional; see below) |
| `POST` | `/v1/chat/respond` | Main chat (body below) |
| `GET` | `/` | Minimal SPA (static) |

### `POST /v1/chat/respond`

**Request JSON**

- `thread_id` (optional): continue a conversation. **Omitted or unknown id → server creates a new thread** and returns `thread_id` (edgeCases E11.1).
- `query` (required)
- `scheme_slug` (optional): Chroma filter; also persisted on thread after a factual Groww citation when inferable.
- `user_context` (optional): accepted for API compatibility; **not** merged into retrieval in v1 (non-PII only per architecture).

**Response JSON**

- `thread_id`, `response_type`, `route`, `answer_text`, `citation_url`, `last_updated_date`, `disclaimer`
- `formatted_message` (full text with Source line, for debugging/UI)
- `pii_redacted`, `retrieval_count`

Backend uses **`mfr_phase3.answer_query`** (PII + routing + Phase 2 RAG).

## UI

- Welcome copy, **three** example question buttons (problem statement §4).
- Persistent disclaimer: **“Facts-only. No investment advice.”**
- `sessionStorage` holds `thread_id`; **New conversation** clears it.

## Thread store

- SQLite: `threads` + `messages` (no raw PII in logs from API; user text stored as submitted — operators should secure `THREAD_DB_PATH`).

## Next

**Phase 5** — eval harness, metrics (`../phase5/README.md`).
