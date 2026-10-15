"""The part that makes the portal automatic.

One loop, one minute at a time:

  * refresh the pool for any field whose scrape has gone stale (at most once
    every FIELD_TTL_HOURS, and only for fields students are waiting on)
  * send every digest whose delivery time has arrived

It runs as a thread inside the web app by default, so `python app.py` is the
only command needed. Run this file directly instead if you would rather give
the worker its own process (or its own Windows scheduled task).
"""
from __future__ import annotations

import sys
import threading
import time
import traceback

import config
import db
import digest
import scraper
import utils

_thread: threading.Thread | None = None
_stop = threading.Event()
LAST_TICK: dict = {"at": None, "scanned": [], "sent": [], "error": ""}


def tick() -> dict:
    """One pass. Never raises: a scheduler that dies on a bad posting is worse
    than one that logs and carries on."""
    result = {"at": utils.iso(utils.utcnow()), "scanned": [], "sent": [], "error": ""}
    try:
        due_fields = scraper.fields_due()
        if due_fields:
            scraper.log(f"[scheduler] pool is stale for {len(due_fields)} field(s)")
            result["scanned"] = scraper.scan_all()
        outcomes = digest.run_due()
        result["sent"] = outcomes
        for outcome in outcomes:
            scraper.log(f"[scheduler] digest -> user {outcome['user_id']}: "
                        f"{outcome['count']} items via {outcome.get('channel')} ({outcome['detail']})")
    except Exception:
        result["error"] = traceback.format_exc(limit=3)
        scraper.log("[scheduler] " + result["error"])
    LAST_TICK.update(result)
    return result


def loop(tick_seconds: int | None = None) -> None:
    tick_seconds = tick_seconds or config.SCHEDULER_TICK_SECONDS
    db.migrate()
    backfill_due_times()
    scraper.log(f"[scheduler] running, checking every {tick_seconds}s")
    while not _stop.is_set():
        tick()
        _stop.wait(tick_seconds)


def start_thread() -> threading.Thread:
    """Start the loop in the background, once per process."""
    global _thread
    if _thread and _thread.is_alive():
        return _thread
    _thread = threading.Thread(target=loop, name="internradar-scheduler", daemon=True)
    _thread.start()
    return _thread


def stop() -> None:
    _stop.set()


def backfill_due_times() -> int:
    """Give a schedule to anyone who somehow has none (an interrupted signup,
    or a row restored from a backup), so nobody silently never hears from us."""
    with db.session() as conn:
        rows = db.all_rows(conn, "SELECT * FROM profiles WHERE next_due_at IS NULL OR next_due_at = ''")
        for row in rows:
            upcoming = utils.next_due(row["deliver_time"], row["frequency"],
                                      int(row["tz_offset"] or 330),
                                      last_sent=utils.parse_iso(row["last_sent_at"]))
            conn.execute("UPDATE profiles SET next_due_at = ? WHERE user_id = ?",
                         (utils.iso(upcoming), row["user_id"]))
    return len(rows)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--once" in sys.argv:
        db.migrate()
        backfill_due_times()
        print(tick())
    else:
        try:
            loop()
        except KeyboardInterrupt:
            print("\nstopped")
