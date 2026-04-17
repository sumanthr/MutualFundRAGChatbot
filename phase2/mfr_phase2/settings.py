from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Groq — required for Phase 2 answer generation (not for Phase 1 index)
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY") or None
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_BASE: str = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1").rstrip("/")

# Shared with Phase 1
CHROMA_PATH: Path = Path(os.getenv("CHROMA_PATH", "./chroma_data"))
CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "mutual_fund_faq_groww_v1")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

# Official education link for refusal paths (problem statement)
AMFI_INVESTOR_EDUCATION_URL: str = os.getenv(
    "AMFI_INVESTOR_EDUCATION_URL",
    "https://www.amfiindia.com/investor/knowledge-center",
)

SEBI_INVESTOR_URL: str = os.getenv(
    "SEBI_INVESTOR_URL",
    "https://investor.sebi.gov.in/",
)

RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "12"))

# Cosine distance in Chroma (lower = closer). Drop weak matches so unrelated queries
# do not get forced factual answers from generic "mutual fund" chunks.
RETRIEVAL_MAX_DISTANCE: float = float(os.getenv("RETRIEVAL_MAX_DISTANCE", "0.325"))
