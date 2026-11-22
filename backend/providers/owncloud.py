"""ownCloud/Nextcloud per WebDAV mit App-Passwort (ADR 0005)."""
from __future__ import annotations

import posixpath
import xml.etree.ElementTree as ET
from urllib.parse import quote, unquote, urlparse

import httpx

from .base import AuthError, ProviderError

PROPFIND_BODY = (
    '<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/></d:prop></d:propfind>'
)


def normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    # Nutzer kopiert oft die WebDAV-URL oder /index.php mit
    for suffix in ("/remote.php/webdav", "/remote.php/dav", "/index.php"):
        if suffix in url:
            url = url[: url.index(suffix)]
    return url


class OwncloudProvider:
    def __init__(self, credentials: dict):
        self.url = credentials["url"]
        self.user = credentials["user"]
        self.password = credentials["password"]
        self.root = f"{self.url}/remote.php/dav/files/{quote(self.user)}"

    def _href(self, path: str) -> str:
        p = path.strip("/")
        return self.root + (quote("/" + p) + "/" if p else "/")

    def _file_href(self, path: str) -> str:
        return self.root + quote("/" + path.strip("/"))

    async def _req(self, method: str, url: str, **kw) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=kw.pop("timeout", 30), auth=(self.user, self.password)) as c:
                r = await c.request(method, url, **kw)
        except httpx.HTTPError as e:
            raise ProviderError(f"ownCloud nicht erreichbar: {e}") from e
        if r.status_code == 401:
            raise AuthError("ownCloud: Benutzername oder App-Passwort falsch")
        return r

    async def test(self) -> None:
        r = await self._req("PROPFIND", self._href(""), headers={"Depth": "0"}, content=PROPFIND_BODY)
        if r.status_code != 207:
            raise ProviderError(f"ownCloud antwortet unerwartet ({r.status_code}) – URL prüfen", 400)

    async def list_folders(self, path: str) -> list[str]:
        href = self._href(path)
        r = await self._req("PROPFIND", href, headers={"Depth": "1"}, content=PROPFIND_BODY)
        if r.status_code == 404:
            raise ProviderError("Ordner nicht gefunden", 404)
        if r.status_code != 207:
            raise ProviderError(f"ownCloud-Fehler {r.status_code}")
        own = unquote(urlparse(href).path).rstrip("/")
        names = []
        ns = {"d": "DAV:"}
        for resp in ET.fromstring(r.content).findall("d:response", ns):
            h = unquote(urlparse(resp.findtext("d:href", "", ns)).path).rstrip("/")
            if h == own:
                continue
            if resp.find(".//d:resourcetype/d:collection", ns) is not None:
                names.append(posixpath.basename(h))
        return sorted(names, key=str.casefold)

    async def create_folder(self, path: str) -> None:
        r = await self._req("MKCOL", self._href(path))
        if r.status_code == 405:
            raise ProviderError("Ordner existiert bereits", 409)
        if r.status_code not in (201,):
            raise ProviderError(f"Ordner anlegen fehlgeschlagen ({r.status_code})")

    async def ensure_folder(self, path: str) -> None:
        try:
            await self.create_folder(path)
        except ProviderError as e:
            if e.status != 409:
                raise

    async def _exists(self, path: str) -> bool:
        r = await self._req("PROPFIND", self._file_href(path), headers={"Depth": "0"}, content=PROPFIND_BODY)
        return r.status_code == 207

    async def upload(self, path: str, data: bytes) -> str:
        # PUT überschreibt → freien Namen suchen (ADR 0005/0008)
        stem, ext = posixpath.splitext(path)
        target, n = path, 1
        while await self._exists(target):
            n += 1
            target = f"{stem} ({n}){ext}"
        r = await self._req("PUT", self._file_href(target), content=data, timeout=120)
        if r.status_code not in (200, 201, 204):
            raise ProviderError(f"Upload fehlgeschlagen ({r.status_code})")
        return target
