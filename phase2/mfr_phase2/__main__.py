from __future__ import annotations

import argparse
import json
import logging
import sys

from mfr_phase2.respond import answer_query


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 2: retrieve from Chroma, answer with Groq, validate format.",
    )
    parser.add_argument("query", nargs="?", help="User question (or pass via --query)")
    parser.add_argument("--query", "-q", dest="query_opt", help="User question")
    parser.add_argument("--scheme-slug", help="Optional Chroma metadata filter, e.g. hdfc-mid-cap-fund-direct-growth")
    parser.add_argument("--json", action="store_true", help="Print JSON result to stdout")
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
        result = answer_query(q, scheme_slug=args.scheme_slug)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "route": result.route,
                    "response_type": result.response_type,
                    "formatted_message": result.formatted_message,
                    "citation_url": result.citation_url,
                    "last_updated_date": result.last_updated_date,
                    "retrieval_count": len(result.retrieval),
                },
                indent=2,
            )
        )
    else:
        print(result.formatted_message)
        print()
        print(f"(route={result.route}, type={result.response_type}, chunks={len(result.retrieval)})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
