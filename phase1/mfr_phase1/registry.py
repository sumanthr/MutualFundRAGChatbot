from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    url: str
    scheme_slug: str
    scheme_name: str
    amc_name: str
    category: str
    source_type: str


SOURCES: Final[tuple[SourceRecord, ...]] = (
    SourceRecord(
        source_id="groww_hdfc_mid_cap_direct_g",
        url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        scheme_slug="hdfc-mid-cap-fund-direct-growth",
        scheme_name="HDFC Mid Cap Fund Direct Growth",
        amc_name="HDFC Mutual Fund",
        category="mid-cap",
        source_type="aggregator_scheme_page",
    ),
    SourceRecord(
        source_id="groww_hdfc_equity_direct_g",
        url="https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        scheme_slug="hdfc-equity-fund-direct-growth",
        scheme_name="HDFC Equity Fund Direct Growth",
        amc_name="HDFC Mutual Fund",
        category="equity",
        source_type="aggregator_scheme_page",
    ),
    SourceRecord(
        source_id="groww_hdfc_focused_direct_g",
        url="https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
        scheme_slug="hdfc-focused-fund-direct-growth",
        scheme_name="HDFC Focused Fund Direct Growth",
        amc_name="HDFC Mutual Fund",
        category="focused",
        source_type="aggregator_scheme_page",
    ),
    SourceRecord(
        source_id="groww_hdfc_elss_direct_g",
        url="https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
        scheme_slug="hdfc-elss-tax-saver-fund-direct-plan-growth",
        scheme_name="HDFC ELSS Tax Saver Fund Direct Plan Growth",
        amc_name="HDFC Mutual Fund",
        category="elss",
        source_type="aggregator_scheme_page",
    ),
    SourceRecord(
        source_id="groww_hdfc_large_cap_direct_g",
        url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        scheme_slug="hdfc-large-cap-fund-direct-growth",
        scheme_name="HDFC Large Cap Fund Direct Growth",
        amc_name="HDFC Mutual Fund",
        category="large-cap",
        source_type="aggregator_scheme_page",
    ),
)


def normalized_url_key(url: str) -> tuple[str, str, str]:
    p = urlparse(url.strip())
    if p.scheme not in ("http", "https"):
        raise ValueError(f"URL must be http(s): {url}")
    scheme = p.scheme.lower()
    host = (p.hostname or "").lower()
    path = (p.path or "").rstrip("/")
    if not path:
        path = "/"
    return (scheme, host, path)


_ALLOWED_KEYS: frozenset[tuple[str, str, str]] = frozenset(normalized_url_key(s.url) for s in SOURCES)


def assert_url_allowlisted(url: str) -> None:
    key = normalized_url_key(url)
    if key not in _ALLOWED_KEYS:
        raise ValueError(f"URL not in Phase 1 ingest registry: {url}")


def source_for_url(url: str) -> SourceRecord:
    key = normalized_url_key(url)
    for s in SOURCES:
        if normalized_url_key(s.url) == key:
            return s
    raise KeyError(url)
