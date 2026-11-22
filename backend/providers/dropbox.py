"""Dropbox per HTTP-API (ADR 0004)."""
from __future__ import annotations

import json
import time
from urllib.parse import urlencode

import httpx

import config
from .base import AuthError, ProviderError

AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
API = "https://api.dropboxapi.com/2"
CONTENT = "https://content.dropboxapi.com/2"
SCOPES = "files.metadata.read files.content.read files.content.write account_info.read"


def redirect_uri() -> str:
    return f"{config.PUBLIC_URL}/api/dropbox/callback"


def authorize_url(state: str) -> str:
    return AUTH_URL + "?" + urlencode({
        "client_id": config.DROPBOX_APP_KEY,
        "response_type": "code",
        "token_access_type": "offline",
        "redirect_uri": redirect_uri(),
        "scope": SCOPES,
        "state": state,
    })


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(TOKEN_URL, data={
            "code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri(),
        }, auth=(config.DROPBOX_APP_KEY, config.DROPBOX_APP_SECRET))
    if r.status_code != 200:
        raise ProviderError(f"Dropbox-Anmeldung fehlgeschlagen: {r.text[:200]}", 400)
    tok = r.json()
    if "refresh_token" not in tok:
        raise ProviderError("Dropbox hat kein Refresh-Token geliefert", 400)
    return {"refresh_token": tok["refresh_token"], "account_id": tok.get("account_id", "")}


async def account_label(access_token: str) -> str:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{API}/users/get_current_account",
                         headers={"Authorization": f"Bearer {access_token}"})
    if r.status_code != 200:
        return "Dropbox"
    d = r.json()
    return d.get("email") or d.get("name", {}).get("display_name") or "Dropbox"


# Access-Tokens nur im Speicher: refresh_token -> (token, ablauf)
_token_cache: dict[str, tuple[str, float]] = {}


async def access_token(refresh_token: str) -> str:
    cached = _token_cache.get(refresh_token)
    if cached and cached[1] > time.time() + 60:
        return cached[0]
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(TOKEN_URL, data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                         auth=(config.DROPBOX_APP_KEY, config.DROPBOX_APP_SECRET))
    if r.status_code in (400, 401):
        raise AuthError()
    if r.status_code != 200:
        raise ProviderError(f"Dropbox-Token-Erneuerung fehlgeschlagen ({r.status_code})")
    tok = r.json()
    _token_cache[refresh_token] = (tok["access_token"], time.time() + int(tok.get("expires_in", 14400)))
    return tok["access_token"]


def _dbx_path(path: str) -> str:
    # Dropbox: Wurzel = "", sonst mit führendem /
    return "" if path in ("", "/") else path


class DropboxProvider:
    def __init__(self, credentials: dict):
        self.refresh_token = credentials["refresh_token"]

    async def _rpc(self, endpoint: str, args: dict) -> dict:
        token = await access_token(self.refresh_token)
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{API}/{endpoint}", json=args, headers={"Authorization": f"Bearer {token}"})
        return self._check(r)

    @staticmethod
    def _check(r: httpx.Response) -> dict:
        if r.status_code == 401:
            raise AuthError()
        if r.status_code == 409:
            raise ProviderError(f"Dropbox: {r.json().get('error_summary', 'Konflikt')}", 409)
        if r.status_code != 200:
            raise ProviderError(f"Dropbox-Fehler {r.status_code}: {r.text[:200]}")
        return r.json()

    async def list_folders(self, path: str) -> list[str]:
        res = await self._rpc("files/list_folder", {"path": _dbx_path(path), "limit": 2000})
        entries = list(res["entries"])
        while res.get("has_more"):
            res = await self._rpc("files/list_folder/continue", {"cursor": res["cursor"]})
            entries += res["entries"]
        return sorted((e["name"] for e in entries if e[".tag"] == "folder"), key=str.casefold)

    async def create_folder(self, path: str) -> None:
        await self._rpc("files/create_folder_v2", {"path": path, "autorename": False})

    async def ensure_folder(self, path: str) -> None:
        try:
            await self.create_folder(path)
        except ProviderError as e:
            if e.status == 409 and "conflict/folder" in str(e):
                return
            raise

    async def upload(self, path: str, data: bytes) -> str:
        token = await access_token(self.refresh_token)
        arg = {"path": path, "mode": "add", "autorename": True, "mute": False}
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(f"{CONTENT}/files/upload", content=data, headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream",
                "Dropbox-API-Arg": json.dumps(arg, ensure_ascii=True),
            })
        return self._check(r)["path_display"]
