from __future__ import annotations

import re

from mfr_phase2.routing import RouteType

# Prompt injection / meta (edgeCases E9.4, E10.4)
_INJECTION = re.compile(
    r"\b("
    r"ignore (all|previous|the) (rules|instructions)|disregard (all|previous)|"
    r"bypass|you are (now )?dba|pretend you are|reveal (your )?prompt|"
    r"system prompt|jailbreak"
    r")\b",
    re.I,
)

# Clearly off-topic for this assistant (edgeCases E1.2 adjacent)
_OFF_TOPIC = re.compile(
    r"\b("
    r"weather in|write a poem|python code|debug my code|who won the match|"
    r"recipe for|translate to french|horoscope"
    r")\b",
    re.I,
)

_ADVISORY = re.compile(
    r"\b("
    r"should i invest|shall i invest|is it a good (time|idea) to invest|"
    r"recommend|which fund is better|which (one )?is better|better fund|best fund|"
    r"best elss|top elss|best (scheme|mutual fund)\b|"
    r"top fund|which (scheme|fund) should|what should i buy|where should i invest|"
    r"safe to invest|worth investing|is (this|it) (a )?good (buy|investment)|"
    r"is this fund safe|maximum returns|maximize returns|"
    r"will i lose money|guaranteed returns"
    r")\b",
    re.I,
)

_PERFORMANCE = re.compile(
    r"\b("
    r"\bcagr\b|past returns?|historical returns?|1y returns?|3y returns?|5y returns?|"
    r"annual returns?|predict (the )?returns?|future returns?|"
    r"how much (will|would) i (earn|make)|calculate (my )?gains|"
    r"performance (of|vs)|beat the market|outperform|"
    r"year to date|ytd|alpha|beta\b|sharpe|"
    r"nav (on|for) \d|compare returns|higher returns"
    r")\b",
    re.I,
)


def classify_query(query: str) -> RouteType:
    """
    Expanded router (architecture §5.1): advisory > performance > factual.
    Multi-intent: advisory patterns take precedence (edgeCases E4.7).
    """
    q = query.strip()
    if not q:
        return RouteType.OUT_OF_SCOPE
    if _INJECTION.search(q):
        return RouteType.OUT_OF_SCOPE
    if _OFF_TOPIC.search(q):
        return RouteType.OUT_OF_SCOPE
    if _ADVISORY.search(q):
        return RouteType.ADVISORY
    if _PERFORMANCE.search(q):
        return RouteType.PERFORMANCE_LIMITED
    return RouteType.FACTUAL
