---
adr: 2
titel: "Zugriff ohne Authentifizierung, nur aus dem Heimnetz"
status: accepted
datum: 2026-11-22
tags:
  - adr
  - snapdrop
---
# 0002 – Zugriff ohne Authentifizierung, nur aus dem Heimnetz

## Kontext
Die App soll ohne Anmeldung nutzbar sein: aufrufen, User wählen, fotografieren. Sie bekommt aber Schreibzugriff auf die Cloudspeicher der User.

## Entscheidung
- Keine Anmeldung in der App.
- Erreichbar nur über einen internen Hostnamen hinter dem Reverse-Proxy (Traefik mit TLS), also im LAN oder per VPN. Keine Portfreigabe ins Internet, kein öffentlich auflösbarer Hostname.

## Verworfene Alternativen
- **Internetzugang ohne Auth:** Dann könnte jeder in die verbundenen Clouds hochladen und deren Ordnerstruktur sehen.
- **PIN oder Passwort pro User:** Solange die App nur intern läuft, nicht nötig.

## Konsequenzen
- Wer im Heimnetz ist, kann jeden User auswählen, in dessen Ordnerbaum stöbern und dorthin hochladen. Das ist für den Haushalt in Ordnung.
- Wird die App später nach außen freigegeben, braucht es vorher eine neue ADR mit Authentifizierung.
