"""snapdrop – Fotos unter einem Titel in Dropbox/ownCloud ablegen."""
from __future__ import annotations

import logging
import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import crypto
import db
import naming
from providers import dropbox
from providers.base import AuthError, ProviderError
from providers.dropbox import DropboxProvider
from providers.owncloud import OwncloudProvider, normalize_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("snapdrop")
logging.getLogger("httpx").setLevel(logging.WARNING)
TZ = ZoneInfo(os.environ.get("TZ") or "UTC")

app = FastAPI(title="snapdrop", docs_url=None, redoc_url=None)
db.init()


@app.exception_handler(ProviderError)
async def provider_error(_: Request, exc: ProviderError):
    return JSONResponse({"detail": str(exc), "reconnect": isinstance(exc, AuthError)}, status_code=exc.status)


def _user(uid: str) -> config.User:
    u = config.users.get(uid)
    if not u:
        raise HTTPException(404, "User unbekannt")
    return u


def _storage(uid: str) -> db.Storage:
    _user(uid)
    st = db.get(uid)
    if not st or st.credentials is None:
        raise HTTPException(409, "Kein Cloudspeicher verbunden")
    return st


def _provider(st: db.Storage):
    if st.provider == "dropbox":
        return DropboxProvider(st.credentials)
    if st.provider == "owncloud":
        return OwncloudProvider(st.credentials)
    raise HTTPException(500, f"Unbekannter Provider {st.provider}")


# ---------- Allgemein ----------

@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/users")
def list_users():
    return [{"id": u.id, "name": u.name} for u in config.users.all()]


@app.get("/api/providers")
def providers():
    return {"dropbox": bool(config.DROPBOX_APP_KEY and config.DROPBOX_APP_SECRET), "owncloud": True}


@app.get("/api/users/{uid}/storage")
def storage_status(uid: str):
    _user(uid)
    st = db.get(uid)
    if not st:
        return {"connected": False}
    if st.credentials is None:  # Schlüssel gewechselt (ADR 0006)
        return {"connected": False, "broken": True}
    return {"connected": True, "provider": st.provider, "account": st.account_label, "base_path": st.base_path}


@app.delete("/api/users/{uid}/storage")
def storage_delete(uid: str):
    _user(uid)
    db.delete(uid)
    return {"ok": True}


# ---------- Dropbox OAuth (ADR 0004) ----------

@app.get("/api/users/{uid}/dropbox/start")
def dropbox_start(uid: str):
    _user(uid)
    if not (config.DROPBOX_APP_KEY and config.DROPBOX_APP_SECRET):
        raise HTTPException(503, "Dropbox ist nicht konfiguriert")
    state = crypto.encrypt({"uid": uid, "n": secrets.token_urlsafe(8), "t": int(time.time())})
    return RedirectResponse(dropbox.authorize_url(state))


def _back(uid: str | None, **params) -> RedirectResponse:
    q = {"user": uid, **params} if uid else params
    return RedirectResponse("/?" + urlencode(q))


@app.get("/api/dropbox/callback")
async def dropbox_callback(state: str = "", code: str = "", error: str = "", error_description: str = ""):
    data = crypto.decrypt(state, ttl=900) if state else None
    if not data or not config.users.get(data.get("uid", "")):
        return _back(None, error="Anmeldung abgelaufen – bitte erneut versuchen")
    uid = data["uid"]
    if error:
        return _back(uid, error=error_description or error)
    try:
        creds = await dropbox.exchange_code(code)
        label = await dropbox.account_label(await dropbox.access_token(creds["refresh_token"]))
    except ProviderError as e:
        return _back(uid, error=str(e))
    db.save(uid, "dropbox", creds, label)
    log.info("User %s mit Dropbox %s verbunden", uid, label)
    return _back(uid, connected="dropbox")


# ---------- ownCloud (ADR 0005) ----------

class OwncloudIn(BaseModel):
    url: str
    user: str
    password: str


@app.post("/api/users/{uid}/owncloud")
async def owncloud_connect(uid: str, body: OwncloudIn):
    _user(uid)
    creds = {"url": normalize_url(body.url), "user": body.user.strip(), "password": body.password.strip()}
    if not creds["user"] or not creds["password"]:
        raise HTTPException(400, "Benutzername und App-Passwort angeben")
    await OwncloudProvider(creds).test()
    host = creds["url"].split("://", 1)[1]
    db.save(uid, "owncloud", creds, f"{creds['user']}@{host}")
    log.info("User %s mit ownCloud %s verbunden", uid, host)
    return storage_status(uid)


# ---------- Ordner ----------

@app.get("/api/users/{uid}/folders")
async def folders(uid: str, path: str = "/"):
    st = _storage(uid)
    path = naming.join(path)
    return {"path": path, "folders": await _provider(st).list_folders(path)}


class FolderIn(BaseModel):
    path: str
    name: str


@app.post("/api/users/{uid}/folders")
async def folder_create(uid: str, body: FolderIn):
    st = _storage(uid)
    name = naming.clean_title(body.name)
    if not name:
        raise HTTPException(400, "Ungültiger Ordnername")
    path = naming.join(body.path, name)
    await _provider(st).create_folder(path)
    return {"path": path}


class BasePathIn(BaseModel):
    path: str


@app.put("/api/users/{uid}/base_path")
def base_path(uid: str, body: BasePathIn):
    _storage(uid)
    db.set_base_path(uid, naming.join(body.path))
    return storage_status(uid)


# ---------- Upload (ADR 0007/0008) ----------

@app.post("/api/users/{uid}/uploads")
async def upload(uid: str, title: str = Form(...), files: list[UploadFile] = File(...),
                 start_index: int = Form(1)):
    st = _storage(uid)
    if not st.base_path:
        raise HTTPException(409, "Kein Arbeitsverzeichnis gewählt")
    clean = naming.clean_title(title)
    if not clean:
        raise HTTPException(400, "Bitte einen Titel angeben")
    prov = _provider(st)
    folder = naming.join(st.base_path, clean)
    await prov.ensure_folder(folder)
    ts = datetime.now(TZ)
    results = []
    for i, f in enumerate(files):
        data = await f.read(config.MAX_FILE_BYTES + 1)
        name = naming.file_name(ts, start_index + i, f.filename)
        if len(data) > config.MAX_FILE_BYTES:
            results.append({"client": f.filename, "ok": False, "error": "Datei zu groß"})
            continue
        try:
            path = await prov.upload(naming.join(folder, name), data)
            results.append({"client": f.filename, "ok": True, "path": path})
        except AuthError:
            raise
        except ProviderError as e:
            results.append({"client": f.filename, "ok": False, "error": str(e)})
    ok = sum(r["ok"] for r in results)
    log.info("User %s: %d/%d Fotos nach %s", uid, ok, len(results), folder)
    return {"folder": folder, "results": results}


# ---------- Frontend ----------

if config.STATIC_DIR and Path(config.STATIC_DIR).is_dir():
    static = Path(config.STATIC_DIR)
    app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404)
        f = (static / full_path).resolve()
        if full_path and f.is_file() and static.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(static / "index.html", headers={"Cache-Control": "no-cache"})
