import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, Storage, User } from "./api";
import { shrink } from "./resize";

const LS_USER = "snapdrop.user";
const LS_SHRINK = "snapdrop.shrink";

function lsGet(k: string) {
  try { return localStorage.getItem(k); } catch { return null; }
}
function lsSet(k: string, v: string | null) {
  try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* egal */ }
}

export default function App() {
  const params = new URLSearchParams(location.search);
  const [users, setUsers] = useState<User[] | null>(null);
  const [userId, setUserId] = useState<string | null>(params.get("user") || lsGet(LS_USER));
  const [storage, setStorage] = useState<Storage | null>(null);
  const [pickFolder, setPickFolder] = useState(false);
  const [error, setError] = useState<string | null>(params.get("error"));
  const [menu, setMenu] = useState(false);

  useEffect(() => {
    if (location.search) history.replaceState(null, "", "/");
    api.users().then(setUsers).catch((e) => setError(e.message));
  }, []);

  const user = users?.find((u) => u.id === userId) ?? null;

  const loadStorage = useCallback(() => {
    if (!user) return;
    setStorage(null);
    api.storage(user.id).then(setStorage).catch((e) => setError(e.message));
  }, [user?.id]);

  useEffect(() => {
    if (users && userId && !user) { setUserId(null); lsSet(LS_USER, null); }
    loadStorage();
  }, [users, user?.id]);

  const choose = (u: User | null) => {
    setUserId(u?.id ?? null);
    setError(null);
    lsSet(LS_USER, u?.id ?? null);
    setStorage(null);
    setPickFolder(false);
    setMenu(false);
  };

  const handleErr = (e: unknown) => {
    const err = e as ApiError;
    setError(err.message);
    if (err.reconnect) loadStorage();
  };

  let body: JSX.Element;
  if (!users) body = <Spinner />;
  else if (!user) body = <UserPicker users={users} onPick={choose} />;
  else if (!storage) body = <Spinner />;
  else if (!storage.connected) body = <Connect user={user} broken={!!storage.broken} onDone={(st) => { setError(null); setStorage(st); }} onError={setError} />;
  else if (!storage.base_path || pickFolder)
    body = (
      <FolderPicker
        user={user}
        start={storage.base_path || "/"}
        canCancel={!!storage.base_path}
        onCancel={() => setPickFolder(false)}
        onPick={async (p) => {
          try { setStorage(await api.setBase(user.id, p)); setPickFolder(false); setError(null); } catch (e) { handleErr(e); }
        }}
        onError={handleErr}
      />
    );
  else body = <Capture user={user} storage={storage} onError={handleErr} onSuccess={() => setError(null)} />;

  return (
    <div className="app">
      <header>
        <span className="logo" onClick={() => choose(null)}>
          <img src="/icon.svg" alt="" /> snapdrop
        </span>
        {user && (
          <button className="chip" onClick={() => setMenu(!menu)} aria-expanded={menu}>
            {user.name} ▾
          </button>
        )}
      </header>
      {menu && user && (
        <div className="menu" onClick={() => setMenu(false)}>
          {storage?.connected && (
            <div className="menu-info">
              {storage.provider === "dropbox" ? "Dropbox" : "ownCloud"} · {storage.account}
              {storage.base_path && <div className="path">{storage.base_path}</div>}
            </div>
          )}
          {storage?.connected && <button onClick={() => setPickFolder(true)}>Arbeitsverzeichnis ändern</button>}
          {storage?.connected && (
            <button
              onClick={async () => {
                if (!confirm("Cloudspeicher-Verbindung wirklich trennen?")) return;
                await api.disconnect(user.id).catch(handleErr);
                loadStorage();
              }}
            >
              Cloudspeicher trennen
            </button>
          )}
          <button onClick={() => choose(null)}>Anderer User</button>
        </div>
      )}
      {error && (
        <div className="banner error" onClick={() => setError(null)}>
          {error} <span className="x">✕</span>
        </div>
      )}
      <main>{body}</main>
    </div>
  );
}

function Spinner() {
  return <div className="spinner" aria-label="Lädt" />;
}

function UserPicker({ users, onPick }: { users: User[]; onPick: (u: User) => void }) {
  if (!users.length)
    return <p className="hint">Noch keine User angelegt. Trage sie in <code>users.yaml</code> ein.</p>;
  return (
    <>
      <h1>Wer bist du?</h1>
      <div className="tiles">
        {users.map((u) => (
          <button key={u.id} className="tile" onClick={() => onPick(u)}>
            <span className="avatar">{u.name.slice(0, 1).toUpperCase()}</span>
            {u.name}
          </button>
        ))}
      </div>
    </>
  );
}

