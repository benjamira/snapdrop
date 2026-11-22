"""Konfiguration aus Umgebung und users.yaml (ADR 0003, 0006)."""
from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import yaml

log = logging.getLogger("snapdrop.config")


def _load_env_file(path: str | None) -> None:
    """Secrets aus einer KEY=VALUE-Datei laden, z. B. per Bind-Mount (ADR 0006). Echte Env-Variablen haben Vorrang."""
    if not path or not Path(path).is_file():
        return
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env_file(os.environ.get("SNAPDROP_ENV_FILE"))

PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8000").rstrip("/")
DROPBOX_APP_KEY = os.environ.get("DROPBOX_APP_KEY", "")
DROPBOX_APP_SECRET = os.environ.get("DROPBOX_APP_SECRET", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
DB_PATH = os.environ.get("SNAPDROP_DB", "snapdrop.db")
USERS_FILE = os.environ.get("USERS_FILE", "users.yaml")
STATIC_DIR = os.environ.get("STATIC_DIR", "")
MAX_FILE_BYTES = int(os.environ.get("MAX_FILE_MB", "25")) * 1024 * 1024

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


@dataclass(frozen=True)
class User:
    id: str
    name: str


class UserStore:
    """Liest users.yaml und lädt bei geänderter mtime neu. Ungültige Datei → letzter gültiger Stand."""

    def __init__(self, path: str):
        self.path = Path(path)
        self._mtime: float | None = None
        self._users: dict[str, User] = {}
        self._lock = threading.Lock()

    def _parse(self) -> dict[str, User]:
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        users: dict[str, User] = {}
        for entry in data.get("users") or []:
            uid = str(entry.get("id", "")).strip()
            if not _ID_RE.match(uid):
                raise ValueError(f"ungültige User-ID: {uid!r}")
            if uid in users:
                raise ValueError(f"doppelte User-ID: {uid!r}")
            users[uid] = User(uid, str(entry.get("name") or uid))
        return users

    def _refresh(self) -> None:
        try:
            mtime = self.path.stat().st_mtime
        except FileNotFoundError:
            if self._mtime is not None:
                log.warning("%s fehlt, behalte letzten Stand", self.path)
            return
        if mtime == self._mtime:
            return
        try:
            self._users = self._parse()
            log.info("%d User aus %s geladen", len(self._users), self.path)
        except Exception as exc:  # noqa: BLE001
            log.error("%s ungültig (%s), behalte letzten Stand", self.path, exc)
        self._mtime = mtime

    def all(self) -> list[User]:
        with self._lock:
            self._refresh()
            return list(self._users.values())

    def get(self, uid: str) -> User | None:
        with self._lock:
            self._refresh()
            return self._users.get(uid)


users = UserStore(USERS_FILE)
