from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

THREAD_DB_PATH: Path = Path(os.getenv("THREAD_DB_PATH", "./data/threads.sqlite3"))