function Connect({ user, broken, onDone, onError }: {
  user: User; broken: boolean; onDone: (s: Storage) => void; onError: (m: string) => void;
}) {
  const [prov, setProv] = useState<{ dropbox: boolean } | null>(null);
  const [oc, setOc] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ url: "", user: "", password: "" });
  useEffect(() => { api.providers().then(setProv).catch(() => setProv({ dropbox: false })); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try { onDone(await api.owncloud(user.id, form.url, form.user, form.password)); }
    catch (err) { onError((err as Error).message); }
    finally { setBusy(false); }
  };

  return (
    <>
      <h1>Cloudspeicher verbinden</h1>
      <p className="hint">
        {broken ? "Die gespeicherte Verbindung ist nicht mehr gültig. " : ""}
        Wohin sollen deine Fotos, {user.name}?
      </p>
      {!oc ? (
        <div className="stack">
          <a
            className={`btn big ${prov?.dropbox ? "" : "disabled"}`}
            href={prov?.dropbox ? api.dropboxStart(user.id) : undefined}
            aria-disabled={!prov?.dropbox}
          >
            Dropbox
            <small>{prov && !prov.dropbox ? "auf dem Server nicht eingerichtet" : "Anmeldung bei Dropbox"}</small>
          </a>
          <button className="btn big" onClick={() => setOc(true)}>
            ownCloud<small>Server-URL und App-Passwort</small>
          </button>
        </div>
      ) : (
        <form className="stack" onSubmit={submit}>
          <label>Server-URL
            <input required inputMode="url" autoCapitalize="off" placeholder="https://cloud.example.org"
              value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
          </label>
          <label>Benutzername
            <input required autoCapitalize="off" autoComplete="username"
              value={form.user} onChange={(e) => setForm({ ...form, user: e.target.value })} />
          </label>
          <label>App-Passwort
            <input required type="password" autoComplete="current-password"
              value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            <small>In ownCloud unter Einstellungen → Sicherheit → „App-Passwörter“ erzeugen.</small>
          </label>
          <div className="row">
            <button type="button" className="btn ghost" onClick={() => setOc(false)}>Zurück</button>
            <button className="btn primary" disabled={busy}>{busy ? "Prüfe …" : "Verbinden"}</button>
          </div>
        </form>
      )}
    </>
  );
}

function FolderPicker({ user, start, canCancel, onCancel, onPick, onError }: {
  user: User; start: string; canCancel: boolean; onCancel: () => void;
  onPick: (p: string) => void; onError: (e: unknown) => void;
}) {
  const [path, setPath] = useState(start);
  const [folders, setFolders] = useState<string[] | null>(null);
  const [newName, setNewName] = useState<string | null>(null);

  const load = useCallback((p: string) => {
    setFolders(null);
    api.folders(user.id, p)
      .then((r) => { setPath(r.path); setFolders(r.folders); })
      .catch((e) => {
        onError(e);
        if (p !== "/") load("/");
        else setFolders([]);
      });
  }, [user.id]);
  useEffect(() => load(start), []);

  const segs = path.split("/").filter(Boolean);
  const to = (i: number) => "/" + segs.slice(0, i).join("/");

  const mkdir = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName?.trim()) return;
    try { const r = await api.mkdir(user.id, path, newName); setNewName(null); load(r.path); }
    catch (err) { onError(err); }
  };

  return (
    <>
      <h1>Arbeitsverzeichnis wählen</h1>
      <nav className="crumbs">
        <button onClick={() => load("/")}>Start</button>
        {segs.map((s, i) => (
          <span key={i}>
            <span className="sep">/</span>
            <button onClick={() => load(to(i + 1))}>{s}</button>
          </span>
        ))}
      </nav>
      <ul className="folders">
        {folders === null && <li><Spinner /></li>}
        {path !== "/" && folders && (
          <li><button onClick={() => load(to(segs.length - 1))}>↰ ..</button></li>
        )}
        {folders?.map((f) => (
          <li key={f}><button onClick={() => load(path.replace(/\/$/, "") + "/" + f)}>📁 {f}</button></li>
        ))}
        {folders?.length === 0 && <li className="empty">Keine Unterordner</li>}
      </ul>
      {newName !== null ? (
        <form className="row" onSubmit={mkdir}>
          <input autoFocus placeholder="Neuer Ordner" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <button className="btn">Anlegen</button>
          <button type="button" className="btn ghost" onClick={() => setNewName(null)}>✕</button>
        </form>
      ) : (
        <button className="btn ghost" onClick={() => setNewName("")}>+ Neuer Ordner</button>
      )}
      <div className="footer-bar">
        {canCancel && <button className="btn ghost" onClick={onCancel}>Abbrechen</button>}
        <button className="btn primary" onClick={() => onPick(path)} disabled={folders === null}>
          „{segs.at(-1) ?? "Start"}“ verwenden
        </button>
      </div>
    </>
  );
}

