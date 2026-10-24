import base64
import csv
import hashlib
import io
import json
import math
import os
import random
import re
import secrets
import smtplib
import sqlite3
import ssl
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
from zoneinfo import ZoneInfo

from flask import (Flask, Response, abort, flash, g, redirect, render_template,
                   request, send_file, session, url_for)
import pyotp
import qrcode
import qrcode.image.svg
from PIL import Image
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

from pdf import build_certificate

# ---------------------------------------------------------------- Konfiguration
DATA_DIR = os.environ.get("DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "uvv.db")
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")
# Standardwerte für neue Unterweisungen
PASS_PERCENT = int(os.environ.get("PASS_PERCENT", "80"))
VALID_MONTHS = int(os.environ.get("VALID_MONTHS", "12"))
# Nur für den ersten Start: legt den ersten Admin an, solange es noch keine Benutzer gibt
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
TZ = ZoneInfo(os.environ.get("TZ_DISPLAY", "Europe/Berlin"))
LOGO_PATH = os.path.join(DATA_DIR, "logo.png")

# Mailversand (Empfänger werden pro Unterweisung eingestellt)
MAIL_TO = os.environ.get("MAIL_TO", "")  # nur für die Übernahme der Drohnen-Unterweisung
DEFAULT_MAIL_TO = os.environ.get("DEFAULT_MAIL_TO", "")            # Vorschlag für neue Unterweisungen
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_SECURITY = os.environ.get("SMTP_SECURITY", "starttls").lower()  # starttls | ssl | none
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
MAIL_COOLDOWN = timedelta(minutes=int(os.environ.get("MAIL_COOLDOWN_MINUTES", "10")))
MAIL_ENABLED = bool(SMTP_HOST and SMTP_FROM)

# Projekt, Version und Changelog für die Seite „Über“
PROJECT_URL = "https://github.com/siliconserver/uvv-unterweisungen"
APP_COMMIT = os.environ.get("APP_COMMIT", "")  # wird beim Bauen des Images gesetzt


def load_changelog():
    """Liest CHANGELOG.md (Abschnitte "## <Version> (<Datum>)" mit "- " Punkten)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(here, "CHANGELOG.md"), os.path.join(here, "..", "CHANGELOG.md")):
        if os.path.exists(path):
            break
    else:
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("## "):
                version, _, date = line[3:].strip().partition(" ")
                entries.append({"version": version, "date": date.strip("()"), "items": []})
            elif line.startswith("- ") and entries:
                entries[-1]["items"].append(line[2:].strip())
    return entries


CHANGELOG = load_changelog()
APP_VERSION = CHANGELOG[0]["version"] if CHANGELOG else "unbekannt"

ROLES = {
    "admin": "Admin – alles inkl. Benutzerverwaltung",
    "verwalter": "Verwalter – Unterweisungen und Nachweise",
}
# Einstellungen, die Admins in der Verwaltung ändern: (Schlüssel, Bezeichnung, Standard, Art, Hilfe).
# Beim ersten Start kann jeder Standard über eine gleichnamige Umgebungsvariable vorbelegt werden
# (z. B. ORG_NAME, IMPRESSUM_URL); danach gilt nur noch, was in der Verwaltung gespeichert ist.
SETTINGS = [
    ("org_name", "Name der Organisation", "Freiwillige Feuerwehr Musterstadt",
     "text", "Steht in der Fußzeile, im Nachweis-Text und im PDF."),
    ("brand_top", "Titel im Seitenkopf – Zeile 1", "Feuerwehr", "text", "Groß und gesperrt, z. B. „Feuerwehr“."),
    ("brand_bottom", "Titel im Seitenkopf – Zeile 2", "Musterstadt", "text", "z. B. der Ortsname."),
    ("app_name", "Name des Systems", "UVV Unterweisungen", "text", "Oben rechts im Kopf und im Browser-Tab."),
    ("primary_color", "Hauptfarbe", "#BA0000", "color", "Kopfzeile, Knöpfe und PDF."),
    ("home_headline", "Überschrift der Startseite", "Unterweisungen online erledigen", "text", ""),
    ("home_lead", "Text der Startseite",
     "Wähle die Unterweisung aus, die du machen sollst. Du liest die Inhalte, beantwortest ein paar Fragen, "
     "unterschreibst und bekommst deinen Nachweis als PDF. Das dauert meist etwa zehn Minuten.", "textarea", ""),
    ("sign_place", "Ort neben der Unterschrift", "", "text",
     "Erscheint im PDF als „Ort, Datum“."),
    ("mail_button", "Beschriftung des Mail-Knopfs", "Per Mail an die Wehr senden", "text", ""),
    ("impressum_url", "Link zum Impressum", "", "url", "z. B. die Impressum-Seite eurer Homepage."),
    ("datenschutz_url", "Link zur Datenschutzerklärung", "", "url", ""),
    ("footer_text", "Zusätzlicher Text in der Fußzeile", "", "text", "optional"),
]
SETTINGS = [(k, label, os.environ.get(k.upper(), default), kind, help_)
            for k, label, default, kind, help_ in SETTINGS]
WEAK_PASSWORDS = {"bitte-aendern", "bitte-aendern!", "changeme123", "passwort123", "password123"}
LOGIN_MAX_FAILS = 8
LOGIN_LOCK = timedelta(minutes=15)

os.makedirs(DATA_DIR, exist_ok=True)


def _secret_key():
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
    path = os.path.join(DATA_DIR, ".secret_key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    SECRET_KEY=_secret_key(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # Cookies nur über HTTPS; COOKIE_SECURE=0 nur zum lokalen Testen ohne HTTPS
    SESSION_COOKIE_SECURE=BASE_URL.startswith("https://") and os.environ.get("COOKIE_SECURE", "1") != "0",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,
)


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    if request.path.startswith(("/admin", "/login")):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- Datenbank
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=15)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    try:
        # Mehrere gunicorn-Worker starten gleichzeitig: Einrichtung exklusiv ausführen
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trainings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                short_name TEXT NOT NULL,
                headline TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                subtitle TEXT NOT NULL DEFAULT '',
                legal TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '[]',
                questions TEXT NOT NULL DEFAULT '[]',
                pass_percent INTEGER NOT NULL DEFAULT 80,
                valid_months INTEGER NOT NULL DEFAULT 12,
                mail_to TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                name TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'verwalter',
                active INTEGER NOT NULL DEFAULT 1,
                failed_logins INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                last_login TEXT,
                created_at TEXT NOT NULL
            )""")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        # Spalten aus späteren Versionen nachrüsten (bestehende Datenbanken bleiben erhalten)
        ucols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
        for name, typ in (("totp_secret", "TEXT"), ("totp_last", "INTEGER"), ("recovery_codes", "TEXT")):
            if name not in ucols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {typ}")
        cols = {r[1] for r in conn.execute("PRAGMA table_info(results)")}
        for name, typ in (("signature", "BLOB"), ("signed_at", "TEXT"), ("mailed_at", "TEXT"),
                          ("training_id", "INTEGER"), ("snapshot", "TEXT"), ("mailed_to", "TEXT"),
                          ("review", "TEXT")):
            if name not in cols:
                conn.execute(f"ALTER TABLE results ADD COLUMN {name} {typ}")

        # Gibt es schon Nachweise, wird eine bestehende Installation übernommen
        legacy = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0] > 0

        for key, _label, default, _kind, _help in SETTINGS:  # fehlende Einstellungen mit Startwert anlegen
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, default))

        # Drohnen-Unterweisung als erste Unterweisung anlegen (bei Neuinstallation als inaktives Beispiel)
        if conn.execute("SELECT COUNT(*) FROM trainings").fetchone()[0] == 0:
            from seed_drohne import TRAINING as t
            ts = now_iso()
            conn.execute(
                "INSERT INTO trainings (slug, title, short_name, headline, description, subtitle, legal,"
                " content, questions, pass_percent, valid_months, mail_to, active, sort_order,"
                " created_at, updated_at, updated_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,10,?,?,'System')",
                (t["slug"], t["title"], t["short_name"], t["headline"], t["description"], t["subtitle"],
                 t["legal"], json.dumps(t["content"], ensure_ascii=False),
                 json.dumps(t["questions"], ensure_ascii=False), PASS_PERCENT, VALID_MONTHS,
                 MAIL_TO, 1 if legacy else 0, ts, ts))
            # Alte Nachweise gehören zur Drohnen-Unterweisung und behalten deren heutigen Stand
            snap = {k: t[k] for k in ("title", "short_name", "description", "subtitle", "legal", "content")}
            snap.update(pass_min=math.ceil(len(t["questions"]) * PASS_PERCENT / 100), valid_months=VALID_MONTHS)
            drone_id = conn.execute("SELECT id FROM trainings WHERE slug = ?", (t["slug"],)).fetchone()[0]
            conn.execute("UPDATE results SET training_id = ?, snapshot = ? WHERE training_id IS NULL",
                         (drone_id, json.dumps(snap, ensure_ascii=False)))

        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            if len(ADMIN_PASSWORD) < 10 or ADMIN_PASSWORD in WEAK_PASSWORDS:
                print("HINWEIS: Kein Admin angelegt. Bitte in der .env ein eigenes ADMIN_PASSWORD "
                      "mit mindestens 10 Zeichen setzen und den Container neu starten.", flush=True)
            else:
                conn.execute(
                    "INSERT INTO users (username, name, password_hash, role, created_at) VALUES (?,?,?,?,?)",
                    (ADMIN_USER, "Administrator", generate_password_hash(ADMIN_PASSWORD), "admin", now_iso()))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


