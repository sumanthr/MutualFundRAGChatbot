from __future__ import annotations

from typing import Any

import chromadb

from mfr_phase2.settings import CHROMA_COLLECTION, CHROMA_PATH


def corpus_stats(*, sample_limit: int = 500) -> dict[str, Any]:
    """Ingest freshness signals (architecture §13) — max/min ingested_at in sample."""
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    coll = client.get_collection(CHROMA_COLLECTION)
    n = coll.count()
    if n == 0:
        return {
            "collection": CHROMA_COLLECTION,
            "chroma_path": str(CHROMA_PATH),
            "approx_count": 0,
            "sample_size": 0,
            "ingested_at_min": None,
            "ingested_at_max": None,
        }
    data = coll.get(include=["metadatas"], limit=min(sample_limit, n))
    metas = data.get("metadatas") or []
    times = [m.get("ingested_at") for m in metas if isinstance(m, dict) and m.get("ingested_at")]
    times_s = [str(t) for t in times if t]
    return {
        "collection": CHROMA_COLLECTION,
        "chroma_path": str(CHROMA_PATH),
        "approx_count": n,
        "sample_size": len(metas),
        "ingested_at_min": min(times_s) if times_s else None,
        "ingested_at_max": max(times_s) if times_s else None,
    }
