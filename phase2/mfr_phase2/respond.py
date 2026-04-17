from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mfr_phase2.groq_client import groq_chat_completion, parse_json_object
from mfr_phase2.prompts import SYSTEM_FACTUAL, SYSTEM_RETRY, build_user_message
from mfr_phase2.routing import RouteType, classify_query
from mfr_phase2 import settings
from mfr_phase2.validator import (
    format_user_message,
    validate_llm_json,
    validate_no_advice_leak,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mfr_phase2.retrieve import RetrievedChunk


@dataclass(frozen=True)
class AnswerResult:
    route: str
    formatted_message: str
    citation_url: str
    last_updated_date: str
    response_type: str
    raw_llm: dict[str, Any] | None
    retrieval: list["RetrievedChunk"]


def _refusal_message(*, education_url: str) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    body = (
        "I can help only with factual mutual fund information from official and indexed sources, "
        "and cannot provide investment advice or fund recommendations."
    )
    return format_user_message(body, education_url, today)


def _performance_limited_message(*, citation_url: str, ingested_at: str | None) -> str:
    date = (ingested_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()).split("T")[0]
    body = (
        "I cannot discuss, calculate, or compare investment returns or performance. "
        "You can review the scheme details on the official scheme page linked below."
    )
    return format_user_message(body, citation_url, date)


def answer_query(
    query: str,
    *,
    retrieval_query: str | None = None,
    scheme_slug: str | None = None,
    chroma_path: Path | None = None,
    collection_name: str | None = None,
    embedding_model: str | None = None,
    groq_api_key: str | None = None,
    groq_model: str | None = None,
    groq_api_base: str | None = None,
    top_k: int | None = None,
    route_override: RouteType | None = None,
    refusal_education_url: str | None = None,
) -> AnswerResult:
    chroma_path = chroma_path or settings.CHROMA_PATH
    collection_name = collection_name or settings.CHROMA_COLLECTION
    embedding_model = embedding_model or settings.EMBEDDING_MODEL
    groq_api_key = groq_api_key or settings.GROQ_API_KEY
    groq_model = groq_model or settings.GROQ_MODEL
    groq_api_base = groq_api_base or settings.GROQ_API_BASE
    top_k = top_k if top_k is not None else settings.RETRIEVAL_TOP_K
    edu = refusal_education_url or settings.AMFI_INVESTOR_EDUCATION_URL

    route = route_override if route_override is not None else classify_query(query)

    if route in (RouteType.ADVISORY, RouteType.OUT_OF_SCOPE):
        msg = _refusal_message(education_url=edu)
        return AnswerResult(
            route=route.value,
            formatted_message=msg,
            citation_url=edu,
            last_updated_date=datetime.now(timezone.utc).date().isoformat(),
            response_type="refusal",
            raw_llm=None,
            retrieval=[],
        )

    from mfr_phase2.retrieve import allowed_citation_urls, max_ingested_at, retrieve

    q_for_retrieve = (retrieval_query or query).strip() or query
    chunks = retrieve(
        q_for_retrieve,
        chroma_path=chroma_path,
        collection_name=collection_name,
        embedding_model=embedding_model,
        top_k=top_k,
        scheme_slug=scheme_slug,
    )
    allow = allowed_citation_urls(chunks)
    batch_ts = max_ingested_at(chunks)

    if route == RouteType.PERFORMANCE_LIMITED:
        cit = ""
        if chunks:
            u = chunks[0].metadata.get("source_url")
            cit = u if isinstance(u, str) else ""
        if not cit and allow:
            cit = sorted(allow)[0]
        if not cit:
            msg = _refusal_message(education_url=edu)
            return AnswerResult(
                route=route.value,
                formatted_message=msg,
                citation_url=edu,
                last_updated_date=datetime.now(timezone.utc).date().isoformat(),
                response_type="refusal",
                raw_llm=None,
                retrieval=chunks,
            )
        msg = _performance_limited_message(citation_url=cit, ingested_at=batch_ts)
        return AnswerResult(
            route=route.value,
            formatted_message=msg,
            citation_url=cit,
            last_updated_date=batch_ts.split("T")[0] if batch_ts else datetime.now(timezone.utc).date().isoformat(),
            response_type="limited_performance",
            raw_llm=None,
            retrieval=chunks,
        )

    if not groq_api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Add it to .env (see .env.example). "
            "Phase 1 indexing does not need it; Phase 2 answer generation does."
        )

    if not chunks:
        msg = _refusal_message(education_url=edu)
        return AnswerResult(
            route=route.value,
            formatted_message=msg,
            citation_url=edu,
            last_updated_date=datetime.now(timezone.utc).date().isoformat(),
            response_type="refusal",
            raw_llm=None,
            retrieval=chunks,
        )

    context_blocks = [c.document for c in chunks if c.document.strip()]
    allowed_list = sorted(allow)
    user_msg = build_user_message(
        question=query,
        context_blocks=context_blocks[:10],
        allowed_urls=allowed_list,
        last_updated_batch=batch_ts,
    )

    messages = [
        {"role": "system", "content": SYSTEM_FACTUAL},
        {"role": "user", "content": user_msg},
    ]

    raw: dict[str, Any] | None = None
    for attempt in range(2):
        sys = SYSTEM_RETRY if attempt else SYSTEM_FACTUAL
        messages[0]["content"] = sys
        content = groq_chat_completion(
            api_base=groq_api_base,
            api_key=groq_api_key,
            model=groq_model,
            messages=messages,
            temperature=0.2,
        )
        try:
            raw = parse_json_object(content)
        except Exception as e:
            logger.warning("Groq JSON parse failed: %s", e)
            raw = None
        if raw:
            errs = validate_llm_json(raw, allowed_citation_urls=allow)
            if not errs and validate_no_advice_leak(str(raw.get("answer_text", ""))):
                break
            logger.warning("Validation errors (attempt %s): %s", attempt + 1, errs)
        raw = None

    if not raw:
        msg = _refusal_message(education_url=edu)
        return AnswerResult(
            route=route.value,
            formatted_message=msg,
            citation_url=edu,
            last_updated_date=datetime.now(timezone.utc).date().isoformat(),
            response_type="refusal",
            raw_llm=None,
            retrieval=chunks,
        )

    at = str(raw["answer_text"])
    cu = str(raw["citation_url"])
    lud = str(raw["last_updated_date"])
    if batch_ts:
        lud = batch_ts.split("T")[0] if "T" in batch_ts else batch_ts[:10]

    formatted = format_user_message(at, cu, lud)
    return AnswerResult(
        route=route.value,
        formatted_message=formatted,
        citation_url=cu,
        last_updated_date=lud,
        response_type="factual",
        raw_llm=raw,
        retrieval=chunks,
    )
