from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mfr_phase5.corpus_stats import corpus_stats
from mfr_phase5.hybrid_demo import hybrid_demo
from mfr_phase5.runner import print_report, run_eval


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 5: eval, corpus stats, hybrid demo.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_eval = sub.add_parser("eval", help="Run regression cases (see cases.json).")
    p_eval.add_argument("--cases", type=Path, help="Override cases JSON path")
    p_eval.add_argument(
        "--include-groq",
        action="store_true",
        help="Run cases that require Groq even if GROQ_API_KEY is empty (will fail).",
    )
    p_eval.add_argument("--json-out", type=Path, help="Write full report JSON")

    p_stat = sub.add_parser("corpus-stats", help="Chroma collection count + ingested_at range.")

    p_h = sub.add_parser("hybrid-demo", help="BM25 + vector RRF ranking demo (needs rank-bm25).")
    p_h.add_argument("query")
    p_h.add_argument("--top-k", type=int, default=8)

    args = parser.parse_args(argv)

    if args.cmd == "eval":
        skip_groq = not args.include_groq
        report = run_eval(cases_path=args.cases, skip_groq_cases=skip_groq)
        print_report(report)
        if args.json_out:
            args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        failed = report["summary"].get("failed", 0)
        return 0 if failed == 0 else 1

    if args.cmd == "corpus-stats":
        print(json.dumps(corpus_stats(), indent=2))
        return 0

    if args.cmd == "hybrid-demo":
        try:
            out = hybrid_demo(args.query, top_k=args.top_k)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            return 2
        print(json.dumps(out, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
