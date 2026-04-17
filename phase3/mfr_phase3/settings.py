from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# amfi | sebi | alternate (hash query for stable pick)
REFUSAL_EDUCATION_MODE: str = os.getenv("REFUSAL_EDUCATION_MODE", "alternate").strip().lower()
