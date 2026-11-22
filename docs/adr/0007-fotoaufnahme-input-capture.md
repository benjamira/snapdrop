---
adr: 7
titel: "Fotoaufnahme über natives Datei-Input statt getUserMedia"
status: accepted
datum: 2026-11-22
tags:
  - adr
  - snapdrop
---
# 0007 – Fotoaufnahme über natives Datei-Input statt getUserMedia

## Kontext
Unter einem Titel sollen ein oder mehrere Fotos aufgenommen und erst mit „Abschließen“ hochgeladen werden. Die App läuft vor allem auf Smartphones (iOS und Android).

## Entscheidung
- Aufnahme über `<input type="file" accept="image/*" capture="environment">`. Das öffnet die System-Kamera mit voller Auflösung, Autofokus und Blitz. Ein zweiter Button ohne `capture` erlaubt die Auswahl aus der Galerie (mehrere Dateien).
- Die Fotos bleiben bis „Abschließen“ im Browser (Object-URLs als Vorschau, löschbar).
- „Abschließen“ schickt einen Multipart-Request ans Backend, das in den Cloudspeicher hochlädt und das Ergebnis pro Datei meldet. Fortschritt per `XMLHttpRequest.upload.onprogress`.
- Optional, standardmäßig aus: Fotos im Browser auf maximal 3000 px Kantenlänge mit JPEG-Qualität 0,85 verkleinern.

## Verworfene Alternativen
- **Eigene Kamera-UI per getUserMedia:** aufwendig, auf iOS fehleranfällig, meist schlechtere Fotos als die System-Kamera.
- **Direkt-Upload vom Browser in die Cloud:** Dafür bräuchte der Browser Tokens, und ownCloud-WebDAV scheitert an CORS.
- **Jedes Foto sofort auf den Server laden:** Dann müssten unvollständige Titel serverseitig zwischengespeichert und aufgeräumt werden. Erst „Abschließen“ macht den Ablauf eindeutig.

## Konsequenzen
- Wird die Seite vor „Abschließen“ neu geladen oder geschlossen, sind die Fotos weg. Die App warnt vorher mit `beforeunload`.
- Das Backend nimmt höchstens 25 MB pro Foto an.
- Schlägt ein Teil der Uploads fehl, bleiben genau die fehlgeschlagenen Fotos stehen und können erneut gesendet werden.
