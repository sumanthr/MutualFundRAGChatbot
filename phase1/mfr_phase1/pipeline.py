from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mfr_phase1.chunking import chunk_source_html, html_to_document_text, stable_chunk_id
from mfr_phase1.config import DEFAULT_COLLECTION, DEFAULT_EMBEDDING_MODEL
from mfr_phase1.groww_facts import extract_groww_key_facts_block, facts_prefix_html
from mfr_phase1.registry import SOURCES, SourceRecord
from mfr_phase1.scrape import fetch_html

logger = logging.getLogger(__name__)


def _metadata_for_chunk(
    source: SourceRecord,
    source_url: str,
    page_title: str,
    ingested_at: str,
    chunk,
) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "source_url": source_url,
        "scheme_slug": source.scheme_slug,
        "scheme_name": source.scheme_name,
        "amc_name": source.amc_name,
        "category": source.category,
        "source_type": source.source_type,
        "section_title": chunk.section_title or "",
        "chunk_index": int(chunk.chunk_index),
        "ingested_at": ingested_at,
        "content_hash": chunk.content_hash,
        "page_title": page_title or "",
        "source_domain": "groww.in",
    }


def run_reindex(
    *,
    chroma_path: Path,
    collection_name: str = DEFAULT_COLLECTION,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Fetch all registry URLs, chunk, embed, upsert into Chroma."""
    batch_ingested_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    summary: dict[str, Any] = {
        "ingested_at": batch_ingested_at,
        "sources_ok": [],
        "sources_failed": [],
        "total_chunks": 0,
    }

    indexer = None
    if not dry_run:
        from mfr_phase1.vectorstore import ChromaIndexer

        chroma_path.mkdir(parents=True, exist_ok=True)
        indexer = ChromaIndexer(chroma_path, collection_name)

    for source in SOURCES:
        try:
            fr = fetch_html(source.url)
            facts = extract_groww_key_facts_block(fr.html)
            augmented_html = facts_prefix_html(facts) + fr.html if facts else fr.html
            chunks = chunk_source_html(augmented_html, source)
            if not chunks:
                raise RuntimeError("No chunks produced (empty parse?)")

            _, page_title = html_to_document_text(fr.html)
            texts = [c.text for c in chunks]
            if dry_run:
                summary["sources_ok"].append(
                    {"url": source.url, "chunks": len(chunks), "dry_run": True}
                )
                summary["total_chunks"] += len(chunks)
                continue

            assert indexer is not None
            from mfr_phase1.embedding import embed_texts

            embeddings = embed_texts(texts, model_name=model_name)
            ids = [stable_chunk_id(source.url, c) for c in chunks]
            metadatas = [
                _metadata_for_chunk(source, source.url, page_title, batch_ingested_at, c)
                for c in chunks
            ]
            indexer.replace_source_chunks(
                source_url=source.url,
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            summary["sources_ok"].append({"url": source.url, "chunks": len(chunks)})
            summary["total_chunks"] += len(chunks)
            logger.info("Indexed %s (%s chunks)", source.url, len(chunks))
        except Exception as e:
            logger.exception("Failed to index %s", source.url)
            summary["sources_failed"].append({"url": source.url, "error": str(e)})

    return summary
