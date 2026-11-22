from __future__ import annotations

from typing import Protocol


class ProviderError(Exception):
    """Fehler beim Cloudspeicher; message ist für den Nutzer gedacht."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


class AuthError(ProviderError):
    """Zugang ungültig/widerrufen → neu verbinden."""

    def __init__(self, message: str = "Zugang zum Cloudspeicher ungültig – bitte neu verbinden"):
        super().__init__(message, 401)


class Provider(Protocol):
    async def list_folders(self, path: str) -> list[str]: ...
    async def create_folder(self, path: str) -> None: ...
    async def ensure_folder(self, path: str) -> None: ...
    async def upload(self, path: str, data: bytes) -> str: ...
