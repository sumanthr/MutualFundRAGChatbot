from __future__ import annotations

import re
from dataclasses import dataclass

# Do not log raw matches — only labels (architecture §7.2, edgeCases E10).

_PAN = re.compile(r"\b[A-Z]{3}[PCHABGJLFT][A-Z]\d{4}[A-Z]\b", re.I)
_AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_EMAIL = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.I,
)
_PHONE_IN = re.compile(
    r"(?:(?:\+|00)91[\s.-]?)?(?:[6-9]\d{9}|\d{5}[\s.-]?\d{5})\b",
)
_OTP = re.compile(
    r"\b(?:otp|one[- ]?time(?: password)?)\b[:\s]+(\d{4,8})\b",
    re.I,
)
_ACCOUNT_LONG = re.compile(
    r"\b(?:account|a/c|a\/c|folio)[\s#:No.-]*(\d{8,18})\b",
    re.I,
)


@dataclass(frozen=True)
class PIISanitizeResult:
    text: str
    redacted_labels: list[str]
    retrieval_text: str


def _retrieval_query(sanitized_text: str) -> str:
    """Strip redaction tokens and lightly expand so embeddings match corpus (edge E10)."""
    q = re.sub(r"\[REDACTED\]\s*", "", sanitized_text)
    q = re.sub(r"\bmy email is\s*", "", q, flags=re.I)
    q = re.sub(r"\s+", " ", q).strip()
    ql = q.lower()
    if "exit load" in ql and "mutual" not in ql:
        q = f"{q} mutual fund"
    return q


def sanitize_query(text: str) -> PIISanitizeResult:
    """Redact PII-like patterns; return labels only (no raw values in logs)."""
    labels: list[str] = []
    out = text

    if _PAN.search(out):
        labels.append("pan")
        out = _PAN.sub("[REDACTED]", out)
    if _AADHAAR.search(out):
        labels.append("aadhaar")
        out = _AADHAAR.sub("[REDACTED]", out)
    if _EMAIL.search(out):
        labels.append("email")
        out = _EMAIL.sub("[REDACTED]", out)
    if _PHONE_IN.search(out):
        labels.append("phone")
        out = _PHONE_IN.sub("[REDACTED]", out)

    def _otp_repl(m: re.Match) -> str:
        return m.group(0).replace(m.group(1), "[REDACTED]")

    if _OTP.search(out):
        labels.append("otp")
        out = _OTP.sub(_otp_repl, out)

    def _acct_repl(m: re.Match) -> str:
        return m.group(0).replace(m.group(1), "[REDACTED]")

    if _ACCOUNT_LONG.search(out):
        labels.append("account_number")
        out = _ACCOUNT_LONG.sub(_acct_repl, out)

    out = re.sub(r"\s+", " ", out).strip()
    return PIISanitizeResult(
        text=out,
        redacted_labels=sorted(set(labels)),
        retrieval_text=_retrieval_query(out),
    )
