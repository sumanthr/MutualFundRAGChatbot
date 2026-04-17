from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from mfr_phase2.respond import AnswerResult, answer_query as phase2_answer
from mfr_phase2.scheme_infer import infer_scheme_slug
from mfr_phase2.routing import RouteType
from mfr_phase3.classifier import classify_query as classify_phase3
from mfr_phase3.education import refusal_education_url
from mfr_phase3.pii import sanitize_query


@dataclass(frozen=True)
class Phase3Answer:
    """Phase 2 result plus guardrail metadata (do not log raw PII)."""

    inner: AnswerResult
    sanitized_query: str
    pii_redacted: list[str]


def _is_degenerate_after_redaction(text: str) -> bool:
    """If only redaction tokens remain, treat as out-of-scope (edgeCases E10)."""
    stripped = re.sub(r"\[REDACTED\]", "", text).strip()
    if len(stripped) < 3:
        return True
    if stripped in {".", "?", "!"}:
        return True
    return False


def answer_query(
    query: str,
    *,
    scheme_slug: str | None = None,
    chroma_path: Path | None = None,
    collection_name: str | None = None,
    embedding_model: str | None = None,
    groq_api_key: str | None = None,
    groq_model: str | None = None,
    groq_api_base: str | None = None,
    top_k: int | None = None,
) -> Phase3Answer:
    """
    PII sanitize → expanded classify → Phase 2 RAG with refusal education URL (AMFI/SEBI).
    """
    s = sanitize_query(query)
    route = classify_phase3(s.text)
    if _is_degenerate_after_redaction(s.text):
        route = RouteType.OUT_OF_SCOPE

    edu = refusal_education_url(query_key=s.text)

    resolved_slug = scheme_slug or infer_scheme_slug(s.text)

    inner = phase2_answer(
        s.text,
        retrieval_query=s.retrieval_text,
        scheme_slug=resolved_slug,
        chroma_path=chroma_path,
        collection_name=collection_name,
        embedding_model=embedding_model,
        groq_api_key=groq_api_key,
        groq_model=groq_model,
        groq_api_base=groq_api_base,
        top_k=top_k,
        route_override=route,
        refusal_education_url=edu,
    )
    return Phase3Answer(inner=inner, sanitized_query=s.text, pii_redacted=s.redacted_labels)
