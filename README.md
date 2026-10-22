# UVV Unterweisungen

Web-App für jährliche Pflichtunterweisungen (UVV) bei Feuerwehren und anderen Organisationen. Teilnehmer lesen die Inhalte am Handy oder PC, beantworten ein paar Fragen, unterschreiben mit dem Finger und bekommen einen PDF-Nachweis mit QR-Code. Die Verwaltung legt beliebig viele Unterweisungen mit eigenen Inhalten und Fragen an.

Entstanden bei der Freiwilligen Feuerwehr Wörth am Rhein. Frei verwendbar unter der [MIT-Lizenz](LICENSE).

## Funktionen

**Für Teilnehmer (ohne Konto, ohne Anmeldung)**
- Startseite mit allen freigeschalteten Unterweisungen
- Inhalte lesen, Namen eingeben, Fragen beantworten (Reihenfolge und Antworten werden gemischt)
- Nach dem Abgeben: falsche Antworten mit richtiger Lösung und Erklärung, auch beim Bestehen
- Unterschrift per Finger, Stift oder Maus
- PDF-Nachweis mit Unterschrift, Ort, Datum und QR-Code zur Online-Prüfung von Datum und Gültigkeit
- Knopf zum Versand des Nachweises per Mail an die Verantwortlichen

**Für die Verwaltung (`/login`)**
- Unterweisungen anlegen, bearbeiten, kopieren, freischalten: Inhalte, Fragen mit Erklärungen, Bestehensgrenze, Gültigkeitsdauer, Mailempfänger
- Nachweisliste je Unterweisung mit Gültigkeit, CSV-Export
- Benutzer mit den Rollen **Admin** (alles) und **Verwalter** (Unterweisungen und Nachweise)
- Zwei-Faktor-Anmeldung mit jeder Authenticator-App inkl. Wiederherstellungscodes
- Eigenes Erscheinungsbild: Name, Logo, Farbe, Texte, Links zu Impressum und Datenschutz

Eine Beispiel-Unterweisung „Sicherer Umgang mit Drohnen“ (BOS-Drohnen nach § 21k LuftVO, DGUV) ist enthalten und zunächst nicht freigeschaltet.

## Voraussetzungen

