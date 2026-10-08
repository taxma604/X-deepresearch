"""SQLite persistence for local research jobs; never stores X cookies."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


class SQLiteJobStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS research_jobs "
                "(job_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        if self.path.is_symlink():
            raise ValueError("SQLite database must not be a symlink.")
        if not self.path.exists():
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        if os.name == "posix" and self.path.stat().st_mode & 0o077:
            raise ValueError("SQLite database must be owner-only (chmod 600).")
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def save(self, job: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO research_jobs (job_id,payload) VALUES (?,?) "
                "ON CONFLICT(job_id) DO UPDATE SET payload=excluded.payload",
                (job["job_id"], json.dumps(job, ensure_ascii=False)),
            )

    def load_all(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT payload FROM research_jobs").fetchall()
        return [json.loads(row[0]) for row in rows]

    def delete(self, job_id: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM research_jobs WHERE job_id=?", (job_id,))
