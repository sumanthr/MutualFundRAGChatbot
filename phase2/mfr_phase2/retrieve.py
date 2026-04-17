from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb

from mfr_phase1.embedding import embed_texts
from mfr_phase2 import settings as phase2_settings


@dataclass(frozen=True)
class RetrievedChunk:
    document: str
    metadata: dict[str, Any]
    distance: float | None


def retrieve(
    query: str,
    *,
    chroma_path: Path,
    collection_name: str,
    embedding_model: str,
    top_k: int = 8,
    scheme_slug: str | None = None,
    max_distance: float | None = None,
) -> list[RetrievedChunk]:
    """Vector search over Chroma (Phase 2 minimum: no BM25)."""
    q_emb = embed_texts([query], model_name=embedding_model)
    if not q_emb:
        return []

    client = chromadb.PersistentClient(path=str(chroma_path))
    coll = client.get_collection(name=collection_name)
    where: dict[str, Any] | None = None
    if scheme_slug:
        where = {"scheme_slug": scheme_slug}

    res = coll.query(
        query_embeddings=q_emb,
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    out: list[RetrievedChunk] = []
    docs = res.get("documents") or [[]]
    metas = res.get("metadatas") or [[]]
    dists = res.get("distances") or [[]]
    row_docs = docs[0] if docs else []
    row_metas = metas[0] if metas else []
    row_dists = dists[0] if dists else []
    for i, text in enumerate(row_docs):
        meta = dict(row_metas[i]) if i < len(row_metas) and row_metas[i] else {}
        dist = float(row_dists[i]) if i < len(row_dists) and row_dists[i] is not None else None
        out.append(RetrievedChunk(document=text or "", metadata=meta, distance=dist))

    lim = max_distance if max_distance is not None else phase2_settings.RETRIEVAL_MAX_DISTANCE
    if lim > 0:
        out = [c for c in out if c.distance is not None and c.distance <= lim]
    return out


def allowed_citation_urls(chunks: list[RetrievedChunk]) -> set[str]:
    urls: set[str] = set()
    for c in chunks:
        u = c.metadata.get("source_url")
        if isinstance(u, str) and u.startswith("http"):
            urls.add(u)
    return urls


def max_ingested_at(chunks: list[RetrievedChunk]) -> str | None:
    """Latest batch timestamp from chunk metadata (ISO strings compare lexicographically for UTC)."""
    times = [c.metadata.get("ingested_at") for c in chunks]
    vals = [t for t in times if isinstance(t, str) and t]
    return max(vals) if vals else None