init_db()


# ---------------------------------------------------------------- Unterweisungen
def load_training(row):
    if row is None:
        return None
    t = dict(row)
    t["content"] = json.loads(t["content"] or "[]")
    t["questions"] = json.loads(t["questions"] or "[]")
    t["count"] = len(t["questions"])
    t["pass_min"] = math.ceil(t["count"] * t["pass_percent"] / 100)
    t["mail_list"] = parse_mails(t["mail_to"])[0]
    t["active"] = bool(t["active"])
    return t


def get_training(slug=None, tid=None, public=False):
    if tid is not None:
        row = db().execute("SELECT * FROM trainings WHERE id = ?", (tid,)).fetchone()
    else:
        row = db().execute("SELECT * FROM trainings WHERE slug = ?", (slug,)).fetchone()
    t = load_training(row)
    # Inaktive Unterweisungen sind nur für angemeldete Verwalter sichtbar (Vorschau)
    if t is None or (public and not t["active"] and not g.user):
        abort(404)
    return t


def snapshot_of(t):
    """Stand der Unterweisung beim Bestehen – bleibt im Nachweis, auch wenn sie später geändert wird."""
    keys = ("title", "short_name", "description", "subtitle", "legal", "content", "pass_min", "valid_months")
    return {k: t[k] for k in keys}


def parse_mails(value):
    parts = [p.strip() for p in re.split(r"[,;\s]+", value or "") if p.strip()]
    good = [p for p in parts if re.fullmatch(r"[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+", p)]
    bad = [p for p in parts if p not in good]
    return good, bad


