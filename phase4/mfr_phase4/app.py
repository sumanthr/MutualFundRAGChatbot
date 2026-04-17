from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from mfr_phase4.schemas import (
    ChatMessageItem,
    ChatRespondRequest,
    ChatRespondResponse,
    HealthResponse,
    ThreadCreateResponse,
    ThreadListResponse,
    ThreadMessagesResponse,
    ThreadSummary,
    ThreadsPurgeResponse,
)
from mfr_phase4.service import respond_chat
from mfr_phase4.settings import THREAD_DB_PATH
from mfr_phase4.thread_store import ThreadStore

_static = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Mutual Fund FAQ RAG",
    description="Facts-only assistant — Phase 4 API + UI",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoStoreApiMiddleware(BaseHTTPMiddleware):
    """Avoid stale thread lists / messages from browser or intermediary caches."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/v1/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
        return response


app.add_middleware(NoStoreApiMiddleware)

_store = ThreadStore(THREAD_DB_PATH)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/v1/chat/threads", response_model=ThreadCreateResponse)
def create_thread() -> ThreadCreateResponse:
    return ThreadCreateResponse(thread_id=_store.create_thread())


@app.get("/v1/chat/threads", response_model=ThreadListResponse)
def list_threads() -> ThreadListResponse:
    rows = _store.list_threads(limit=50)
    threads = [
        ThreadSummary(
            thread_id=t.thread_id,
            updated_at=t.updated_at,
            preview=_store.get_thread_preview(t.thread_id),
        )
        for t in rows
    ]
    return ThreadListResponse(threads=threads)


@app.delete("/v1/chat/threads", response_model=ThreadsPurgeResponse)
def purge_threads(
    keep: Optional[str] = Query(
        default=None,
        description="If set, this thread is kept and all others are removed.",
    ),
) -> ThreadsPurgeResponse:
    keep = (keep or "").strip() or None
    if keep and _store.get_thread(keep) is None:
        raise HTTPException(status_code=404, detail="Unknown keep thread id")
    n = _store.delete_threads_except(keep)
    return ThreadsPurgeResponse(removed_threads=n, kept_thread_id=keep)


@app.get("/v1/chat/threads/{thread_id}/messages", response_model=ThreadMessagesResponse)
def thread_messages(thread_id: str) -> ThreadMessagesResponse:
    if _store.get_thread(thread_id) is None:
        raise HTTPException(status_code=404, detail="Unknown thread")
    raw = _store.recent_messages(thread_id, limit=100)
    messages = [
        ChatMessageItem(role=str(m["role"]), content=str(m["content"]), created_at=str(m["created_at"]))
        for m in raw
    ]
    return ThreadMessagesResponse(thread_id=thread_id, messages=messages)


@app.post("/v1/chat/respond", response_model=ChatRespondResponse)
def chat_respond(body: ChatRespondRequest) -> ChatRespondResponse:
    try:
        raw_tid = body.thread_id.strip() if body.thread_id else None
        return respond_chat(
            store=_store,
            thread_id=raw_tid or None,
            query=body.query.strip(),
            scheme_slug=body.scheme_slug.strip() if body.scheme_slug else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/")
def index() -> FileResponse:
    index_path = _static / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="UI not found")
    return FileResponse(index_path)


app.mount("/static", StaticFiles(directory=str(_static)), name="static")
