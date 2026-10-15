"""SQLite storage for the portal: students, their preferences, the shared
pool of scraped internships, and what has already been sent to whom.

One connection per request/worker (sqlite3 objects are not thread-safe), opened
through connect(). Schema changes are applied by migrate() on every start, so
the file upgrades itself.

Times are stored as UTC ISO strings. A student picks a delivery time in their
own clock, so every comparison goes through utils.local_now / utils.to_utc.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    is_admin      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id       INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    field         TEXT NOT NULL DEFAULT '',
    skills_json   TEXT NOT NULL DEFAULT '[]',
    cities_json   TEXT NOT NULL DEFAULT '[]',
    remote_ok     INTEGER NOT NULL DEFAULT 1,
    min_stipend   INTEGER NOT NULL DEFAULT 0,
    allow_unpaid  INTEGER NOT NULL DEFAULT 0,
    college       TEXT NOT NULL DEFAULT '',
    grad_year     TEXT NOT NULL DEFAULT '',
    phone         TEXT NOT NULL DEFAULT '',
    linkedin      TEXT NOT NULL DEFAULT '',
    resume_link   TEXT NOT NULL DEFAULT '',
    deliver_time  TEXT NOT NULL DEFAULT '09:00',
    frequency     TEXT NOT NULL DEFAULT 'daily',
    tz_offset     INTEGER NOT NULL DEFAULT 330,
    max_items     INTEGER NOT NULL DEFAULT 10,
    email_on      INTEGER NOT NULL DEFAULT 1,
    paused        INTEGER NOT NULL DEFAULT 0,
    last_sent_at  TEXT,
    next_due_at   TEXT,
    updated_at    TEXT NOT NULL DEFAULT ''
);

-- The shared pool. One row per real opening, keyed by company+title so the
-- same internship re-posted with a fresh URL does not become a second row.
CREATE TABLE IF NOT EXISTS postings (
    key          TEXT PRIMARY KEY,
    title        TEXT NOT NULL DEFAULT '',
    company      TEXT NOT NULL DEFAULT '',
    location     TEXT NOT NULL DEFAULT '',
    city_label   TEXT NOT NULL DEFAULT '',
    is_remote    INTEGER NOT NULL DEFAULT 0,
    is_intern    INTEGER NOT NULL DEFAULT 1,
    stipend_min  REAL,
    stipend_max  REAL,
    pay_interval TEXT NOT NULL DEFAULT '',
    pay_label    TEXT NOT NULL DEFAULT '',
    source       TEXT NOT NULL DEFAULT '',
    link         TEXT NOT NULL DEFAULT '',
    posted       TEXT NOT NULL DEFAULT '',
    description  TEXT NOT NULL DEFAULT '',
    found_for    TEXT NOT NULL DEFAULT '',   -- comma-separated field keys
    first_seen   TEXT NOT NULL DEFAULT '',
    last_seen    TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_postings_seen ON postings(last_seen);

-- One row per (student, internship) the matcher approved. sent_at is set when
-- it goes out in a digest, which is also what stops it being sent twice.
CREATE TABLE IF NOT EXISTS matches (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    posting_key  TEXT NOT NULL REFERENCES postings(key) ON DELETE CASCADE,
    score        INTEGER NOT NULL DEFAULT 0,
    fit          TEXT NOT NULL DEFAULT '',
    reasons_json TEXT NOT NULL DEFAULT '[]',
    status       TEXT NOT NULL DEFAULT 'new',   -- new | saved | applied | hidden
    created_at   TEXT NOT NULL DEFAULT '',
    sent_at      TEXT,
    UNIQUE(user_id, posting_key)
);
CREATE INDEX IF NOT EXISTS idx_matches_user ON matches(user_id, score DESC);

CREATE TABLE IF NOT EXISTS digests (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    item_count INTEGER NOT NULL DEFAULT 0,
    channel    TEXT NOT NULL DEFAULT '',      -- email | outbox | none
    ok         INTEGER NOT NULL DEFAULT 1,
    detail     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_digests_user ON digests(user_id, created_at DESC);

-- When each field was last scraped, so N students in one field cause one scrape.
CREATE TABLE IF NOT EXISTS field_scans (
    field        TEXT PRIMARY KEY,
    last_scan_at TEXT NOT NULL DEFAULT '',
    scraped      INTEGER NOT NULL DEFAULT 0,
    kept         INTEGER NOT NULL DEFAULT 0,
    detail       TEXT NOT NULL DEFAULT ''
);
"""


def connect() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")   # the scanner writes while you browse
    return conn


@contextmanager
def session() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def migrate() -> None:
    with session() as conn:
        conn.executescript(SCHEMA)


# --- small helpers ---------------------------------------------------------

def jload(raw: Any, default: Any = None) -> Any:
    try:
        return json.loads(raw) if raw else (default if default is not None else [])
    except (TypeError, ValueError):
        return default if default is not None else []


def jdump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def one(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> sqlite3.Row | None:
    return conn.execute(sql, args).fetchone()


def all_rows(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
    return conn.execute(sql, args).fetchall()


def user_by_email(conn: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return one(conn, "SELECT * FROM users WHERE email = ?", (email.strip().lower(),))


def profile(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return one(conn, "SELECT * FROM profiles WHERE user_id = ?", (user_id,))


def active_fields(conn: sqlite3.Connection) -> list[str]:
    """Fields at least one un-paused student is waiting on - the only ones
    worth spending a scrape on."""
    rows = all_rows(conn, "SELECT DISTINCT field FROM profiles WHERE paused = 0 AND field <> ''")
    return [r["field"] for r in rows]
