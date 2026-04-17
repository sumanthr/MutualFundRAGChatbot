from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatRespondRequest(BaseModel):
    thread_id: Optional[str] = Field(
        default=None,
        description="Conversation id; omit or invalid id creates a new thread.",
    )
    query: str = Field(..., min_length=1)
    scheme_slug: Optional[str] = Field(
        default=None,
        description="Optional filter / thread hint, e.g. hdfc-mid-cap-fund-direct-growth",
    )
    user_context: Optional[str] = Field(
        default=None,
        description="Non-PII context only (optional; currently not appended to retrieval).",
    )


class ChatRespondResponse(BaseModel):
    thread_id: str
    response_type: str
    route: str
    answer_text: str
    citation_url: str
    last_updated_date: str
    disclaimer: str
    formatted_message: str
    pii_redacted: list[str] = Field(default_factory=list)
    retrieval_count: int = 0


class ThreadCreateResponse(BaseModel):
    thread_id: str


class ThreadSummary(BaseModel):
    thread_id: str
    updated_at: str
    preview: Optional[str] = None


class ThreadListResponse(BaseModel):
    threads: list[ThreadSummary] = Field(default_factory=list)


class ChatMessageItem(BaseModel):
    role: str
    content: str
    created_at: str


class ThreadMessagesResponse(BaseModel):
    thread_id: str
    messages: list[ChatMessageItem] = Field(default_factory=list)


class ThreadsPurgeResponse(BaseModel):
    removed_threads: int
    kept_thread_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
