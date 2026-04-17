from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from mfr_phase1.config import DEFAULT_CHROMA_PATH, DEFAULT_COLLECTION, DEFAULT_EMBEDDING_MODEL
from mfr_phase1.pipeline import run_reindex


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 1: scrape Groww scheme pages, chunk, embed (bge-small-en-v1.5), upsert Chroma.",
    )
    parser.add_argument(
        "--chroma-path",
        type=Path,
        default=DEFAULT_CHROMA_PATH,
        help=f"Chroma persist directory (default: {DEFAULT_CHROMA_PATH})",
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help=f"Chroma collection name (default: {DEFAULT_COLLECTION})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_EMBEDDING_MODEL,
        help=f"Sentence-Transformers model id (default: {DEFAULT_EMBEDDING_MODEL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and chunk only; skip embeddings and Chroma writes.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable summary JSON to stdout.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Write ingest summary JSON to this file (for CI/logs; does not suppress normal output).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    summary = run_reindex(
        chroma_path=args.chroma_path,
        collection_name=args.collection,
        model_name=args.model,
        dry_run=args.dry_run,
    )
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("Ingest batch:", summary["ingested_at"])
        print("Chunks indexed:", summary["total_chunks"])
        for row in summary["sources_ok"]:
            print("  OK", row)
        for row in summary["sources_failed"]:
            print("  FAIL", row)

    return 0 if not summary["sources_failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
