from __future__ import annotations

import re
from enum import Enum


class RouteType(str, Enum):
    FACTUAL = "factual_supported"
    ADVISORY = "advisory_refuse"
    OUT_OF_SCOPE = "out_of_scope_refuse"
    PERFORMANCE_LIMITED = "performance_related_limited"


_ADVISORY = re.compile(
    r"\b("
    r"should i invest|shall i invest|is it a good (time|idea) to invest|"
    r"recommend|which fund is better|which (one )?is better|better fund|best fund|"
    r"top fund|which (scheme|fund) should|what should i buy|where should i invest|"
    r"safe to invest|worth investing"
    r")\b",
    re.I,
)

_PERFORMANCE = re.compile(
    r"\b("
    r"\bcagr\b|past returns?|historical returns?|1y returns?|3y returns?|5y returns?|"
    r"annual returns?|predict (the )?returns?|future returns?|"
    r"how much (will|would) i (earn|make)|calculate (my )?gains|"
    r"performance (of|vs)|beat the market|outperform"
    r")\b",
    re.I,
)


def classify_query(query: str) -> RouteType:
    """Lightweight router (full classifier tuning is Phase 3)."""
    q = query.strip()
    if not q:
        return RouteType.OUT_OF_SCOPE
    if _ADVISORY.search(q):
        return RouteType.ADVISORY
    if _PERFORMANCE.search(q):
        return RouteType.PERFORMANCE_LIMITED
    return RouteType.FACTUAL
