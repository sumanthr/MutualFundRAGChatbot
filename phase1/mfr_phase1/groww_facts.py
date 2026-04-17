from __future__ import annotations

import json
import re
from html import escape
from typing import Any


def _next_data_json(html: str) -> dict[str, Any] | None:
    m = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>([\s\S]*?)</script>',
        html,
        re.I,
    )
    if not m:
        return None
    try:
        return json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return None


def _mf_server_side(data: dict[str, Any]) -> dict[str, Any] | None:
    mf = (
        data.get("props", {})
        .get("pageProps", {})
        .get("mfServerSideData")
    )
    return mf if isinstance(mf, dict) else None


def format_key_facts(mf: dict[str, Any]) -> str:
    """Human-readable lines for embedding (expense, exit load, SIP, benchmark, etc.)."""
    lines: list[str] = ["Key scheme facts (from Groww page data):"]

    def add(label: str, val: Any) -> None:
        if val is None or val == "":
            return
        lines.append(f"{label}: {val}")

    add("Fund name", mf.get("fund_name") or mf.get("scheme_name"))
    add("Category", mf.get("category"))
    add("Sub-category", mf.get("sub_category"))
    add("Expense ratio (%)", mf.get("expense_ratio"))
    add("Exit load", mf.get("exit_load"))
    nav = mf.get("nav")
    if nav is not None:
        add("NAV", f"{nav} (as of {mf.get('nav_date', 'date on page')})")
    add("Minimum SIP (INR)", mf.get("min_sip_investment"))
    add("SIP allowed", mf.get("sip_allowed"))
    add("Benchmark", mf.get("benchmark_name") or mf.get("benchmark"))
    add("Risk (as labeled on page)", mf.get("nfo_risk"))

    lock = mf.get("lock_in")
    if isinstance(lock, dict) and lock.get("years") is not None:
        y, mo, d = lock.get("years"), lock.get("months"), lock.get("days")
        add("Lock-in", f"{y}y {mo}m {d}d")

    hist_exit = mf.get("historic_exit_loads")
    if isinstance(hist_exit, list) and hist_exit:
        note = hist_exit[0].get("note") if isinstance(hist_exit[0], dict) else None
        if note:
            add("Exit load (historic note)", note)

    return "\n".join(lines)


def extract_groww_key_facts_block(html: str) -> str:
    """Return multi-line facts string, or empty if not a Groww MF Next.js page."""
    data = _next_data_json(html)
    if not data:
        return ""
    mf = _mf_server_side(data)
    if not mf:
        return ""
    return format_key_facts(mf)


def facts_prefix_html(facts_block: str) -> str:
    """Inject as HTML so chunker keeps a high-signal section at the top."""
    if not facts_block.strip():
        return ""
    safe = escape(facts_block)
    return (
        '<div id="mfr-groww-ssr-facts"><h2>Key scheme facts</h2>'
        f"<pre>{safe}</pre></div>"
    )
