from __future__ import annotations

from mfr_phase2 import settings as p2

from mfr_phase3 import settings as p3


def refusal_education_url(*, query_key: str = "") -> str:
    """
    One official education link for refusal / empty-corpus paths (problem statement §3).
    REFUSAL_EDUCATION_MODE: amfi | sebi | alternate (stable hash of query_key).
    """
    mode = p3.REFUSAL_EDUCATION_MODE
    amfi = p2.AMFI_INVESTOR_EDUCATION_URL
    sebi = p2.SEBI_INVESTOR_URL
    if mode == "amfi":
        return amfi
    if mode == "sebi":
        return sebi
    h = sum(ord(c) for c in query_key) if query_key else 0
    return amfi if h % 2 == 0 else sebi
