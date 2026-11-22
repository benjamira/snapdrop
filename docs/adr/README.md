---
titel: "ADR-Index: snapdrop"
tags:
  - adr
  - snapdrop
  - index
---
# Architekturentscheidungen: snapdrop

snapdrop ist eine selbst gehostete Webapp: User wählen, einmalig Dropbox oder ownCloud verbinden und ein Arbeitsverzeichnis wählen, dann unter einem Titel Fotos aufnehmen und mit „Abschließen“ nach `<Arbeitsverzeichnis>/<Titel>/` hochladen. Jede ADR hat Status, Datum, Kontext, Entscheidung, verworfene Alternativen und Konsequenzen.

| Nr. | Titel | Status |
|---|---|---|
| [0001](0001-architektur-ein-container.md) | Architektur: ein Container mit FastAPI und React/Vite | accepted |
| [0002](0002-zugriff-ohne-auth-intern.md) | Zugriff ohne Authentifizierung, nur aus dem Heimnetz | accepted |
| [0003](0003-benutzer-per-config-datei.md) | Benutzerverwaltung per Config-Datei | accepted |
| [0004](0004-dropbox-oauth.md) | Dropbox-Anbindung per OAuth2-Code-Flow mit Refresh-Token | accepted |
| [0005](0005-owncloud-webdav.md) | ownCloud-Anbindung per WebDAV und App-Passwort | accepted |
| [0006](0006-speicherung-zugangsdaten.md) | Speicherung der Zugangsdaten | accepted |
| [0007](0007-fotoaufnahme-input-capture.md) | Fotoaufnahme über natives Datei-Input statt getUserMedia | accepted |
| [0008](0008-ablagestruktur.md) | Ablagestruktur und Dateibenennung | accepted |
| [0009](0009-build-deploy.md) | Build per GitHub Actions, Deployment per Docker Compose | accepted |
