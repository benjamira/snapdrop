import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

import crypto
import db
import main

client = TestClient(main.app)
DAV = "https://cloud.test/remote.php/dav/files/anna"


def propfind(*entries):
    parts = []
    for href, folder in entries:
        rt = "<d:collection/>" if folder else ""
        parts.append(f"<d:response><d:href>{href}</d:href><d:propstat><d:prop><d:resourcetype>{rt}"
                     f"</d:resourcetype></d:prop></d:propstat></d:response>")
    return '<?xml version="1.0"?><d:multistatus xmlns:d="DAV:">' + "".join(parts) + "</d:multistatus>"


@pytest.fixture(autouse=True)
def clean():
    db.delete("anna")
    db.delete("bob")
    from providers import dropbox
    dropbox._token_cache.clear()


def test_users_and_status():
    assert client.get("/api/users").json() == [{"id": "anna", "name": "Anna"}, {"id": "bob", "name": "Bob"}]
    assert client.get("/api/users/anna/storage").json() == {"connected": False}
    assert client.get("/api/users/nobody/storage").status_code == 404


@respx.mock
def test_owncloud_flow():
    root = "/remote.php/dav/files/anna/"
    respx.route(method="PROPFIND", url=DAV + "/").mock(side_effect=lambda req: httpx.Response(207, text=propfind(
        (root, True), (root + "Fotos/", True), (root + "Doku%20Haus/", True), (root + "a.txt", False))))
    r = client.post("/api/users/anna/owncloud",
                    json={"url": "cloud.test/remote.php/webdav/", "user": "anna", "password": "pw"})
    assert r.status_code == 200, r.text
    assert r.json()["account"] == "anna@cloud.test"
    assert db.get("anna").credentials["url"] == "https://cloud.test"
    assert client.get("/api/users/anna/folders?path=/").json() == {"path": "/", "folders": ["Doku Haus", "Fotos"]}
    # Secrets kommen nicht über die API
    assert "pw" not in client.get("/api/users/anna/storage").text

    client.put("/api/users/anna/base_path", json={"path": "/Fotos"})
    respx.route(method="MKCOL", url=DAV + "/Fotos/Garten/").mock(return_value=httpx.Response(201))
    respx.route(method="PROPFIND", url__startswith=DAV + "/Fotos/Garten/2").mock(return_value=httpx.Response(404))
    put = respx.route(method="PUT", url__startswith=DAV + "/Fotos/Garten/").mock(return_value=httpx.Response(201))
    r = client.post("/api/users/anna/uploads", data={"title": " Garten "},
                    files=[("files", ("a.jpg", b"1", "image/jpeg")), ("files", ("b.png", b"22", "image/png"))])
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["folder"] == "/Fotos/Garten"
    assert [x["ok"] for x in res["results"]] == [True, True]
    assert res["results"][1]["path"].endswith("_02.png")
    assert put.call_count == 2


@respx.mock
def test_owncloud_wrong_password():
    respx.route(method="PROPFIND", url=DAV + "/").mock(return_value=httpx.Response(401))
    r = client.post("/api/users/anna/owncloud", json={"url": "https://cloud.test", "user": "anna", "password": "x"})
    assert r.status_code == 401
    assert db.get("anna") is None


@respx.mock
def test_dropbox_flow():
    r = client.get("/api/users/bob/dropbox/start", follow_redirects=False)
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert q["token_access_type"] == ["offline"]
    assert q["redirect_uri"] == ["https://snap.test/api/dropbox/callback"]
    state = q["state"][0]

    respx.post("https://api.dropboxapi.com/oauth2/token").mock(side_effect=lambda req: httpx.Response(200, json=(
        {"refresh_token": "R", "access_token": "A0", "account_id": "x"} if b"authorization_code" in req.content
        else {"access_token": "A1", "expires_in": 14400})))
    respx.post("https://api.dropboxapi.com/2/users/get_current_account").mock(
        return_value=httpx.Response(200, json={"email": "bob@example.org"}))
    r = client.get(f"/api/dropbox/callback?state={state}&code=C", follow_redirects=False)
    assert r.headers["location"] == "/?user=bob&connected=dropbox"
    assert db.get("bob").credentials == {"refresh_token": "R", "account_id": "x"}

    respx.post("https://api.dropboxapi.com/2/files/list_folder").mock(return_value=httpx.Response(200, json={
        "entries": [{".tag": "folder", "name": "b"}, {".tag": "file", "name": "f"}], "has_more": True, "cursor": "c"}))
    respx.post("https://api.dropboxapi.com/2/files/list_folder/continue").mock(return_value=httpx.Response(
        200, json={"entries": [{".tag": "folder", "name": "A"}], "has_more": False}))
    assert client.get("/api/users/bob/folders").json()["folders"] == ["A", "b"]

    client.put("/api/users/bob/base_path", json={"path": "/A"})
    respx.post("https://api.dropboxapi.com/2/files/create_folder_v2").mock(return_value=httpx.Response(
        409, json={"error_summary": "path/conflict/folder/.."}))
    up = respx.post("https://content.dropboxapi.com/2/files/upload").mock(side_effect=lambda req: httpx.Response(
        200, json={"path_display": json.loads(req.headers["Dropbox-API-Arg"])["path"]}))
    r = client.post("/api/users/bob/uploads", data={"title": "Zähler"},
                    files=[("files", ("x.jpg", b"1", "image/jpeg"))])
    assert r.status_code == 200, r.text
    assert r.json()["results"][0]["path"].startswith("/A/Zähler/")
    assert up.calls[0].request.headers["Authorization"] == "Bearer A1"


def test_dropbox_bad_state():
    r = client.get("/api/dropbox/callback?state=garbage&code=C", follow_redirects=False)
    assert "error=" in r.headers["location"]


@respx.mock
def test_dropbox_revoked_token():
    db.save("bob", "dropbox", {"refresh_token": "R"}, "bob")
    respx.post("https://api.dropboxapi.com/oauth2/token").mock(return_value=httpx.Response(400, json={}))
    r = client.get("/api/users/bob/folders")
    assert r.status_code == 401 and r.json()["reconnect"] is True


def test_upload_requires_base_path_and_title():
    db.save("anna", "owncloud", {"url": "https://cloud.test", "user": "anna", "password": "p"}, "a")
    r = client.post("/api/users/anna/uploads", data={"title": "x"}, files=[("files", ("a.jpg", b"1"))])
    assert r.status_code == 409
    db.set_base_path("anna", "/")
    r = client.post("/api/users/anna/uploads", data={"title": "??"}, files=[("files", ("a.jpg", b"1"))])
    assert r.status_code == 400


def test_broken_key():
    db.save("anna", "owncloud", {"x": 1}, "a")
    with db._conn() as con:
        con.execute("UPDATE storage SET credentials_enc='zzz' WHERE user_id='anna'")
    assert client.get("/api/users/anna/storage").json() == {"connected": False, "broken": True}
