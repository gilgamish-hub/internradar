"""Settings for the internship portal.

Everything here can be overridden in a .env file next to this one (see
.env.example). The portal is designed to run with no .env at all: without
SMTP credentials digests are still built and shown on the dashboard, and the
email is written to data/outbox as an .html file you can open.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUTBOX = DATA / "outbox"
DB_PATH = DATA / "portal.db"
SECRET_FILE = DATA / "secret.key"


def _load_env() -> None:
    """Minimal .env reader - no dependency, ignores comments and blank lines."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_env()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _int(name: str, default: int) -> int:
    try:
        return int(_env(name) or default)
    except ValueError:
        return default


# --- web -------------------------------------------------------------------
# Hosting platforms (Render, Railway, Fly, Heroku) hand the app a port in $PORT
# and expect it on 0.0.0.0. On a laptop neither is set, and binding to
# 127.0.0.1 keeps the portal off the local network until someone asks for it.
_PLATFORM_PORT = _int("PORT", 0)
PORT = _PLATFORM_PORT or _int("PORTAL_PORT", 8700)
HOST = _env("PORTAL_HOST", "0.0.0.0" if _PLATFORM_PORT else "127.0.0.1")
# Used in emails so the links in a digest open the right dashboard.
BASE_URL = (_env("PORTAL_BASE_URL")
            or f"http://{'127.0.0.1' if HOST == '0.0.0.0' else HOST}:{PORT}")
BRAND = _env("PORTAL_BRAND", "InternRadar")

# Who gets the /admin page. A comma-separated list of email addresses: whoever
# enrolls with one of them is an operator, whenever they enrol. Leave it empty
# and the portal falls back to making the very first account the operator, so
# a fresh install is never locked out of its own admin page.
ADMIN_EMAILS = {e.strip().lower() for e in _env("ADMIN_EMAILS").split(",") if e.strip()}


def secret_key() -> str:
    """A stable session key, so logins survive a restart. Generated once."""
    if key := _env("PORTAL_SECRET"):
        return key
    DATA.mkdir(parents=True, exist_ok=True)
    if not SECRET_FILE.exists():
        SECRET_FILE.write_text(secrets.token_hex(32), encoding="utf-8")
    return SECRET_FILE.read_text(encoding="utf-8").strip()


# --- email -----------------------------------------------------------------
# Gmail: turn on 2-step verification, then create an App Password (16 chars)
# at myaccount.google.com/apppasswords and put it in SMTP_PASS.
SMTP_HOST = _env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = _int("SMTP_PORT", 587)
SMTP_USER = _env("SMTP_USER")
SMTP_PASS = _env("SMTP_PASS")
MAIL_FROM = _env("MAIL_FROM") or SMTP_USER or "internradar@localhost"
MAIL_FROM_NAME = _env("MAIL_FROM_NAME", BRAND)
EMAIL_ENABLED = bool(SMTP_USER and SMTP_PASS)

# --- scanning --------------------------------------------------------------
SITES = [s.strip() for s in _env("SCAN_SITES", "linkedin,naukri,indeed").split(",") if s.strip()]
# Where the portal looks. Outside India, set both of these and drop naukri from
# SCAN_SITES - it is an Indian board. cities.py is an Indian city list, so a
# student elsewhere should pick "Anywhere" until that table is replaced.
SCAN_COUNTRY = _env("SCAN_COUNTRY", "India")
SCAN_LOCATION = _env("SCAN_LOCATION", "India")
RESULTS_PER_QUERY = _int("SCAN_RESULTS_PER_QUERY", 20)
SCAN_DAYS = _int("SCAN_DAYS", 7)            # how far back postings may be
FIELD_TTL_HOURS = _int("SCAN_FIELD_TTL_HOURS", 8)   # don't re-scrape a field sooner
POSTING_TTL_DAYS = _int("POSTING_TTL_DAYS", 30)     # forget postings older than this
MIN_SCORE = _int("MIN_SCORE", 35)           # below this a posting is not a "match"
DEFAULT_MAX_ITEMS = _int("DEFAULT_MAX_ITEMS", 10)   # internships per digest
SCHEDULER_TICK_SECONDS = _int("SCHEDULER_TICK_SECONDS", 60)
# IST, so a student typing 08:00 gets it at 08:00 their time. Offset in minutes.
TZ_OFFSET_MINUTES = _int("TZ_OFFSET_MINUTES", 330)

DEMO_MODE = _env("DEMO_MODE", "0") == "1"   # seed sample postings, never scrape


def ensure_dirs() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)
