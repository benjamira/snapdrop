---
adr: 6
titel: "Speicherung der Zugangsdaten"
status: accepted
datum: 2026-11-22
tags:
  - adr
  - snapdrop
---
# 0006 – Speicherung der Zugangsdaten

## Kontext
Pro User müssen ein Dropbox-Refresh-Token oder ein ownCloud-App-Passwort dauerhaft gespeichert werden. Dazu kommen das Dropbox-App-Secret und ein Schlüssel zum Signieren des OAuth-`state`.

## Entscheidung
- Tabelle `storage(user_id PK, provider, credentials_enc, base_path, account_label, updated_at)` in SQLite, `credentials_enc` ist Fernet-verschlüsselt.
- `SECRET_KEY` (Fernet-Schlüssel), `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET` und `PUBLIC_URL` stehen in einer env-Datei auf dem Host, die per Bind-Mount eingebunden wird (`SNAPDROP_ENV_FILE`), nicht im Repo.
- Die API gibt Secrets nie heraus, nur Provider, Kontoname und Basisordner.

## Verworfene Alternativen
- **Klartext in SQLite:** Ein Backup oder eine Kopie der DB würde sonst die Cloud-Zugänge preisgeben.
- **Secrets im Compose-Repo:** Das Repo ist zwar privat, Secrets gehören trotzdem nicht in Git.

## Konsequenzen
- Geht `SECRET_KEY` verloren oder wird er gewechselt, lassen sich die Zugangsdaten nicht mehr entschlüsseln. Die App behandelt den User dann als nicht verbunden, und er verbindet seinen Speicher neu.
- DB und env-Datei gehören in dasselbe Backup.
