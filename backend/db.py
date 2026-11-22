"""SQLite-Speicher für Cloud-Verbindungen (ADR 0006)."""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass

import config
import crypto

SCHEMA = """
CREATE TABLE IF NOT EXISTS storage (
    user_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    credentials_enc TEXT NOT NULL,
    account_label TEXT NOT NULL DEFAULT '',
    base_path TEXT,
    updated_at INTEGER NOT NULL
)
"""


@dataclass
class Storage:
    user_id: str
    provider: str
    credentials: dict | None  # None = nicht entschlüsselbar (Schlüssel gewechselt)
    account_label: str
    base_path: str | None


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init() -> None:
    with _conn() as con:
        con.execute(SCHEMA)


def get(user_id: str) -> Storage | None:
    with _conn() as con:
        row = con.execute("SELECT * FROM storage WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        return None
    return Storage(row["user_id"], row["provider"], crypto.decrypt(row["credentials_enc"]),
                   row["account_label"], row["base_path"])


def save(user_id: str, provider: str, credentials: dict, account_label: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO storage(user_id, provider, credentials_enc, account_label, base_path, updated_at) "
            "VALUES(?,?,?,?,NULL,?) ON CONFLICT(user_id) DO UPDATE SET provider=excluded.provider, "
            "credentials_enc=excluded.credentials_enc, account_label=excluded.account_label, "
            "base_path=NULL, updated_at=excluded.updated_at",
            (user_id, provider, crypto.encrypt(credentials), account_label, int(time.time())),
        )


def update_credentials(user_id: str, credentials: dict) -> None:
    with _conn() as con:
        con.execute("UPDATE storage SET credentials_enc=?, updated_at=? WHERE user_id=?",
                    (crypto.encrypt(credentials), int(time.time()), user_id))


def set_base_path(user_id: str, path: str) -> None:
    with _conn() as con:
        con.execute("UPDATE storage SET base_path=?, updated_at=? WHERE user_id=?",
                    (path, int(time.time()), user_id))


def delete(user_id: str) -> None:
    with _conn() as con:
        con.execute("DELETE FROM storage WHERE user_id=?", (user_id,))
