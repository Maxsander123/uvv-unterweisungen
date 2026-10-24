# Changelog

Alle relevanten Änderungen an UVV Unterweisungen. Neueste Version oben.
Diese Datei wird auch auf der Seite „Über“ (Link unten in der Fußzeile) angezeigt; die oberste Version ist die App-Version.
Jede neue Version oben in dieser Datei erzeugt beim Merge auf `main` automatisch einen Git-Tag, ein GitHub-Release und ein Docker-Image.

## 1.1 (2026-10-24)
- Fertiges Docker-Image in der GitHub Container Registry: `ghcr.io/siliconserver/uvv-unterweisungen` (amd64 und arm64)
- Automatische Tags und GitHub-Releases für jede neue Version in diesem Changelog
- Neue Seite „Über“ in der Fußzeile: Version, Links zu Quellcode, Issues, Releases und der Changelog
- `docker-compose.yml` nutzt das fertige Image, Version über `UVV_TAG` in der `.env` wählbar
- README als Anleitung für Betreiber neu geschrieben

## 1.0 (2026-10-22)
- Erste Version von UVV Unterweisungen (Weiterentwicklung der UVV-Drohne-App)
- Beliebig viele Unterweisungen mit eigenen Inhalten, Fragen, Bestehensgrenze, Gültigkeit und Mailempfängern
- Teilnahme ohne Konto: lesen, Wissenstest, Unterschrift, PDF-Nachweis mit QR-Code zur Online-Prüfung
- Verwaltung mit Benutzern (Admin, Verwalter), Zwei-Faktor-Anmeldung, Nachweisliste und CSV-Export
- Eigenes Erscheinungsbild: Name, Logo, Farbe, Texte, Links zu Impressum und Datenschutz
