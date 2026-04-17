from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from mfr_phase2.validator import count_http_urls, count_sentences, extract_footer_date


def _answer_body_only(formatted_message: str) -> str:
    t = formatted_message.strip()
    if "\n\nSource: " in t:
        t = t.split("\n\nSource: ", 1)[0].strip()
    return t


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


_REGULATORY_HOSTS = frozenset(
    {
        "www.amfiindia.com",
        "amfiindia.com",
        "www.sebi.gov.in",
        "sebi.gov.in",
        "investor.sebi.gov.in",
    }
)


@dataclass(frozen=True)
class FormatCheckResult:
    ok: bool
    violations: list[str]


def check_response_format(formatted_message: str, citation_url: str, max_sentences: int = 3) -> FormatCheckResult:
    """Problem statement: footer, one citation URL in user-visible blob."""
    v: list[str] = []
    if not extract_footer_date(formatted_message):
        v.append("missing_footer_date")
    n_urls = count_http_urls(formatted_message)
    if n_urls < 1:
        v.append("no_url_in_message")
    if n_urls > 1:
        v.append(f"too_many_urls:{n_urls}")
    body = _answer_body_only(formatted_message)
    if count_sentences(body) > max_sentences:
        v.append(f"too_many_sentences:{count_sentences(body)}")
    if not citation_url.startswith("http"):
        v.append("citation_url_invalid")
    return FormatCheckResult(ok=len(v) == 0, violations=v)


def host_is_groww_scheme(url: str) -> bool:
    h = _host(url)
    if h != "groww.in":
        return False
    p = urlparse(url).path.lower()
    return "/mutual-funds/" in p


def host_is_regulatory_education(url: str) -> bool:
    return _host(url) in _REGULATORY_HOSTS


@dataclass(frozen=True)
class ExpectationResult:
    ok: bool
    violations: list[str]


def check_expectations(
    *,
    route: str,
    response_type: str,
    citation_url: str,
    expect_route: str | None = None,
    expect_response_type: str | None = None,
    citation_should_be_regulatory: bool | None = None,
    citation_should_be_groww: bool | None = None,
) -> ExpectationResult:
    v: list[str] = []
    if expect_route is not None and route != expect_route:
        v.append(f"route_want:{expect_route}_got:{route}")
    if expect_response_type is not None and response_type != expect_response_type:
        v.append(f"type_want:{expect_response_type}_got:{response_type}")
    if citation_should_be_regulatory and not host_is_regulatory_education(citation_url):
        v.append("citation_not_regulatory")
    if citation_should_be_groww and not host_is_groww_scheme(citation_url):
        v.append("citation_not_groww_scheme")
    return ExpectationResult(ok=len(v) == 0, violations=v)