- Ein Linux-Server mit [Docker](https://docs.docker.com/engine/install/) und Docker Compose (Befehl `docker compose`)
- Eine Domain bzw. Subdomain, z. B. `uvv.feuerwehr-musterstadt.de`
- HTTPS über einen Reverse Proxy (z. B. Traefik, Caddy, nginx). Die App selbst spricht nur HTTP auf Port 8000. Ohne HTTPS funktioniert die Anmeldung zur Verwaltung nicht (siehe [Lokal ausprobieren](#lokal-ausprobieren)).
- Optional: ein Mailpostfach mit SMTP-Zugang für den Versand der Nachweise

## Installation

**1. Code holen**

```bash
git clone https://github.com/<benutzer>/uvv-unterweisungen.git /opt/uvv-unterweisungen
cd /opt/uvv-unterweisungen
```

**2. Konfiguration anlegen**

```bash
cp .env.example .env
nano .env
chmod 600 .env
```

Mindestens diese Werte eintragen:

| Variable | Beispiel | Bedeutung |
|---|---|---|
| `DOMAIN` | `uvv.feuerwehr-musterstadt.de` | Adresse ohne `https://`. Sie steht im QR-Code jedes Nachweises und sollte später nicht mehr geändert werden. |
| `ADMIN_PASSWORD` | ein langes eigenes Passwort | Passwort des ersten Admins (mindestens 10 Zeichen) |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | | Mailversand. Leer lassen, wenn keine Mails verschickt werden sollen. |

Alle weiteren Werte sind in der `.env.example` erklärt. Die `.env` enthält Passwörter und wird nicht ins Git eingecheckt.

**3. Starten**

```bash
docker compose up -d --build
docker compose logs -f        # Strg+C zum Beenden der Anzeige
```

`docker compose config` zeigt die Konfiguration mit allen eingesetzten Werten.

**4. HTTPS einrichten**

- *Traefik:* In der `docker-compose.yml` den Block `ports` entfernen und die auskommentierten `labels` und `networks` aktivieren (Name des Zertifikats-Resolvers ggf. anpassen).
- *Anderer Reverse Proxy:* Anfragen für die Domain an `http://<server>:8000` weiterleiten (Port über `HTTP_PORT` änderbar) und die Header `X-Forwarded-For`, `X-Forwarded-Proto` und `X-Forwarded-Host` mitschicken.

**5. Einrichten im Browser**

1. `https://<DOMAIN>/login` aufrufen (Link „Verwaltung“ unten rechts) und mit `ADMIN_USER` / `ADMIN_PASSWORD` anmelden
2. **Einstellungen:** Name der Organisation, Logo, Farbe, Ort für die Unterschrift, Links zu Impressum und Datenschutz
3. **Mein Konto:** Passwort ändern und Zwei-Faktor-Anmeldung einrichten
4. **Benutzer:** weitere Admins oder Verwalter anlegen
5. **Unterweisungen:** eigene anlegen oder die Beispiel-Unterweisung anpassen und freischalten

Danach den Link zur Startseite an die Teilnehmer schicken.

## Unterweisungen anlegen

- **Inhalte** werden als einfacher Text eingegeben: Jeder Abschnitt beginnt mit `## Überschrift`, darunter ein Punkt pro Zeile mit `- `.
- **Fragen** haben 2 bis 8 Antworten, genau eine ist richtig. Die Erklärung sieht nur, wer die Frage falsch beantwortet.
- **Bestehensgrenze** in Prozent, **Gültigkeit** in Monaten (12 = jährlich).
- **Mailempfänger:** eine oder mehrere Adressen. Ohne Empfänger wird der Mail-Knopf ausgeblendet.
- Nicht freigeschaltete Unterweisungen sind nur für angemeldete Benutzer sichtbar (Vorschau).
- Jeder Nachweis speichert den Stand der Unterweisung beim Bestehen. Spätere Änderungen verändern alte Nachweise nicht.
- Unterweisungen mit Nachweisen lassen sich nicht löschen, nur deaktivieren.

## Update

```bash
cd /opt/uvv-unterweisungen
cp data/uvv.db ~/uvv-backup-$(date +%F).db
git pull
docker compose up -d --build
```

Neue Tabellen und Spalten werden beim Start automatisch ergänzt, vorhandene Daten bleiben erhalten.

## Backup

Alle Daten liegen im Datenordner (`DATA_PATH`, Standard `./data`): die SQLite-Datenbank `uvv.db`, das Logo und der Sitzungsschlüssel. Diesen Ordner regelmäßig sichern, z. B.:

```bash
cp /opt/uvv-unterweisungen/data/uvv.db ~/uvv-backup-$(date +%F).db
```

Für mehrere Organisationen am besten je eine eigene Installation (eigener Ordner, eigene `.env`, eigene Domain) betreiben.

## Sicherheit

- Passwörter werden nur als Hash gespeichert. Nach 8 Fehlversuchen ist ein Konto 15 Minuten gesperrt.
- Zwei-Faktor-Anmeldung (TOTP) mit 10 Wiederherstellungscodes. Bei verlorenem Handy setzt ein Admin sie unter „Benutzer“ zurück.
- CSRF-Schutz für alle Formulare der Verwaltung, Sicherheits-Header, Sitzungen laufen nach 12 Stunden ab.
- Mit einem zu kurzen oder Platzhalter-Passwort in `ADMIN_PASSWORD` wird kein Admin angelegt.

## Datenschutz

Gespeichert werden nur Vorname, Nachname, Ergebnis, falsch beantwortete Fragen, Zeitpunkt, Unterschrift (als Bild), Versandzeitpunkt und Empfänger bestandener Tests. Nicht bestandene Versuche werden nicht gespeichert. Die Prüfseite ist nur mit dem zufälligen Code aus dem QR-Code erreichbar. Alte Nachweise können unter „Nachweise“ gelöscht werden. Verantwortlich für den Betrieb und die Datenschutzerklärung ist die jeweilige Organisation.

## Lokal ausprobieren

```bash
cp .env.example .env
# in der .env setzen: DOMAIN=localhost:8000, ADMIN_PASSWORD=..., COOKIE_SECURE=0
docker compose up -d --build
```

Dann `http://localhost:8000` öffnen. `COOKIE_SECURE=0` erlaubt die Anmeldung ohne HTTPS und gehört **nicht** auf einen öffentlichen Server.

Ohne Docker (Python 3.12):

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cd app && DATA_DIR=../data ADMIN_PASSWORD=einlangespasswort flask --app app run --debug
```

## Fehlersuche

| Problem | Lösung |
|---|---|
| Anmeldung springt immer wieder zur Login-Seite | Seite wird ohne HTTPS aufgerufen. HTTPS einrichten oder zum Testen `COOKIE_SECURE=0` setzen. |
| Es gibt keinen Admin | `ADMIN_PASSWORD` fehlt oder ist zu kurz. In der `.env` setzen und `docker compose up -d` ausführen. Der Admin wird nur angelegt, solange es noch keinen Benutzer gibt. |
| Mail-Knopf fehlt | `SMTP_HOST` nicht gesetzt oder bei der Unterweisung keine Mailempfänger eingetragen |
| Mailversand schlägt fehl | `docker compose logs uvv-unterweisungen \| grep -A5 Mailversand` |
| QR-Code zeigt eine falsche Adresse | `DOMAIN` in der `.env` prüfen |
| Datenordner nicht beschreibbar | Das Startskript setzt die Rechte selbst. Läuft der Container ohne root: `sudo chown -R 1000:1000 <DATA_PATH>` |

## Technik

Python 3.12, Flask, SQLite, reportlab (PDF), pyotp (2FA), gunicorn, Docker. Der Code liegt in `app/`: `app.py` (Anwendung), `pdf.py` (Nachweis), `seed_drohne.py` (Beispiel-Unterweisung), `templates/`, `static/`.

## Lizenz

[MIT](LICENSE) – frei nutzbar, veränderbar und weitergebbar, ohne Gewähr.
