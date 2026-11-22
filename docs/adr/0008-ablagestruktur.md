---
adr: 8
titel: "Ablagestruktur und Dateibenennung"
status: accepted
datum: 2026-11-22
tags:
  - adr
  - snapdrop
---
# 0008 – Ablagestruktur und Dateibenennung

## Kontext
Die Fotos eines Titels sollen in einem neuen Verzeichnis mit dem Namen des Titels unter dem gewählten Arbeitsverzeichnis landen.

## Entscheidung
- Ziel ist `<Arbeitsverzeichnis>/<Titel>/`. Aus dem Titel werden Steuerzeichen entfernt und `/ \ : * ? " < > |` durch Leerzeichen ersetzt (mehrfache Leerzeichen zusammengefasst), Leerzeichen am Rand und Punkte am Ende abgeschnitten, die Länge auf 100 Zeichen begrenzt. Ein leerer Titel wird abgelehnt.
- Existiert der Ordner schon, wird er weiterverwendet.
- Dateinamen haben die Form `YYYYMMDD-HHMMSS_NN.<ext>` (Zeitpunkt von „Abschließen“, laufende Nummer, Endung aus dem Original, sonst `jpg`). Bei Namenskonflikten nummeriert der Provider automatisch weiter.

## Verworfene Alternativen
- **Ordnernamen mit Zeitstempel-Suffix:** eindeutig, aber unübersichtlich, und das Ergänzen eines Titels wäre nicht möglich.
- **Abbruch bei vorhandenem Ordner:** frustrierend, wenn man Fotos zu einem Titel nachreichen will.
- **Originale Dateinamen (`IMG_1234.jpg`):** auf iOS oft nur `image.jpg`, also ständige Konflikte.

## Konsequenzen
- Ein erneuter Upload mit demselben Titel ergänzt den bestehenden Ordner.
