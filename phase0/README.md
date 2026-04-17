# Phase 0 — Repository and environment

**Goal:** Runnable project skeleton, dependency pins, configuration pattern.

## Done in repo root

- `pyproject.toml` — package install with Phase 1 dependencies (`httpx`, `beautifulsoup4`, `lxml`, `chromadb`, `sentence-transformers`).
- `README.md` — setup and Phase 1 CLI.
- `.gitignore` — venv, `chroma_data/`, caches.

## Exit criteria

- [x] Create venv, `pip install -e .` succeeds.
- [x] `python -m mfr_phase1 --help` runs (after Phase 1 code is present).

## Next

Implement and run **Phase 1** (`../phase1/README.md`).