# ---------------------------------------------------------------- Hilfen
def add_months(dt, months):
    y, m = divmod(dt.month - 1 + months, 12)
    year, month = dt.year + y, m + 1
    days = [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return dt.replace(year=year, month=month, day=min(dt.day, days))


def _training_info(row):
    """Angaben zur Unterweisung eines Nachweises: gespeicherter Stand, sonst aktueller Stand."""
    if row["snapshot"]:
        return json.loads(row["snapshot"])
    t = get_training(tid=row["training_id"]) if row["training_id"] else None
    if t is None:
        abort(404)
    return snapshot_of(t)


def enrich(row):
    t = _training_info(row)
    created = datetime.fromisoformat(row["created_at"]).astimezone(TZ)
    valid_until = add_months(created, t["valid_months"])
    return {
        **dict(row),
        "t": t,
        "name": f'{row["first_name"]} {row["last_name"]}',
        "created": created,
        "date_str": created.strftime("%d.%m.%Y"),
        "datetime_str": created.strftime("%d.%m.%Y, %H:%M Uhr"),
        "valid_until": valid_until,
        "valid_str": valid_until.strftime("%d.%m.%Y"),
        "is_valid": datetime.now(TZ) <= valid_until,
        "short_id": hashlib.sha256(row["token"].encode()).hexdigest()[:8].upper(),
        "signed": row["signature"] is not None,
        "signed_str": _fmt(row["signed_at"]),
        "mailed_str": _fmt(row["mailed_at"]),
    }


def _fmt(iso):
    if not iso:
        return None
    return datetime.fromisoformat(iso).astimezone(TZ).strftime("%d.%m.%Y, %H:%M Uhr")


def get_result(token):
    row = db().execute("SELECT * FROM results WHERE token = ?", (token,)).fetchone()
    if row is None:
        abort(404)
    return enrich(row)


def verify_url(token):
    base = BASE_URL or request.url_root.rstrip("/")
    return f"{base}/pruefen/{token}"


def clean_name(value, limit=60):
    value = " ".join((value or "").split())
    return value[:limit]


def interval_label(months):
    if months == 12:
        return "Jährliche Pflichtunterweisung"
    if months == 24:
        return "Pflichtunterweisung alle zwei Jahre"
    return f"Pflichtunterweisung alle {months} Monate"


# ---------------------------------------------------------------- Einstellungen & Erscheinungsbild
def settings():
    if "settings" not in g:
        g.settings = {k: d for k, _l, d, _t, _h in SETTINGS}
        g.settings.update({r["key"]: r["value"] for r in db().execute("SELECT key, value FROM settings")})
    return g.settings


def _hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def theme_colors(primary):
    """Hauptfarbe plus dunklere Variante (Hover) und helle Variante (Hintergründe)."""
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", primary or ""):
        primary = "#BA0000"
    r, g_, b = _hex_rgb(primary)
    dark = "#{:02X}{:02X}{:02X}".format(*(int(c * 0.76) for c in (r, g_, b)))
    soft = "#{:02X}{:02X}{:02X}".format(*(int(255 - (255 - c) * 0.1) for c in (r, g_, b)))
    return {"primary": primary.upper(), "dark": dark, "soft": soft}


def logo_version():
    try:
        return int(os.path.getmtime(LOGO_PATH))
    except OSError:
        return None


@app.get("/logo.png")
def logo():
    if not os.path.exists(LOGO_PATH):
        abort(404)
    return send_file(LOGO_PATH, mimetype="image/png", max_age=86400)


# ---------------------------------------------------------------- Anmeldung
@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        row = db().execute("SELECT * FROM users WHERE id = ? AND active = 1", (uid,)).fetchone()
        if row is None:
            session.pop("uid", None)
        else:
            g.user = dict(row)
    if request.method == "POST" and request.path.startswith(("/admin", "/login")):
        expected = session.get("csrf", "")
        if not expected or not secrets.compare_digest(request.form.get("csrf", ""), expected):
            abort(400)


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]


