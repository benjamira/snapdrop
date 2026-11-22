---
adr: 9
titel: "Build per GitHub Actions, Deployment per Docker Compose mit fertigem Image"
status: accepted
datum: 2026-11-22
tags:
  - adr
  - snapdrop
---
# 0009 – Build per GitHub Actions, Deployment per Docker Compose mit fertigem Image

## Kontext
snapdrop läuft auf einem Heimserver mit Docker, Traefik als Reverse-Proxy und GitOps-Deployment: Ein Tool zieht Compose-Dateien aus einem Git-Repo und rollt sie aus. Dieses Tool kann selbst keine Images bauen.

## Entscheidung
- Der Workflow `.github/workflows/docker.yml` baut bei einem Tag `v*` (und per `workflow_dispatch`) das Image `ghcr.io/<owner>/snapdrop` für `linux/amd64`, getaggt mit der Version und `latest`. `.github/workflows/test.yml` führt bei jedem Push die Backend-Tests aus und baut das Frontend.
- Deployment per Docker Compose mit **fester Image-Version**, Zugriff über Traefik-Labels statt `ports:`. Daten, Config und Secrets kommen per Bind-Mount vom Host. Vorlage: `docker-compose.example.yaml`.
- Release: Tag pushen, auf den grünen Build warten, dann die Version in der Compose-Datei des Deployments anheben.

## Verworfene Alternativen
- **`build:` in der Compose-Datei:** Das GitOps-Tool kann nicht bauen, außerdem wären Builds auf dem Server nicht reproduzierbar.
- **`latest` im Deployment:** Wird nicht zuverlässig neu gezogen, Deploys wären nicht nachvollziehbar.

## Konsequenzen
- Ein Release besteht aus zwei Schritten: Tag im App-Repo, dann Versionssprung im Deployment-Repo.
- Wer snapdrop selbst betreibt, kann das veröffentlichte Image nutzen oder mit `docker build .` selbst bauen.
