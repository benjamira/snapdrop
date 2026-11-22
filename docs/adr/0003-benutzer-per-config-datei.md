---
adr: 3
titel: "Benutzerverwaltung per Config-Datei"
status: accepted
datum: 2026-11-22
tags:
  - adr
  - snapdrop
---
# 0003 – Benutzerverwaltung per Config-Datei

## Kontext
Die User legt ein Admin an, entweder über eine Admin-Oberfläche oder per Datei. Es geht um wenige, selten wechselnde Personen.

## Entscheidung
- User stehen in `users.yaml` (`users: [{id: anna, name: Anna}, …]`) im Config-Ordner auf dem Host. Gemountet wird der Ordner (read-only nach `/config`), nicht die Datei: Ein Single-File-Bind-Mount hängt an der Inode und sieht Dateien nicht, die ein Editor neu schreibt.
- Das Backend prüft bei jeder Anfrage die mtime der Datei und lädt sie bei Änderung neu, ein Neustart ist nicht nötig.
- `id` ist der stabile Schlüssel für die Speicherverbindung, `name` der angezeigte Name.

## Verworfene Alternativen
- **Admin-UI mit Passwort:** mehr Code und eine Angriffsfläche für eine Aufgabe, die selten vorkommt.
- **User nur in der Datenbank:** nicht versionierbar und ohne UI schlecht zu pflegen.

## Konsequenzen
- Einen User anlegen heißt, die Datei auf dem Server zu bearbeiten.
- Wird ein User entfernt, bleibt seine Speicherverbindung in der DB liegen. Taucht dieselbe `id` wieder auf, ist er sofort wieder verbunden. Löschen geht über „Speicher trennen“ vor dem Entfernen oder direkt in der DB.
- Eine ungültige YAML-Datei lässt den letzten gültigen Stand aktiv und wird geloggt.