def login_required(role=None):
    def deco(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not g.user:
                return redirect(url_for("login", next=request.full_path.rstrip("?")))
            if role and g.user["role"] != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapper
    return deco


@app.context_processor
def inject_globals():
    cfg = settings()
    return {"cfg": cfg, "org_name": cfg["org_name"], "app_name": cfg["app_name"],
            "theme": theme_colors(cfg["primary_color"]), "logo_v": logo_version(),
            "year": datetime.now(TZ).year, "current_user": g.get("user"), "csrf_token": csrf_token,
            "roles": ROLES, "interval_label": interval_label, "app_version": APP_VERSION}


def _safe_next(value):
    return value if value and value.startswith("/") and not value.startswith("//") else url_for("admin")


def _is_locked(row):
    return bool(row["locked_until"]) and datetime.fromisoformat(row["locked_until"]) > datetime.now(timezone.utc)


def _register_fail(conn, row):
    fails = row["failed_logins"] + 1
    until = (datetime.now(timezone.utc) + LOGIN_LOCK).isoformat() if fails >= LOGIN_MAX_FAILS else None
    conn.execute("UPDATE users SET failed_logins = ?, locked_until = ? WHERE id = ?",
                 (0 if until else fails, until, row["id"]))
    conn.commit()
    time.sleep(0.8)


def _finish_login(conn, row, nxt):
    conn.execute("UPDATE users SET failed_logins = 0, locked_until = NULL, last_login = ? WHERE id = ?",
                 (now_iso(), row["id"]))
    conn.commit()
    session.clear()
    session.permanent = True
    session["uid"] = row["id"]
    return redirect(nxt)


@app.route("/login", methods=["GET", "POST"])
def login():
    nxt = _safe_next(request.values.get("next", ""))
    if g.user:
        return redirect(nxt)
    error = None
    username = clean_name(request.form.get("username"))
    if request.method == "POST":
        conn = db()
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        locked = row is not None and _is_locked(row)
        if row and row["active"] and not locked and check_password_hash(row["password_hash"],
                                                                         request.form.get("password", "")):
            if not row["totp_secret"]:
                return _finish_login(conn, row, nxt)
            # Zweiter Schritt: Code aus der Authenticator-App
            session.clear()
            session["pending"] = {"uid": row["id"], "next": nxt, "at": time.time()}
            return redirect(url_for("login_2fa"))
        if row and not locked:
            _register_fail(conn, row)
        else:
            time.sleep(0.8)
        error = ("Zu viele Fehlversuche. Bitte in 15 Minuten erneut versuchen." if locked
                 else "Benutzername oder Passwort ist falsch.")
    no_users = db().execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    return render_template("login.html", error=error, username=username, next=nxt, no_users=no_users)


def check_totp(row, code):
    """Prüft einen 6-stelligen Code; jeder Code gilt nur einmal. Gibt den Zeitschritt zurück oder None."""
    totp = pyotp.TOTP(row["totp_secret"])
    now = time.time()
    for offset in (0, -1, 1):  # eine Minute Toleranz für ungenaue Uhren
        step = int(now // 30) + offset
        if secrets.compare_digest(totp.at(step * 30), code) and step > (row["totp_last"] or 0):
            return step
    return None


def _hash_code(code):
    return hashlib.sha256(code.replace("-", "").lower().encode()).hexdigest()


def new_recovery_codes():
    codes = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(10)]
    return codes, json.dumps([_hash_code(c) for c in codes])


@app.route("/login/2fa", methods=["GET", "POST"])
def login_2fa():
    pending = session.get("pending")
    if not pending or time.time() - pending["at"] > 300:
        session.pop("pending", None)
        flash("Bitte noch einmal anmelden.", "info")
        return redirect(url_for("login"))
    error = None
    if request.method == "POST":
        conn = db()
        row = conn.execute("SELECT * FROM users WHERE id = ? AND active = 1", (pending["uid"],)).fetchone()
        if row is None or not row["totp_secret"] or _is_locked(row):
            session.pop("pending", None)
            flash("Zu viele Fehlversuche. Bitte in 15 Minuten erneut versuchen." if row else
                  "Bitte noch einmal anmelden.", "error")
            return redirect(url_for("login"))
        code = re.sub(r"\s", "", request.form.get("code", "")).lower()
        if re.fullmatch(r"\d{6}", code):
            step = check_totp(row, code)
            if step:
                conn.execute("UPDATE users SET totp_last = ? WHERE id = ?", (step, row["id"]))
                return _finish_login(conn, row, pending["next"])
        elif code:
            hashes = json.loads(row["recovery_codes"] or "[]")
            h = _hash_code(code)
            if h in hashes:
                hashes.remove(h)
                conn.execute("UPDATE users SET recovery_codes = ? WHERE id = ?", (json.dumps(hashes), row["id"]))
                flash(f"Wiederherstellungscode verwendet. Es sind noch {len(hashes)} übrig.", "info")
                return _finish_login(conn, row, pending["next"])
        _register_fail(conn, row)
        error = "Der Code stimmt nicht. Bitte den aktuellen Code aus der App eingeben."
    return render_template("login_2fa.html", error=error)


@app.post("/admin/abmelden")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------- Teilnehmer
@app.get("/")
def index():
    rows = db().execute("SELECT * FROM trainings WHERE active = 1 ORDER BY sort_order, title").fetchall()
    return render_template("index.html", trainings=[load_training(r) for r in rows])


def _person_key(t):
    return f"person_{t['id']}"


@app.get("/unterweisung/<slug>")
def training(slug):
    t = get_training(slug, public=True)
    return render_template("training.html", t=t, form=session.get(_person_key(t), {}))


@app.post("/unterweisung/<slug>/start")
def start(slug):
    t = get_training(slug, public=True)
    first = clean_name(request.form.get("first_name"))
    last = clean_name(request.form.get("last_name"))
    errors = []
    if len(first) < 2:
        errors.append("Bitte gib deinen Vornamen ein.")
    if len(last) < 2:
        errors.append("Bitte gib deinen Nachnamen ein.")
    if not request.form.get("read"):
        errors.append("Bitte bestätige, dass du die Inhalte der Unterweisung gelesen hast.")
    if errors:
        return render_template("training.html", t=t, errors=errors,
                               form={"first_name": first, "last_name": last}), 400
    session[_person_key(t)] = {"first_name": first, "last_name": last}
    return redirect(url_for("test", slug=slug))


@app.get("/unterweisung/<slug>/test")
def test(slug):
    t = get_training(slug, public=True)
    person = session.get(_person_key(t))
    if not person or not t["questions"]:
        return redirect(url_for("training", slug=slug))
    questions = []
    for q in random.sample(t["questions"], t["count"]):
        opts = list(q["options"].items())
        random.shuffle(opts)
        questions.append({"id": q["id"], "text": q["text"], "options": opts})
    return render_template("test.html", t=t, person=person, questions=questions)


@app.post("/unterweisung/<slug>/auswerten")
def evaluate(slug):
    t = get_training(slug, public=True)
    person = session.get(_person_key(t))
    if not person:
        return redirect(url_for("training", slug=slug))

    wrong, score = [], 0
    for q in t["questions"]:
        given = request.form.get(q["id"])
        if given == q["correct"]:
            score += 1
        else:
            wrong.append({
                "text": q["text"],
                "given": q["options"].get(given, "keine Antwort"),
                "correct": q["options"][q["correct"]],
                "explain": q.get("explain", ""),
            })

    if score < t["pass_min"]:
        return render_template("failed.html", t=t, person=person, score=score,
                               total=t["count"], wrong=wrong)

    token = secrets.token_urlsafe(16)
    conn = db()
    conn.execute(
        "INSERT INTO results (token, first_name, last_name, score, total, created_at, training_id, snapshot,"
        " review) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (token, person["first_name"], person["last_name"], score, t["count"], now_iso(), t["id"],
         json.dumps(snapshot_of(t), ensure_ascii=False), json.dumps(wrong, ensure_ascii=False)))
    conn.commit()
    session.pop(_person_key(t), None)
    return redirect(url_for("result", token=token))


def _mail_targets(r):
    t = get_training(tid=r["training_id"]) if r["training_id"] else None
    return t["mail_list"] if t else []


@app.get("/ergebnis/<token>")
def result(token):
    r = get_result(token)
    mail_to = _mail_targets(r)
    review = json.loads(r["review"]) if r["review"] else None
    return render_template("result.html", r=r, t=r["t"], mail_enabled=MAIL_ENABLED and bool(mail_to),
                           mail_to=", ".join(mail_to), mailed_to=r["mailed_to"] or ", ".join(mail_to),
                           sign_place=settings()["sign_place"], review=review)


def make_pdf(r):
    signed_at = datetime.fromisoformat(r["signed_at"]).astimezone(TZ) if r["signed_at"] else None
    cfg = settings()
    pdf = build_certificate(r, verify_url(r["token"]), r["t"], cfg,
                            LOGO_PATH if os.path.exists(LOGO_PATH) else None,
                            theme_colors(cfg["primary_color"])["primary"],
                            signature=r["signature"], signed_at=signed_at)
    filename = f'UVV-{r["t"]["short_name"]}_{r["last_name"]}_{r["first_name"]}_{r["created"]:%Y-%m-%d}.pdf'
    filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    return pdf, filename


@app.get("/nachweis/<token>.pdf")
def certificate(token):
    pdf, filename = make_pdf(get_result(token))
    resp = send_file(io.BytesIO(pdf), mimetype="application/pdf",
                     as_attachment=request.args.get("download") == "1",
                     download_name=filename)
    resp.headers["Cache-Control"] = "no-store"
    return resp


MAX_SIG_BYTES = 400_000


