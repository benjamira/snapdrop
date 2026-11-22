---
adr: 4
titel: "Dropbox-Anbindung per OAuth2-Code-Flow mit Refresh-Token"
status: accepted
datum: 2026-11-22
tags:
  - adr
  - snapdrop
---
# 0004 – Dropbox-Anbindung per OAuth2-Code-Flow mit Refresh-Token

## Kontext
Wählt ein User Dropbox, soll er sich bei Dropbox anmelden und danach einen beliebigen Ordner als Arbeitsverzeichnis wählen. Uploads müssen dauerhaft funktionieren, ohne dass er sich neu anmeldet.

## Entscheidung
- Eigene Dropbox-App (App Console) mit Zugriff **Full Dropbox** und den Scopes `files.metadata.read`, `files.content.read`, `files.content.write` sowie `account_info.read` (Kontoname in der Anzeige).
- Code-Flow mit `token_access_type=offline` und einem signierten `state` (enthält User-ID und Nonce, verhindert CSRF). Callback ist `<PUBLIC_URL>/api/dropbox/callback`, für lokale Tests zusätzlich `http://localhost:8000/api/dropbox/callback`.
- Der Refresh-Token wird gespeichert (siehe ADR 0006), Access-Tokens werden bei Bedarf erneuert und nur im Speicher gehalten.
- API-Aufrufe direkt per HTTP: `files/list_folder` (+`continue`), `files/create_folder_v2`, `files/upload` (`mode: add`, `autorename: true`).

## Verworfene Alternativen
- **Zugriffstyp „App folder“:** Dann könnten nur Ordner unter `Apps/<App>/` gewählt werden, nicht frei im Dropbox.
- **Offizielles Dropbox-SDK:** groß und für vier Endpunkte unnötig.
- **Implicit Flow im Browser:** keine Refresh-Tokens, Token im Client.

## Konsequenzen
- Es gibt eine einzige App, die der Betreiber in seinem Account anlegt. Jeder User verbindet sein eigenes Dropbox-Konto über OAuth, eine eigene App pro User ist nicht nötig.
- Die App bleibt im Development-Status, eine Freigabe durch Dropbox ist nicht nötig. Damit sich außer dem App-Besitzer weitere Konten verbinden können (bis zu 500), muss in der App Console einmal „Enable additional users“ geklickt werden.
- Der Redirect geht an einen internen Hostnamen. Das klappt, weil der Browser weiterleitet, aber nur aus dem Heimnetz (passt zu ADR 0002).
- `files/upload` erlaubt bis 150 MB pro Datei, für Fotos reicht das.
