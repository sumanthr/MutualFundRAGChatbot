from __future__ import annotations

import re
from typing import Any


def count_sentences(text: str) -> int:
    t = text.strip()
    if not t:
        return 0
    parts = re.split(r"(?<=[.!?])\s+", t)
    return len([p for p in parts if p.strip()])


def count_http_urls(text: str) -> int:
    return len(re.findall(r"https?://[^\s)]+", text))


def extract_footer_date(formatted_message: str) -> str | None:
    m = re.search(
        r"Last updated from sources:\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9TZ:\-+]+)",
        formatted_message,
        re.I,
    )
    return m.group(1).strip() if m else None


def validate_llm_json(
    obj: dict[str, Any],
    *,
    allowed_citation_urls: set[str],
    max_sentences: int = 3,
) -> list[str]:
    errors: list[str] = []
    for key in ("answer_text", "citation_url", "last_updated_date", "response_type"):
        if key not in obj:
            errors.append(f"missing:{key}")
    if errors:
        return errors

    at = obj.get("answer_text")
    if not isinstance(at, str):
        errors.append("answer_text_not_str")
    elif count_sentences(at) > max_sentences:
        errors.append(f"too_many_sentences:{count_sentences(at)}")
    elif count_http_urls(at) > 0:
        errors.append("answer_text_contains_url")

    cu = obj.get("citation_url")
    if not isinstance(cu, str) or not cu.startswith("http"):
        errors.append("citation_url_invalid")
    elif cu not in allowed_citation_urls:
        errors.append("citation_url_not_in_context")

    lud = obj.get("last_updated_date")
    if not isinstance(lud, str) or not lud.strip():
        errors.append("last_updated_date_invalid")

    rt = obj.get("response_type")
    if rt != "factual":
        errors.append("response_type_not_factual")

    return errors


_ADVISORY_LEAK = re.compile(
    r"\b(you should invest|i recommend|buy this|sell this|better than|best fund)\b",
    re.I,
)


def validate_no_advice_leak(answer_text: str) -> bool:
    return _ADVISORY_LEAK.search(answer_text) is None


def format_user_message(
    answer_text: str,
    citation_url: str,
    last_updated_date: str,
) -> str:
    """Single user-visible blob: answer + one link + footer (architecture §6.1)."""
    return (
        f"{answer_text.strip()}\n\n"
        f"Source: {citation_url}\n\n"
        f"Last updated from sources: {last_updated_date.strip()}"
    )