@app.post("/unterschrift/<token>")
def sign(token):
    r = get_result(token)
    if r["signed"]:
        flash("Der Nachweis ist bereits unterschrieben.", "info")
        return redirect(url_for("result", token=token))

    data = request.form.get("signature", "")
    prefix = "data:image/png;base64,"
    try:
        if not data.startswith(prefix) or len(data) > MAX_SIG_BYTES * 4 // 3 + 100:
            raise ValueError
        raw = base64.b64decode(data[len(prefix):], validate=True)
        img = Image.open(io.BytesIO(raw))
        img.verify()
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        # Nur die gezeichneten Pixel behalten; leeres Feld ablehnen
        bbox = img.getchannel("A").getbbox()
        if not bbox or (bbox[2] - bbox[0]) < 20 or (bbox[3] - bbox[1]) < 8:
            raise ValueError
        pad = 6
        img = img.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                        min(img.width, bbox[2] + pad), min(img.height, bbox[3] + pad)))
        img.thumbnail((1200, 400))
        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
    except Exception:
        flash("Die Unterschrift konnte nicht gespeichert werden. Bitte noch einmal unterschreiben.", "error")
        return redirect(url_for("result", token=token))

    conn = db()
    conn.execute("UPDATE results SET signature = ?, signed_at = ? WHERE token = ? AND signature IS NULL",
                 (out.getvalue(), now_iso(), token))
    conn.commit()
    flash("Unterschrift gespeichert – sie ist jetzt im PDF enthalten.", "success")
    return redirect(url_for("result", token=token) + "#aktionen")


def send_certificate_mail(r, pdf, filename, recipients):
    t = r["t"]
    msg = EmailMessage()
    msg["Subject"] = f"UVV-Unterweisung {t['short_name']}: {r['name']} ({r['date_str']})"
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(recipients)
    msg.set_content(
        f"Neuer Nachweis über die {t['title']}\n\n"
        f"Name:          {r['name']}\n"
        f"Datum:         {r['datetime_str']}\n"
        f"Ergebnis:      {r['score']} von {r['total']} richtig\n"
        f"Gültig bis:    {r['valid_str']}\n"
        f"Unterschrift:  {'ja, ' + r['signed_str'] if r['signed'] else 'nein'}\n"
        f"Nachweis-ID:   {r['short_id']}\n\n"
        f"Online prüfen: {verify_url(r['token'])}\n\n"
        f"Der Nachweis ist als PDF angehängt.\n"
    )
    msg.add_attachment(pdf, maintype="application", subtype="pdf", filename=filename)

    ctx = ssl.create_default_context()
    if SMTP_SECURITY == "ssl":
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=20)
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
    with server:
        if SMTP_SECURITY == "starttls":
            server.starttls(context=ctx)
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


@app.post("/mailen/<token>")
def mail(token):
    r = get_result(token)
    target = url_for("result", token=token) + "#aktionen"
    recipients = _mail_targets(r)
    if not MAIL_ENABLED or not recipients:
        flash("Der Mailversand ist für diese Unterweisung nicht eingerichtet.", "error")
        return redirect(target)
    if not r["signed"]:
        flash("Bitte zuerst unterschreiben.", "error")
        return redirect(target)
    if r["mailed_at"]:
        last = datetime.fromisoformat(r["mailed_at"])
        if datetime.now(timezone.utc) - last < MAIL_COOLDOWN:
            flash(f"Der Nachweis wurde bereits am {r['mailed_str']} verschickt.", "info")
            return redirect(target)

    pdf, filename = make_pdf(r)
    try:
        send_certificate_mail(r, pdf, filename, recipients)
    except Exception as exc:
        app.logger.exception("Mailversand fehlgeschlagen: %s", exc)
        flash("Die Mail konnte nicht verschickt werden. Bitte später noch einmal versuchen "
              "oder das PDF herunterladen und selbst schicken.", "error")
        return redirect(target)

    conn = db()
    conn.execute("UPDATE results SET mailed_at = ?, mailed_to = ? WHERE token = ?",
                 (now_iso(), ", ".join(recipients), token))
    conn.commit()
    flash(f"Nachweis an {', '.join(recipients)} verschickt.", "success")
    return redirect(target)


@app.get("/pruefen/<token>")
def verify(token):
    row = db().execute("SELECT * FROM results WHERE token = ?", (token,)).fetchone()
    if row is None:
        return render_template("verify.html", r=None), 404
    r = enrich(row)
    return render_template("verify.html", r=r, t=r["t"])


# ---------------------------------------------------------------- Verwaltung: Übersicht & Nachweise
@app.get("/admin")
@login_required()
def admin():
    rows = db().execute("""
        SELECT t.*, COUNT(r.id) AS n, MAX(r.created_at) AS last
        FROM trainings t LEFT JOIN results r ON r.training_id = t.id
        GROUP BY t.id ORDER BY t.sort_order, t.title""").fetchall()
    trainings = []
    for row in rows:
        t = load_training(row)
        t["n"], t["last_str"] = row["n"], _fmt(row["last"])
        trainings.append(t)
    return render_template("admin/dashboard.html", trainings=trainings, mail_enabled=MAIL_ENABLED)


def _results_query(slug):
    sql = "SELECT r.* FROM results r"
    args = ()
    t = None
    if slug:
        t = get_training(slug)
        sql += " WHERE r.training_id = ?"
        args = (t["id"],)
    return t, db().execute(sql + " ORDER BY r.created_at DESC", args).fetchall()


@app.get("/admin/nachweise")
@login_required()
def admin_results():
    slug = request.args.get("u") or None
    t, rows = _results_query(slug)
    all_t = db().execute("SELECT slug, title FROM trainings ORDER BY sort_order, title").fetchall()
    return render_template("admin/results.html", rows=[enrich(r) for r in rows], t=t, trainings=all_t)


@app.get("/admin/nachweise.csv")
@login_required()
def admin_export():
    slug = request.args.get("u") or None
    t, rows = _results_query(slug)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Unterweisung", "Nachname", "Vorname", "Datum", "Ergebnis", "Gültig bis", "Unterschrieben",
                "Per Mail verschickt", "Nachweis-ID"])
    for r in map(enrich, rows):
        w.writerow([r["t"]["title"], r["last_name"], r["first_name"], r["datetime_str"],
                    f'{r["score"]}/{r["total"]}', r["valid_str"], r["signed_str"] or "",
                    r["mailed_str"] or "", r["short_id"]])
    name = f"uvv-{t['slug']}.csv" if t else "uvv-nachweise.csv"
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={name}"})


