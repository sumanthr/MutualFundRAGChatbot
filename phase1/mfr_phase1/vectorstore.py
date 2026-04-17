from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb


class ChromaIndexer:
    def __init__(self, persist_path: Path, collection_name: str) -> None:
        self._client = chromadb.PersistentClient(path=str(persist_path))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def replace_source_chunks(
        self,
        source_url: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Delete existing vectors for source_url, then add new rows (no orphan chunks)."""
        self._collection.delete(where={"source_url": source_url})
        if not ids:
            return
        self._collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    @property
    def collection(self):
        return self._collection
