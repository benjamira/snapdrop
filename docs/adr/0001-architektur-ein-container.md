---
adr: 1
titel: "Architektur: ein Container mit FastAPI-Backend und React/Vite-Frontend"
status: accepted
datum: 2026-11-22
tags:
  - adr
  - snapdrop
---
# 0001 – Architektur: ein Container mit FastAPI-Backend und React/Vite-Frontend

## Kontext
snapdrop braucht eine mobile Weboberfläche und eine Serverkomponente: Das Dropbox-Client-Secret und die Tokens der User dürfen nicht im Browser liegen, und die Uploads sollen über einen vertrauenswürdigen Punkt laufen. Ein einzelner Container, der FastAPI und ein gebautes React-Frontend ausliefert, hat sich bei anderen Heimserver-Apps schon bewährt.

## Entscheidung
- Ein Image: Mehrstufiger Build (node → python-slim), FastAPI liefert `/api/*` und das statische Frontend unter `/`.
- Persistenz in SQLite unter `/data/snapdrop.db`.
- Das Backend greift auf die Cloud-APIs über `httpx` zu, ohne Anbieter-SDKs.

## Verworfene Alternativen
- **Frontend und Backend in getrennten Containern:** mehr Compose- und Traefik-Aufwand ohne Nutzen bei einer Handvoll Nutzer.
- **Reine Client-App (SPA ohne Backend):** OAuth-Secret und Tokens lägen im Browser, und ownCloud-WebDAV scheitert im Browser oft an CORS.

## Konsequenzen
- Ein Image, ein Release-Tag, ein Healthcheck.
- Fotos laufen durch den Server (doppelter Transfer im LAN, unkritisch).