@app.post("/admin/nachweise/<token>/loeschen")
@login_required()
def admin_delete(token):
    conn = db()
    conn.execute("DELETE FROM results WHERE token = ?", (token,))
    conn.commit()
    flash("Nachweis gelöscht.", "success")
    back = request.form.get("back", "")
    return redirect(back if back.startswith("/") and not back.startswith("//") else url_for("admin_results"))


# ---------------------------------------------------------------- Verwaltung: Unterweisungen
def content_to_text(content):
    lines = []
    for heading, items in content:
        lines.append(f"## {heading}")
        lines += [f"- {i}" for i in items]
        lines.append("")
    return "\n".join(lines).strip()


def text_to_content(text):
    sections = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            sections.append([s.lstrip("#").strip(), []])
            continue
        if s[0] in "-•*":
            s = s[1:].strip()
        if not sections:
            sections.append(["Inhalte", []])
        if s:
            sections[-1][1].append(s)
    return [sec for sec in sections if sec[0] and sec[1]]


def slugify(value):
    value = value.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")[:40]


def parse_questions(raw):
    """Fragen aus dem Editor (JSON) prüfen. Gibt (Fragen, Fehlerliste) zurück."""
    try:
        data = json.loads(raw or "[]")
        assert isinstance(data, list)
    except Exception:
        return [], ["Die Fragen konnten nicht gelesen werden."]
    out, errors, seen = [], [], set()
    for n, q in enumerate(data, 1):
        text = clean_name(str(q.get("text", "")), 500)
        options = [clean_name(str(o), 300) for o in q.get("options", [])]
        options = [o for o in options if o]
        try:
            correct = int(q.get("correct"))
        except (TypeError, ValueError):
            correct = -1
        explain = clean_name(str(q.get("explain", "")), 600)
        if not text and not options:
            continue  # leere Frage ignorieren
        if not text:
            errors.append(f"Frage {n}: Der Fragetext fehlt.")
        if len(options) < 2:
            errors.append(f"Frage {n}: Es braucht mindestens zwei Antworten.")
        if not 0 <= correct < len(options):
            errors.append(f"Frage {n}: Bitte die richtige Antwort markieren.")
            correct = 0
        qid = str(q.get("id") or "")
        if not re.fullmatch(r"[a-z0-9]{1,16}", qid) or qid in seen:
            qid = "q" + secrets.token_hex(4)
        seen.add(qid)
        keys = "abcdefgh"
        out.append({"id": qid, "text": text,
                    "options": {keys[i]: o for i, o in enumerate(options[:8])},
                    "correct": keys[min(correct, 7)], "explain": explain})
    if not out:
        errors.append("Bitte mindestens eine Frage anlegen.")
    return out, errors


def questions_for_editor(questions):
    return [{"id": q["id"], "text": q["text"], "options": list(q["options"].values()),
             "correct": list(q["options"]).index(q["correct"]), "explain": q.get("explain", "")}
            for q in questions]


EMPTY_TRAINING = {
    "id": None, "slug": "", "title": "UVV-Unterweisung ", "short_name": "", "headline": "",
    "description": "", "subtitle": "gemäß DGUV Vorschrift 1 und DGUV Vorschrift 49", "legal": "",
    "content": [], "questions": [], "pass_percent": PASS_PERCENT, "valid_months": VALID_MONTHS,
    "mail_to": DEFAULT_MAIL_TO, "active": False, "sort_order": 100,
}


@app.route("/admin/unterweisungen/neu", methods=["GET", "POST"])
@app.route("/admin/unterweisungen/<int:tid>", methods=["GET", "POST"])
@login_required()
def admin_training(tid=None):
    t = get_training(tid=tid) if tid else dict(EMPTY_TRAINING)
    if request.method == "GET":
        return render_template("admin/training.html", t=t, content_text=content_to_text(t["content"]),
                               questions=questions_for_editor(t["questions"]), errors=[])

    f = request.form
    data = {
        "title": clean_name(f.get("title"), 120),
        "short_name": clean_name(f.get("short_name"), 40),
        "headline": clean_name(f.get("headline"), 120),
        "description": clean_name(f.get("description"), 300),
        "subtitle": clean_name(f.get("subtitle"), 160),
        "legal": clean_name(f.get("legal"), 1000),
        "slug": slugify(f.get("slug") or f.get("short_name") or ""),
        "mail_to": f.get("mail_to", ""),
        "active": 1 if f.get("active") else 0,
    }
    errors = []
    for key, label in (("title", "Titel"), ("short_name", "Kurzname"), ("headline", "Überschrift")):
        if not data[key]:
            errors.append(f"Bitte {label} ausfüllen.")
    for key, label, lo, hi in (("pass_percent", "Bestehensgrenze", 1, 100),
                               ("valid_months", "Gültigkeit", 1, 120),
                               ("sort_order", "Reihenfolge", 0, 9999)):
        try:
            data[key] = int(f.get(key, ""))
            assert lo <= data[key] <= hi
        except (ValueError, AssertionError):
            errors.append(f"{label}: bitte eine Zahl von {lo} bis {hi} eingeben.")
            data[key] = t.get(key)
    if not data["slug"]:
        errors.append("Bitte eine Webadresse (Kürzel) angeben.")
    elif db().execute("SELECT 1 FROM trainings WHERE slug = ? AND id IS NOT ?", (data["slug"], tid)).fetchone():
        errors.append(f"Die Webadresse „{data['slug']}“ ist schon vergeben.")
    mails, bad = parse_mails(data["mail_to"])
    if bad:
        errors.append("Ungültige Mailadresse: " + ", ".join(bad))
    data["mail_to"] = ", ".join(mails)
    content = text_to_content(f.get("content"))
    if not content:
        errors.append("Bitte die Inhalte der Unterweisung eintragen (Abschnitte mit ## Überschrift).")
    questions, qerr = parse_questions(f.get("questions"))
    errors += qerr

    if errors:
        t.update(data)
        return render_template("admin/training.html", t=t, content_text=f.get("content", ""),
                               questions=questions_for_editor(questions), errors=errors), 400

    data["content"] = json.dumps(content, ensure_ascii=False)
    data["questions"] = json.dumps(questions, ensure_ascii=False)
    data["updated_at"] = now_iso()
    data["updated_by"] = g.user["name"] or g.user["username"]
    conn = db()
    if tid:
        cols = ", ".join(f"{k} = ?" for k in data)
        conn.execute(f"UPDATE trainings SET {cols} WHERE id = ?", (*data.values(), tid))
    else:
        data["created_at"] = data["updated_at"]
        cols = ", ".join(data)
        conn.execute(f"INSERT INTO trainings ({cols}) VALUES ({', '.join('?' * len(data))})",
                     tuple(data.values()))
        tid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    flash("Unterweisung gespeichert." + ("" if data["active"] else " Sie ist noch nicht freigeschaltet."),
          "success")
    return redirect(url_for("admin_training", tid=tid))


