---
adr: 5
titel: "ownCloud-Anbindung per WebDAV und App-Passwort"
status: accepted
datum: 2026-11-22
tags:
  - adr
  - snapdrop
---
# 0005 – ownCloud-Anbindung per WebDAV und App-Passwort

## Kontext
Als zweiter Anbieter soll der eigene ownCloud-Server angebunden werden, möglichst ebenfalls mit Ordnerauswahl. OAuth2 gibt es bei ownCloud nur als serverseitig zu installierende und zu konfigurierende App.

## Entscheidung
- Der User gibt Server-URL, Benutzername und ein in ownCloud erzeugtes **App-Passwort** ein.
- Zugriff per WebDAV auf `<url>/remote.php/dav/files/<user>/`: `PROPFIND` mit Depth 1 zum Auflisten der Ordner, `MKCOL` zum Anlegen, `PUT` zum Hochladen. Pfade werden URL-kodiert.
- Beim Speichern wird die Verbindung mit einem `PROPFIND` auf die Wurzel getestet. Schlägt der Test fehl, wird nichts gespeichert.

## Verworfene Alternativen
- **ownCloud-OAuth2:** setzt die OAuth2-App und einen registrierten Client auf dem Server voraus, das ist für einen Server mit wenigen Nutzern zu viel Aufwand.
- **Direkt ins Dateisystem des ownCloud-Servers schreiben:** umgeht ownCloud, Dateien fehlen ohne `occ files:scan` im Index, dazu Rechteprobleme.
- **Login-Passwort statt App-Passwort:** funktioniert nicht bei aktivierter 2FA und lässt sich nicht einzeln widerrufen.

## Konsequenzen
- Das App-Passwort liegt verschlüsselt in der DB (ADR 0006) und lässt sich in ownCloud jederzeit widerrufen.
- Ein Nextcloud-Server funktioniert über denselben Pfad ebenfalls.
- Existiert eine Datei schon, hängt der Provider selbst ein Suffix an (WebDAV-`PUT` würde sie sonst überschreiben).
