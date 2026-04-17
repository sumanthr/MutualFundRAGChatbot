from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from mfr_phase1.config import MAX_RETRIES, REQUEST_TIMEOUT_S, RETRY_BACKOFF_S, USER_AGENT
from mfr_phase1.registry import assert_url_allowlisted

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: int
    html: str
    final_url: str


def fetch_html(url: str) -> FetchResult:
    """HTTP GET with allowlist check, retries on transient errors, and timeouts."""
    assert_url_allowlisted(url)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_S, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                return FetchResult(
                    url=url,
                    status_code=resp.status_code,
                    html=resp.text,
                    final_url=str(resp.url),
                )
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status in (429, 503) and attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF_S * (2**attempt)
                logger.warning("Fetch retry %s for %s (HTTP %s)", attempt + 1, url, status)
                time.sleep(wait)
                continue
            raise
        except (httpx.TimeoutException, httpx.TransportError) as e:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF_S * (2**attempt)
                logger.warning("Fetch retry %s for %s: %s", attempt + 1, url, e)
                time.sleep(wait)
                continue
            raise