@app.post("/admin/unterweisungen/<int:tid>/kopieren")
@login_required()
def admin_training_copy(tid):
    t = get_training(tid=tid)
    conn = db()
    slug, n = f"{t['slug']}-kopie", 2
    while conn.execute("SELECT 1 FROM trainings WHERE slug = ?", (slug,)).fetchone():
        slug, n = f"{t['slug']}-kopie-{n}", n + 1
    ts = now_iso()
    conn.execute(
        "INSERT INTO trainings (slug, title, short_name, headline, description, subtitle, legal, content,"
        " questions, pass_percent, valid_months, mail_to, active, sort_order, created_at, updated_at, updated_by)"
        " SELECT ?, title || ' (Kopie)', short_name, headline, description, subtitle, legal, content, questions,"
        " pass_percent, valid_months, mail_to, 0, sort_order + 1, ?, ?, ? FROM trainings WHERE id = ?",
        (slug, ts, ts, g.user["name"] or g.user["username"], tid))
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    flash("Kopie angelegt. Sie ist noch nicht freigeschaltet.", "success")
    return redirect(url_for("admin_training", tid=new_id))


@app.post("/admin/unterweisungen/<int:tid>/loeschen")
@login_required()
def admin_training_delete(tid):
    t = get_training(tid=tid)
    conn = db()
    if conn.execute("SELECT 1 FROM results WHERE training_id = ?", (tid,)).fetchone():
        flash("Zu dieser Unterweisung gibt es Nachweise. Sie kann deshalb nicht gelöscht, "
              "sondern nur deaktiviert werden.", "error")
        return redirect(url_for("admin_training", tid=tid))
    conn.execute("DELETE FROM trainings WHERE id = ?", (tid,))
    conn.commit()
    flash(f"Unterweisung „{t['title']}“ gelöscht.", "success")
    return redirect(url_for("admin"))


# ---------------------------------------------------------------- Verwaltung: Benutzer
def _active_admins(exclude=None):
    return db().execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1 AND id IS NOT ?",
                        (exclude,)).fetchone()[0]


@app.get("/admin/benutzer")
@login_required("admin")
def admin_users():
    users = [dict(u, last_login_str=_fmt(u["last_login"]))
             for u in db().execute("SELECT * FROM users ORDER BY active DESC, role, username").fetchall()]
    return render_template("admin/users.html", users=users)


@app.route("/admin/benutzer/neu", methods=["GET", "POST"])
@app.route("/admin/benutzer/<int:uid>", methods=["GET", "POST"])
@login_required("admin")
def admin_user(uid=None):
    conn = db()
    u = None
    if uid:
        u = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if u is None:
            abort(404)
        u = dict(u)
    if request.method == "GET":
        return render_template("admin/user.html", u=u or {"role": "verwalter", "active": 1}, errors=[])

    f = request.form
    data = {
        "username": clean_name(f.get("username"), 40).lower(),
        "name": clean_name(f.get("name"), 80),
        "email": clean_name(f.get("email"), 120),
        "role": f.get("role") if f.get("role") in ROLES else "verwalter",
        "active": 1 if f.get("active") else 0,
    }
    password = f.get("password", "")
    errors = []
    if not re.fullmatch(r"[a-z0-9._-]{2,40}", data["username"]):
        errors.append("Benutzername: 2–40 Zeichen, nur Kleinbuchstaben, Ziffern, Punkt, Binde- oder Unterstrich.")
    elif conn.execute("SELECT 1 FROM users WHERE username = ? AND id IS NOT ?", (data["username"], uid)).fetchone():
        errors.append("Diesen Benutzernamen gibt es schon.")
    if data["email"] and parse_mails(data["email"])[1]:
        errors.append("Die Mailadresse ist ungültig.")
    if (not uid or password) and len(password) < 10:
        errors.append("Das Passwort muss mindestens 10 Zeichen haben.")
    if uid == g.user["id"] and (data["role"] != "admin" or not data["active"]):
        errors.append("Du kannst dir selbst die Admin-Rolle nicht entziehen und dich nicht deaktivieren.")
    if u and u["role"] == "admin" and (data["role"] != "admin" or not data["active"]) and _active_admins(uid) == 0:
        errors.append("Es muss mindestens ein aktiver Admin bleiben.")
    if errors:
        return render_template("admin/user.html", u={**(u or {}), **data}, errors=errors), 400

    if password:
        data["password_hash"] = generate_password_hash(password)
        data["failed_logins"], data["locked_until"] = 0, None
    if uid and f.get("reset_2fa"):
        data["totp_secret"] = data["totp_last"] = data["recovery_codes"] = None
    if uid:
        cols = ", ".join(f"{k} = ?" for k in data)
        conn.execute(f"UPDATE users SET {cols} WHERE id = ?", (*data.values(), uid))
    else:
        data["created_at"] = now_iso()
        conn.execute(f"INSERT INTO users ({', '.join(data)}) VALUES ({', '.join('?' * len(data))})",
                     tuple(data.values()))
    conn.commit()
    flash(f"Benutzer „{data['username']}“ gespeichert.", "success")
    return redirect(url_for("admin_users"))


@app.post("/admin/benutzer/<int:uid>/loeschen")
@login_required("admin")
def admin_user_delete(uid):
    conn = db()
    u = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if u is None:
        abort(404)
    if uid == g.user["id"]:
        flash("Du kannst dich nicht selbst löschen.", "error")
    elif u["role"] == "admin" and _active_admins(uid) == 0:
        flash("Es muss mindestens ein aktiver Admin bleiben.", "error")
    else:
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()
        flash(f"Benutzer „{u['username']}“ gelöscht.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/konto", methods=["GET", "POST"])
