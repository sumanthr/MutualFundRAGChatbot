from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ThreadRecord:
    thread_id: str
    scheme_slug: str | None
    updated_at: str


class ThreadStore:
    """SQLite-backed thread isolation (architecture §8)."""

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    scheme_slug TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    meta_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (thread_id) REFERENCES threads(id)
                )
                """
            )
            c.commit()

    def create_thread(self) -> str:
        tid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with self._lock, self._connect() as c:
            c.execute(
                "INSERT INTO threads (id, scheme_slug, updated_at) VALUES (?, ?, ?)",
                (tid, None, now),
            )
            c.commit()
        return tid

    def get_thread(self, thread_id: str) -> ThreadRecord | None:
        with self._connect() as c:
            row = c.execute(
                "SELECT id, scheme_slug, updated_at FROM threads WHERE id = ?",
                (thread_id,),
            ).fetchone()
        if row is None:
            return None
        return ThreadRecord(
            thread_id=str(row["id"]),
            scheme_slug=row["scheme_slug"],
            updated_at=str(row["updated_at"]),
        )

    def ensure_thread(self, thread_id: str | None) -> str:
        """If thread_id is missing or unknown, create a new thread (edgeCases E11.1)."""
        if thread_id:
            if self.get_thread(thread_id):
                return thread_id
        return self.create_thread()

    def set_scheme_slug(self, thread_id: str, scheme_slug: str | None) -> None:
        if not scheme_slug:
            return
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with self._lock, self._connect() as c:
            c.execute(
                "UPDATE threads SET scheme_slug = ?, updated_at = ? WHERE id = ?",
                (scheme_slug, now, thread_id),
            )
            c.commit()

    def get_scheme_slug(self, thread_id: str) -> str | None:
        t = self.get_thread(thread_id)
        return t.scheme_slug if t else None

    def append_message(
        self,
        thread_id: str,
        *,
        role: str,
        content: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        meta_json = json.dumps(meta) if meta else None
        with self._lock, self._connect() as c:
            c.execute(
                """
                INSERT INTO messages (thread_id, role, content, meta_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (thread_id, role, content, meta_json, now),
            )
            c.execute(
                "UPDATE threads SET updated_at = ? WHERE id = ?",
                (now, thread_id),
            )
            c.commit()

    def list_threads(self, limit: int = 50) -> list[ThreadRecord]:
        with self._connect() as c:
            rows = c.execute(
                """
                SELECT id, scheme_slug, updated_at FROM threads
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            ThreadRecord(
                thread_id=str(r["id"]),
                scheme_slug=r["scheme_slug"],
                updated_at=str(r["updated_at"]),
            )
            for r in rows
        ]

    def get_thread_preview(self, thread_id: str, *, max_len: int = 52) -> str | None:
        with self._connect() as c:
            row = c.execute(
                """
                SELECT content FROM messages
                WHERE thread_id = ? AND role = 'user'
                ORDER BY id ASC
                LIMIT 1
                """,
                (thread_id,),
            ).fetchone()
        if row is None:
            return None
        text = str(row["content"]).strip().replace("\n", " ")
        if len(text) > max_len:
            return text[: max_len - 1] + "…"
        return text

    def delete_threads_except(self, keep_thread_id: str | None) -> int:
        """Delete all threads (and their messages). If keep_thread_id is set, retain that thread."""
        with self._lock, self._connect() as c:
            if keep_thread_id:
                c.execute(
                    "DELETE FROM messages WHERE thread_id IN "
                    "(SELECT id FROM threads WHERE id != ?)",
                    (keep_thread_id,),
                )
                cur = c.execute("DELETE FROM threads WHERE id != ?", (keep_thread_id,))
                n = cur.rowcount if cur.rowcount is not None else 0
            else:
                c.execute("DELETE FROM messages")
                cur = c.execute("DELETE FROM threads")
                n = cur.rowcount if cur.rowcount is not None else 0
            c.commit()
        return int(n)

    def recent_messages(self, thread_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as c:
            rows = c.execute(
                """
                SELECT role, content, meta_json, created_at
                FROM messages
                WHERE thread_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (thread_id, limit),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in reversed(rows):
            meta = json.loads(row["meta_json"]) if row["meta_json"] else None
            out.append(
                {
                    "role": row["role"],
                    "content": row["content"],
                    "meta": meta,
                    "created_at": row["created_at"],
                }
            )
        return out
