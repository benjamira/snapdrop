export type User = { id: string; name: string };
export type Storage =
  | { connected: false; broken?: boolean }
  | { connected: true; provider: "dropbox" | "owncloud"; account: string; base_path: string | null };
export type UploadResult = { client: string; ok: boolean; path?: string; error?: string };

export class ApiError extends Error {
  constructor(message: string, public status: number, public reconnect = false) {
    super(message);
  }
}

async function req<T>(method: string, url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(data.detail || `Fehler ${r.status}`, r.status, !!data.reconnect);
  return data as T;
}

const u = (id: string) => `/api/users/${encodeURIComponent(id)}`;

export const api = {
  users: () => req<User[]>("GET", "/api/users"),
  providers: () => req<{ dropbox: boolean; owncloud: boolean }>("GET", "/api/providers"),
  storage: (id: string) => req<Storage>("GET", `${u(id)}/storage`),
  disconnect: (id: string) => req("DELETE", `${u(id)}/storage`),
  dropboxStart: (id: string) => `${u(id)}/dropbox/start`,
  owncloud: (id: string, url: string, user: string, password: string) =>
    req<Storage>("POST", `${u(id)}/owncloud`, { url, user, password }),
  folders: (id: string, path: string) =>
    req<{ path: string; folders: string[] }>("GET", `${u(id)}/folders?path=${encodeURIComponent(path)}`),
  mkdir: (id: string, path: string, name: string) => req<{ path: string }>("POST", `${u(id)}/folders`, { path, name }),
  setBase: (id: string, path: string) => req<Storage>("PUT", `${u(id)}/base_path`, { path }),

  upload(id: string, title: string, files: File[], startIndex: number, onProgress: (f: number) => void) {
    return new Promise<{ folder: string; results: UploadResult[] }>((resolve, reject) => {
      const fd = new FormData();
      fd.append("title", title);
      fd.append("start_index", String(startIndex));
      files.forEach((f) => fd.append("files", f, f.name));
      const x = new XMLHttpRequest();
      x.open("POST", `${u(id)}/uploads`);
      x.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
      x.onerror = () => reject(new ApiError("Netzwerkfehler – bist du im Heimnetz?", 0));
      x.onload = () => {
        let data: any = {};
        try { data = JSON.parse(x.responseText); } catch { /* leer */ }
        if (x.status >= 200 && x.status < 300) resolve(data);
        else reject(new ApiError(data.detail || `Fehler ${x.status}`, x.status, !!data.reconnect));
      };
      x.send(fd);
    });
  },
};
