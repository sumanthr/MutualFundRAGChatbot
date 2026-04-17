from __future__ import annotations

import argparse
import json
import logging
import sys

from mfr_phase3.respond import answer_query


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 3: PII redaction + expanded routing + AMFI/SEBI refusals; then Phase 2 RAG.",
    )
    parser.add_argument("query", nargs="?", help="User question")
    parser.add_argument("--query", "-q", dest="query_opt", help="User question")
    parser.add_argument("--scheme-slug", help="Optional Chroma metadata filter")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    q = args.query_opt or args.query
    if not q:
        parser.error("Provide a question as a positional argument or use --query")

    try:
        out = answer_query(q, scheme_slug=args.scheme_slug)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    r = out.inner
    if args.json:
        print(
            json.dumps(
                {
                    "sanitized_query": out.sanitized_query,
                    "pii_redacted": out.pii_redacted,
                    "route": r.route,
                    "response_type": r.response_type,
                    "formatted_message": r.formatted_message,
                    "citation_url": r.citation_url,
                    "last_updated_date": r.last_updated_date,
                    "retrieval_count": len(r.retrieval),
                },
                indent=2,
            )
        )
    else:
        print(r.formatted_message)
        print()
        if out.pii_redacted:
            print("(PII fields redacted:", ", ".join(out.pii_redacted), ")", file=sys.stderr)
        print(
            f"(route={r.route}, type={r.response_type}, chunks={len(r.retrieval)})",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