// Vorschau wie naming.clean_title im Backend (ADR 0008)
const cleanTitle = (t: string) =>
  t.replace(/\s/g, " ").replace(/[\x00-\x1f\x7f]/g, "").replace(/[/\\:*?"<>|]/g, " ")
    .replace(/ +/g, " ").trim().slice(0, 100).replace(/[. ]+$/, "");

type Photo = { id: number; file: File; url: string; failed?: string };
let photoSeq = 0;

function Capture({ user, storage, onError, onSuccess }: {
  user: User; storage: Extract<Storage, { connected: true }>; onError: (e: unknown) => void; onSuccess: () => void;
}) {
  const [title, setTitle] = useState("");
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [done, setDone] = useState<{ folder: string; count: number } | null>(null);
  const [small, setSmall] = useState(lsGet(LS_SHRINK) === "1");
  const nextIndex = useRef(1);
  const camRef = useRef<HTMLInputElement>(null);
  const galRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => { if (photos.length) { e.preventDefault(); e.returnValue = ""; } };
    addEventListener("beforeunload", warn);
    return () => removeEventListener("beforeunload", warn);
  }, [photos.length]);

  const add = (list: FileList | null) => {
    if (!list) return;
    const fresh = Array.from(list).map((file) => ({ id: ++photoSeq, file, url: URL.createObjectURL(file) }));
    setPhotos((p) => [...p, ...fresh]);
    setDone(null);
  };
  const remove = (id: number) =>
    setPhotos((p) => p.filter((x) => (x.id === id ? (URL.revokeObjectURL(x.url), false) : true)));

  const finish = async () => {
    setProgress(0);
    try {
      const files = small ? await Promise.all(photos.map((p) => shrink(p.file))) : photos.map((p) => p.file);
      const start = nextIndex.current;
      nextIndex.current += files.length;
      const res = await api.upload(user.id, title, files, start, setProgress);
      const failed = new Map<number, string>();
      res.results.forEach((r, i) => !r.ok && failed.set(photos[i].id, r.error || "Fehler"));
      photos.forEach((p) => !failed.has(p.id) && URL.revokeObjectURL(p.url));
      const okCount = res.results.length - failed.size;
      if (failed.size) {
        setPhotos(photos.filter((p) => failed.has(p.id)).map((p) => ({ ...p, failed: failed.get(p.id) })));
        onError(new ApiError(`${failed.size} von ${res.results.length} Fotos fehlgeschlagen – erneut senden`, 502));
      } else {
        setPhotos([]);
        onSuccess();
        setDone({ folder: res.folder, count: okCount });
        setTitle("");
        nextIndex.current = 1;
      }
    } catch (e) {
      onError(e);
    } finally {
      setProgress(null);
    }
  };

  if (done)
    return (
      <div className="done">
        <div className="check">✓</div>
        <h1>{done.count} {done.count === 1 ? "Foto" : "Fotos"} hochgeladen</h1>
        <p className="path">{done.folder}</p>
        <button className="btn primary big" onClick={() => setDone(null)}>Neuer Titel</button>
      </div>
    );

  const busy = progress !== null;
  return (
    <>
      <label className="title-field">
        Titel
        <input
          value={title}
          maxLength={100}
          placeholder="z. B. Zählerstand November"
          onChange={(e) => setTitle(e.target.value)}
          disabled={busy}
        />
        <small className="path">→ {storage.base_path?.replace(/\/$/, "")}/{cleanTitle(title) || "…"}</small>
      </label>

      <input ref={camRef} type="file" accept="image/*" capture="environment" hidden
        onChange={(e) => { add(e.target.files); e.target.value = ""; }} />
      <input ref={galRef} type="file" accept="image/*" multiple hidden
        onChange={(e) => { add(e.target.files); e.target.value = ""; }} />

      <div className="row">
        <button className="btn primary big grow" onClick={() => camRef.current?.click()} disabled={busy}>
          📷 Foto aufnehmen
        </button>
        <button className="btn big" onClick={() => galRef.current?.click()} disabled={busy} title="Aus Galerie">
          🖼
        </button>
      </div>

      {photos.length > 0 && (
        <ul className="grid">
          {photos.map((p) => (
            <li key={p.id} className={p.failed ? "failed" : ""}>
              <img src={p.url} alt="" />
              {!busy && <button className="del" onClick={() => remove(p.id)} aria-label="Entfernen">✕</button>}
              {p.failed && <span className="err">{p.failed}</span>}
            </li>
          ))}
        </ul>
      )}

      <label className="toggle">
        <input type="checkbox" checked={small}
          onChange={(e) => { setSmall(e.target.checked); lsSet(LS_SHRINK, e.target.checked ? "1" : "0"); }} />
        Fotos verkleinern (max. 3000 px)
      </label>

      <div className="footer-bar">
        {busy ? (
          <div className="progress"><div style={{ width: `${Math.round((progress ?? 0) * 100)}%` }} />
            <span>{progress! < 1 ? `Lade hoch … ${Math.round(progress! * 100)} %` : "Speichere in der Cloud …"}</span>
          </div>
        ) : (
          <button className="btn primary big grow" disabled={!cleanTitle(title) || !photos.length} onClick={finish}>
            Abschließen{photos.length ? ` (${photos.length})` : ""}
          </button>
        )}
      </div>
    </>
  );
}
