from __future__ import annotations

import re

from mfr_phase1.registry import SOURCES

_SKIP_SLUG_TOKENS = frozenset({"fund", "direct", "growth", "plan", "hdfc"})


def infer_scheme_slug(query: str) -> str | None:
    """Best-effort scheme from natural language (HDFC bootcamp corpus)."""
    if not query or not query.strip():
        return None
    ql = query.lower().strip()
    ql_tokens = set(re.findall(r"[a-z0-9]+", ql))

    hints: list[tuple[str, tuple[str, ...]]] = [
        ("hdfc-elss-tax-saver-fund-direct-plan-growth", ("elss", "tax saver")),
        ("hdfc-mid-cap-fund-direct-growth", ("mid cap", "midcap")),
        ("hdfc-large-cap-fund-direct-growth", ("large cap",)),
        ("hdfc-focused-fund-direct-growth", ("focused",)),
        (
            "hdfc-equity-fund-direct-growth",
            ("hdfc equity fund", "equity fund direct growth", "hdfc equity"),
        ),
    ]
    for slug, kws in hints:
        if any(k in ql for k in kws):
            return slug

    best_slug: str | None = None
    best = 0
    for s in SOURCES:
        slug = s.scheme_slug
        slug_words = slug.replace("-", " ").split()
        score = 0
        for w in slug_words:
            if len(w) <= 2 or w in _SKIP_SLUG_TOKENS:
                continue
            if w in ql_tokens:
                score += 1
        name_tokens = [
            t
            for t in s.scheme_name.lower().replace("(", " ").replace(")", " ").split()
            if len(t) > 3 and t not in ("fund", "plan", "growth", "direct", "hdfc")
        ]
        for t in name_tokens:
            if t in ql_tokens:
                score += 2
        if score > best:
            best = score
            best_slug = slug
    if best >= 3:
        return best_slug
    return None
