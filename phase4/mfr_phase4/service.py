from __future__ import annotations

import re
from urllib.parse import urlparse

from mfr_phase2.scheme_infer import infer_scheme_slug
from mfr_phase3.respond import Phase3Answer, answer_query as phase3_answer

from mfr_phase4 import DISCLAIMER
from mfr_phase4.schemas import ChatRespondResponse
from mfr_phase4.thread_store import ThreadStore


def _groww_slug_from_url(url: str) -> str | None:
    p = urlparse(url)
    if (p.hostname or "").lower() != "groww.in":
        return None
    parts = [x for x in p.path.strip("/").split("/") if x]
    if len(parts) >= 2 and parts[0] == "mutual-funds":
        return parts[1]
    return None


def _split_answer_body(formatted_message: str, _citation_url: str) -> str:
    """Main answer lines without Source / footer (for API answer_text field)."""
    t = formatted_message.strip()
    if "\n\nSource: " in t:
        t = t.split("\n\nSource: ", 1)[0].strip()
    elif "\n\nLast updated from sources:" in t:
        t = t.split("\n\nLast updated from sources:", 1)[0].strip()
    t = re.sub(r"\n+Source:\s*.*$", "", t, flags=re.I | re.M).strip()
    return t


def respond_chat(
    *,
    store: ThreadStore,
    thread_id: str | None,
    query: str,
    scheme_slug: str | None,
) -> ChatRespondResponse:
    tid = store.ensure_thread(thread_id)
    thread_slug = store.get_scheme_slug(tid)
    effective_slug = scheme_slug or thread_slug or infer_scheme_slug(query)

    out: Phase3Answer = phase3_answer(query, scheme_slug=effective_slug)

    inner = out.inner
    if inner.response_type == "factual" and inner.citation_url:
        slug = _groww_slug_from_url(inner.citation_url)
        if slug:
            store.set_scheme_slug(tid, slug)

    store.append_message(tid, role="user", content=query, meta={"sanitized": out.sanitized_query})
    store.append_message(
        tid,
        role="assistant",
        content=inner.formatted_message,
        meta={
            "response_type": inner.response_type,
            "route": inner.route,
            "citation_url": inner.citation_url,
            "pii_redacted": out.pii_redacted,
        },
    )

    answer_text = _split_answer_body(inner.formatted_message, inner.citation_url)

    return ChatRespondResponse(
        thread_id=tid,
        response_type=inner.response_type,
        route=inner.route,
        answer_text=answer_text,
        citation_url=inner.citation_url,
        last_updated_date=inner.last_updated_date,
        disclaimer=DISCLAIMER,
        formatted_message=inner.formatted_message,
        pii_redacted=out.pii_redacted,
        retrieval_count=len(inner.retrieval),
    )