@login_required()
def admin_account():
    errors = []
    if request.method == "POST":
        f = request.form
        if not check_password_hash(g.user["password_hash"], f.get("current", "")):
            errors.append("Das aktuelle Passwort ist falsch.")
        if len(f.get("password", "")) < 10:
            errors.append("Das neue Passwort muss mindestens 10 Zeichen haben.")
        elif f.get("password") != f.get("password2"):
            errors.append("Die beiden neuen Passwörter stimmen nicht überein.")
        if not errors:
            conn = db()
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                         (generate_password_hash(f["password"]), g.user["id"]))
            conn.commit()
            flash("Passwort geändert.", "success")
            return redirect(url_for("admin_account"))
    codes_left = len(json.loads(g.user["recovery_codes"] or "[]"))
    return render_template("admin/account.html", errors=errors, codes_left=codes_left)


def _qr_svg(data):
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    return img.to_string(encoding="unicode")


@app.route("/admin/konto/2fa", methods=["GET", "POST"])
@login_required()
def admin_2fa_setup():
    if g.user["totp_secret"]:
        return redirect(url_for("admin_account"))
    secret = session.get("totp_setup") or pyotp.random_base32()
    session["totp_setup"] = secret
    error = None
    if request.method == "POST":
        code = re.sub(r"\s", "", request.form.get("code", ""))
        step = check_totp({"totp_secret": secret, "totp_last": 0}, code) if re.fullmatch(r"\d{6}", code) else None
        if step:
            codes, hashes = new_recovery_codes()
            conn = db()
            conn.execute("UPDATE users SET totp_secret = ?, totp_last = ?, recovery_codes = ? WHERE id = ?",
                         (secret, step, hashes, g.user["id"]))
            conn.commit()
            session.pop("totp_setup", None)
            return render_template("admin/recovery_codes.html", codes=codes, first=True)
        error = "Der Code stimmt nicht. Bitte den aktuellen Code aus der App eingeben."
    uri = pyotp.TOTP(secret).provisioning_uri(name=g.user["username"], issuer_name=settings()["app_name"])
    pretty = " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))
    return render_template("admin/twofa_setup.html", qr=_qr_svg(uri), secret=pretty, error=error)


@app.post("/admin/konto/2fa/aus")
@login_required()
def admin_2fa_disable():
    if not check_password_hash(g.user["password_hash"], request.form.get("current", "")):
        flash("Das Passwort ist falsch. Die Zwei-Faktor-Anmeldung bleibt aktiv.", "error")
        return redirect(url_for("admin_account"))
    conn = db()
    conn.execute("UPDATE users SET totp_secret = NULL, totp_last = NULL, recovery_codes = NULL WHERE id = ?",
                 (g.user["id"],))
    conn.commit()
    flash("Zwei-Faktor-Anmeldung ausgeschaltet.", "success")
    return redirect(url_for("admin_account"))


@app.post("/admin/konto/2fa/codes")
@login_required()
def admin_2fa_codes():
    if not g.user["totp_secret"]:
        return redirect(url_for("admin_account"))
    if not check_password_hash(g.user["password_hash"], request.form.get("current", "")):
        flash("Das Passwort ist falsch.", "error")
        return redirect(url_for("admin_account"))
    codes, hashes = new_recovery_codes()
    conn = db()
    conn.execute("UPDATE users SET recovery_codes = ? WHERE id = ?", (hashes, g.user["id"]))
    conn.commit()
    return render_template("admin/recovery_codes.html", codes=codes, first=False)


# ---------------------------------------------------------------- Verwaltung: Einstellungen
MAX_LOGO_BYTES = 5_000_000


@app.route("/admin/einstellungen", methods=["GET", "POST"])
@login_required("admin")
def admin_settings():
    errors = []
    values = dict(settings())
    if request.method == "POST":
        f = request.form
        for key, label, _default, kind, _help in SETTINGS:
            value = (f.get(key) or "").strip()
            value = value[:2000] if kind == "textarea" else " ".join(value.split())[:300]
            if kind == "url" and value and not re.fullmatch(r"https?://\S+", value):
                errors.append(f"{label}: bitte eine vollständige Adresse mit https:// angeben.")
            if kind == "color" and not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                errors.append(f"{label}: bitte eine Farbe im Format #RRGGBB angeben.")
            values[key] = value
        if not values["org_name"]:
            errors.append("Bitte den Namen der Organisation angeben.")
        if not values["app_name"]:
            errors.append("Bitte einen Namen für das System angeben.")

        new_logo = None
        upload = request.files.get("logo")
        if upload and upload.filename:
            raw = upload.read(MAX_LOGO_BYTES + 1)
            try:
                if len(raw) > MAX_LOGO_BYTES:
                    raise ValueError
                img = Image.open(io.BytesIO(raw))
                img.load()
                img = img.convert("RGBA")
                img.thumbnail((800, 800))
                out = io.BytesIO()
                img.save(out, format="PNG", optimize=True)
                new_logo = out.getvalue()
            except Exception:
                errors.append("Das Logo konnte nicht gelesen werden. Bitte PNG oder JPG bis 5 MB hochladen.")

        if not errors:
            conn = db()
            for key in (s[0] for s in SETTINGS):
                conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                             "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, values[key]))
            conn.commit()
            if new_logo:
                tmp = LOGO_PATH + ".tmp"
                with open(tmp, "wb") as fh:
                    fh.write(new_logo)
                os.replace(tmp, LOGO_PATH)
            elif f.get("remove_logo") and os.path.exists(LOGO_PATH):
                os.remove(LOGO_PATH)
            g.pop("settings", None)
            flash("Einstellungen gespeichert.", "success")
            return redirect(url_for("admin_settings"))
    return render_template("admin/settings.html", fields=SETTINGS, values=values, errors=errors,
                           has_logo=os.path.exists(LOGO_PATH)), (400 if errors else 200)


# ---------------------------------------------------------------- Sonstiges
@app.get("/favicon.ico")
def favicon():
    if os.path.exists(LOGO_PATH):
        return redirect(url_for("logo"), code=302)
    abort(404)


@app.get("/ueber")
def about():
    return render_template("about.html", changelog=CHANGELOG, project_url=PROJECT_URL,
                           commit=APP_COMMIT, commit_short=APP_COMMIT[:7])


@app.get("/healthz")
def healthz():
    return "ok"


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(_e):
    return render_template("404.html", forbidden=True), 403
