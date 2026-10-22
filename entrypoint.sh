#!/bin/sh
# Startskript: Der Datenordner ist ein Bind-Mount (DATA_PATH aus der .env) und gehört
# beim ersten Start meist root. Deshalb hier als root die Rechte setzen und die App
# danach als unprivilegierter Nutzer "uvv" starten.
set -e
DATA_DIR="${DATA_DIR:-/data}"

if [ "$(id -u)" = "0" ]; then
  mkdir -p "$DATA_DIR"
  chown -R 1000:1000 "$DATA_DIR" || echo "WARNUNG: konnte Rechte von $DATA_DIR nicht setzen" >&2
  export HOME=/app
  exec setpriv --reuid=1000 --regid=1000 --clear-groups "$@"
fi

# Läuft bereits ohne root (z. B. "user:" in der Compose-Datei gesetzt)
if ! touch "$DATA_DIR/.schreibtest" 2>/dev/null; then
  echo "FEHLER: $DATA_DIR ist für Benutzer $(id -u):$(id -g) nicht beschreibbar." >&2
  echo "Auf dem Host ausführen: sudo chown -R $(id -u):$(id -g) <DATA_PATH aus der .env>" >&2
  exit 1
fi
rm -f "$DATA_DIR/.schreibtest"
exec "$@"
