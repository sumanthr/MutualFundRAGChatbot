from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from mfr_phase2 import settings as p2
from mfr_phase3.respond import answer_query

from mfr_phase5.checks import check_expectations, check_response_format
from mfr_phase5.load_cases import load_cases


@dataclass
class CaseResult:
    id: str
    skipped: bool
    skip_reason: str | None
    ok: bool
    route: str | None
    response_type: str | None
    citation_url: str | None
    pii_redacted: list[str]
    retrieval_count: int
    format_violations: list[str]
    expectation_violations: list[str]
    error: str | None


def run_eval(
    *,
    cases_path: Path | None = None,
    skip_groq_cases: bool | None = None,
) -> dict[str, Any]:
    if skip_groq_cases is None:
        skip_groq_cases = not (p2.GROQ_API_KEY or "").strip()

    cases = load_cases(cases_path)
    results: list[CaseResult] = []

    for c in cases:
        cid = str(c.get("id", "unknown"))
        requires_groq = bool(c.get("requires_groq", False))
        if requires_groq and skip_groq_cases:
            results.append(
                CaseResult(
                    id=cid,
                    skipped=True,
                    skip_reason="requires_groq",
                    ok=True,
                    route=None,
                    response_type=None,
                    citation_url=None,
                    pii_redacted=[],
                    retrieval_count=0,
                    format_violations=[],
                    expectation_violations=[],
                    error=None,
                )
            )
            continue

        query = str(c["query"])
        scheme = c.get("scheme_slug")
        scheme_slug = str(scheme).strip() if scheme else None

        try:
            out = answer_query(query, scheme_slug=scheme_slug)
            inner = out.inner
            fmt = check_response_format(inner.formatted_message, inner.citation_url)
            exp = check_expectations(
                route=inner.route,
                response_type=inner.response_type,
                citation_url=inner.citation_url,
                expect_route=c.get("expect_route"),
                expect_response_type=c.get("expect_response_type"),
                citation_should_be_regulatory=c.get("citation_should_be_regulatory"),
                citation_should_be_groww=c.get("citation_should_be_groww"),
            )
            ok = fmt.ok and exp.ok
            results.append(
                CaseResult(
                    id=cid,
                    skipped=False,
                    skip_reason=None,
                    ok=ok,
                    route=inner.route,
                    response_type=inner.response_type,
                    citation_url=inner.citation_url,
                    pii_redacted=list(out.pii_redacted),
                    retrieval_count=len(inner.retrieval),
                    format_violations=list(fmt.violations),
                    expectation_violations=list(exp.violations),
                    error=None,
                )
            )
        except Exception as e:
            results.append(
                CaseResult(
                    id=cid,
                    skipped=False,
                    skip_reason=None,
                    ok=False,
                    route=None,
                    response_type=None,
                    citation_url=None,
                    pii_redacted=[],
                    retrieval_count=0,
                    format_violations=[],
                    expectation_violations=[],
                    error=str(e),
                )
            )

    ran = [r for r in results if not r.skipped]
    passed = [r for r in ran if r.ok]
    failed = [r for r in ran if not r.ok]

    summary = {
        "total": len(results),
        "skipped": sum(1 for r in results if r.skipped),
        "ran": len(ran),
        "passed": len(passed),
        "failed": len(failed),
        "skip_groq_cases": skip_groq_cases,
    }
    return {
        "summary": summary,
        "results": [asdict(r) for r in results],
    }


def print_report(report: dict[str, Any]) -> None:
    s = report["summary"]
    print("Phase 5 eval summary")
    print(json.dumps(s, indent=2))
    for r in report["results"]:
        if r.get("skipped"):
            print(f"  SKIP {r['id']}: {r.get('skip_reason')}")
            continue
        status = "PASS" if r.get("ok") else "FAIL"
        print(f"  {status} {r['id']} route={r.get('route')} type={r.get('response_type')}")
        if r.get("error"):
            print(f"       error: {r['error']}")
        if r.get("format_violations"):
            print(f"       format: {r['format_violations']}")
        if r.get("expectation_violations"):
            print(f"       expect: {r['expectation_violations']}")
