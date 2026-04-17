from __future__ import annotations

from typing import Any

import chromadb

from mfr_phase1.embedding import embed_texts
from mfr_phase2.settings import CHROMA_COLLECTION, CHROMA_PATH, EMBEDDING_MODEL


def _rrf(rank_lists: list[list[str]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranks in rank_lists:
        for i, doc_id in enumerate(ranks):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + i + 1)
    return scores


def hybrid_demo(
    query: str,
    *,
    top_k: int = 8,
    rrf_k: int = 60,
) -> dict[str, Any]:
    """
    Optional BM25 + vector RRF demo (architecture §4.3 Phase 5).
    Requires: pip install rank-bm25
    """
    try:
        from rank_bm25 import BM25Okapi  # type: ignore
    except ImportError as e:
        raise RuntimeError("Install optional dependency: pip install rank-bm25") from e

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    coll = client.get_collection(CHROMA_COLLECTION)
    data = coll.get(include=["documents", "metadatas"])
    ids = data.get("ids") or []
    docs = data.get("documents") or []
    if not ids or not docs:
        return {"error": "empty_collection", "ids": 0}

    tokenized = [str(d).lower().split() for d in docs]
    bm25 = BM25Okapi(tokenized)
    q_tok = query.lower().split()
    bm25_scores = bm25.get_scores(q_tok)
    bm25_order = sorted(range(len(ids)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]
    bm25_ids = [ids[i] for i in bm25_order]

    q_emb = embed_texts([query], model_name=EMBEDDING_MODEL)
    vres = coll.query(query_embeddings=q_emb, n_results=top_k, include=[])
    vec_ids = (vres.get("ids") or [[]])[0]

    fused = _rrf([bm25_ids, vec_ids], k=rrf_k)
    ranked = sorted(fused.keys(), key=lambda x: fused[x], reverse=True)[:top_k]

    return {
        "query": query,
        "top_k": top_k,
        "bm25_top_ids": bm25_ids,
        "vector_top_ids": vec_ids,
        "rrf_top_ids": ranked,
        "rrf_scores": {i: round(fused[i], 6) for i in ranked},
    }
