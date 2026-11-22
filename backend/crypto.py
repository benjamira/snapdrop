"""Verschlüsselung der Zugangsdaten und signierter OAuth-State (ADR 0006)."""
from __future__ import annotations

import json
import logging

from cryptography.fernet import Fernet, InvalidToken

import config

log = logging.getLogger("snapdrop.crypto")

if config.SECRET_KEY:
    _fernet = Fernet(config.SECRET_KEY.encode())
else:  # nur für lokale Entwicklung
    log.warning("SECRET_KEY fehlt – erzeuge flüchtigen Schlüssel (Verbindungen überleben keinen Neustart)")
    _fernet = Fernet(Fernet.generate_key())


def encrypt(data: dict) -> str:
    return _fernet.encrypt(json.dumps(data).encode()).decode()


def decrypt(token: str, ttl: int | None = None) -> dict | None:
    try:
        return json.loads(_fernet.decrypt(token.encode(), ttl=ttl))
    except (InvalidToken, ValueError):
        return None
