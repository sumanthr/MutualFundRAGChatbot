from __future__ import annotations

from pathlib import Path

DEFAULT_CHROMA_PATH = Path("./chroma_data")
DEFAULT_COLLECTION = "mutual_fund_faq_groww_v1"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

USER_AGENT = (
    "MutualFundRAG-Phase1/0.1 (+https://github.com/; educational RAG indexer; contact: local)"
)
REQUEST_TIMEOUT_S = 30.0
MAX_RETRIES = 3
RETRY_BACKOFF_S = 2.0

# Chunking (see docs/ragChunkingEmbeddingVectorDb.md §2.2)
MAX_CHUNK_CHARS = 512
CHUNK_OVERLAP_CHARS = 96
MIN_CHUNK_CHARS = 100
