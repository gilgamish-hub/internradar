"""Building and sending one student's digest.

The flow for a student whose delivery time has arrived:

  1. score every pooled internship in their field they have not seen before
  2. keep the ones above MIN_SCORE as matches
  3. take the top N that have never been sent
  4. email them (or write the mail to data/outbox), and stamp them as sent

Step 4 is what stops repeats: a match carries sent_at, so tomorrow's digest
cannot contain today's internships even if they still score highest.
"""
from __future__ import annotations

import sys
from html import escape

import config
import db
import fields
import mailer
import matcher
import utils


def profile_dict(row) -> dict:
    """A profiles row with its JSON columns decoded, as the matcher wants it."""
    data = dict(row)
    data["skills"] = db.jload(row["skills_json"])
    data["cities"] = db.jload(row["cities_json"])
    return data


def refresh_matches(conn, user_id: int, profile: dict) -> int:
    """Score pooled internships this student has not been scored against yet."""
    field = profile.get("field") or ""
    if not field:
        return 0
    rows = db.all_rows(conn, """
        SELECT * FROM postings
         WHERE (',' || found_for || ',') LIKE ?
           AND key NOT IN (SELECT posting_key FROM matches WHERE user_id = ?)
         ORDER BY last_seen DESC LIMIT 600""", (f"%,{field},%", user_id))
    now = utils.iso(utils.utcnow())
    added = 0
    for row in rows:
        verdict = matcher.score(dict(row), profile)
        if not verdict or verdict["score"] < config.MIN_SCORE:
            continue
        conn.execute("""INSERT OR IGNORE INTO matches
                        (user_id, posting_key, score, fit, reasons_json, status, created_at)
                        VALUES (?, ?, ?, ?, ?, 'new', ?)""",
                     (user_id, row["key"], verdict["score"], verdict["fit"],
                      db.jdump({"good": verdict["reasons"], "warn": verdict["warnings"]}), now))
        added += 1
    return added


def pending_items(conn, user_id: int, limit: int) -> list[dict]:
    rows = db.all_rows(conn, """
        SELECT m.id, m.score, m.fit, m.reasons_json, p.*
          FROM matches m JOIN postings p ON p.key = m.posting_key
         WHERE m.user_id = ? AND m.sent_at IS NULL AND m.status <> 'hidden'
         ORDER BY m.score DESC, p.last_seen DESC LIMIT ?""", (user_id, limit))
    items = []
    for row in rows:
        data = dict(row)
        data["reasons"] = db.jload(row["reasons_json"], {"good": [], "warn": []})
        items.append(data)
    return items


# --- the email ------------------------------------------------------------
# Inline styles only: every mail client strips a <style> block sooner or later.

def _card(item: dict) -> str:
    good = item["reasons"].get("good", [])[:4]
    warn = item["reasons"].get("warn", [])[:2]
    chips = "".join(
        f'<span style="display:inline-block;background:#eef2ff;color:#3730a3;border-radius:999px;'
        f'padding:3px 10px;font-size:12px;margin:0 6px 6px 0">{escape(reason)}</span>'
        for reason in good)
    flags = "".join(
        f'<div style="color:#92400e;font-size:13px;margin-top:6px">&#9888; {escape(w)}</div>'
        for w in warn)
    return f"""
    <tr><td style="padding:0 0 14px 0">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border:1px solid #e5e7eb;border-radius:12px;background:#ffffff">
        <tr><td style="padding:16px 18px">
          <div style="font-size:12px;color:#6b7280;letter-spacing:.04em;text-transform:uppercase">
            {escape(item['fit'])} fit &middot; {item['score']}/100
          </div>
          <div style="font-size:17px;font-weight:700;color:#111827;margin:4px 0 2px">
            {escape(item['title'])}
          </div>
          <div style="font-size:14px;color:#374151;margin-bottom:10px">
            {escape(item['company'])} &middot; {escape(item['city_label'] or 'Location not stated')}
            &middot; {escape(item['pay_label'])}
          </div>
          <div>{chips}</div>
          {flags}
          <div style="margin-top:12px">
            <a href="{escape(item['link'])}"
               style="display:inline-block;background:#4338ca;color:#ffffff;text-decoration:none;
                      padding:9px 16px;border-radius:8px;font-size:14px;font-weight:600">
              Open the posting
            </a>
            <span style="font-size:12px;color:#9ca3af;margin-left:10px">
              via {escape(item['source'])}
            </span>
          </div>
        </td></tr>
      </table>
    </td></tr>"""


def build_html(user, profile: dict, items: list[dict]) -> str:
    name = (user["name"] or user["email"].split("@")[0]).split()[0]
    heading = (f"{len(items)} new internship{'s' if len(items) != 1 else ''} in "
               f"{fields.label(profile['field'])}")
    cards = "".join(_card(item) for item in items)
    dash = f"{config.BASE_URL}/dashboard"
    return f"""<!doctype html>
<html><body style="margin:0;padding:24px 12px;background:#f3f4f6;
                   font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;margin:0 auto">
    <tr><td style="padding-bottom:18px">
      <div style="font-size:13px;color:#6b7280">{escape(config.BRAND)}</div>
      <div style="font-size:22px;font-weight:800;color:#111827;margin-top:2px">
        Morning {escape(name)} &mdash; {escape(heading)}
      </div>
      <div style="font-size:14px;color:#6b7280;margin-top:6px">
        Picked for your field, your cities and a stipend floor of
        Rs {int(profile.get('min_stipend') or 0):,}/month.
      </div>
    </td></tr>
    {cards}
    <tr><td style="padding-top:8px;font-size:13px;color:#6b7280;line-height:1.6">
      <a href="{dash}" style="color:#4338ca">Open your dashboard</a> to mark these applied,
      or <a href="{config.BASE_URL}/settings" style="color:#4338ca">change your field,
      cities or delivery time</a>.<br>
      You are getting this because you enrolled at {escape(config.BRAND)}. Nothing here asks
      you for money - if a posting ever does, it is not a real internship.
    </td></tr>
  </table>
</body></html>"""


def build_text(profile: dict, items: list[dict]) -> str:
    lines = [f"{len(items)} new internships in {fields.label(profile['field'])}", ""]
    for item in items:
        lines += [f"{item['title']} - {item['company']}",
                  f"  {item['city_label'] or 'Location not stated'} | {item['pay_label']} "
                  f"| {item['fit']} fit {item['score']}/100",
                  f"  {item['link']}", ""]
    lines.append(f"Dashboard: {config.BASE_URL}/dashboard")
    return "\n".join(lines)


# --- sending --------------------------------------------------------------

def send_for_user(user_id: int, force: bool = False, reschedule: bool = True) -> dict:
    """Build and send one digest. force=True sends even outside the schedule."""
    with db.session() as conn:
        user = db.one(conn, "SELECT * FROM users WHERE id = ?", (user_id,))
        row = db.profile(conn, user_id)
        if not user or not row:
            return {"ok": False, "detail": "no such student", "count": 0}
        profile = profile_dict(row)
        if profile["paused"] and not force:
            return {"ok": True, "detail": "paused", "count": 0}

        refresh_matches(conn, user_id, profile)
        items = pending_items(conn, user_id, int(profile["max_items"] or config.DEFAULT_MAX_ITEMS))

    now = utils.utcnow()
    if not items:
        channel, ok, detail = "none", True, "nothing new scored above the threshold"
    elif not profile["email_on"]:
        channel, ok, detail = "none", True, "email off, digest waiting on the dashboard"
    else:
        subject = (f"{len(items)} new {fields.label(profile['field'])} internship"
                   f"{'s' if len(items) != 1 else ''} for you")
        channel, ok, detail = mailer.send(user["email"], subject,
                                         build_html(user, profile, items),
                                         build_text(profile, items))

    with db.session() as conn:
        # Items are stamped sent whenever they reached the student - including
        # when they are only waiting on the dashboard, so the list does not
        # repeat tomorrow.
        if items:
            conn.executemany("UPDATE matches SET sent_at = ? WHERE id = ?",
                             [(utils.iso(now), item["id"]) for item in items])
        conn.execute("""INSERT INTO digests (user_id, created_at, item_count, channel, ok, detail)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (user_id, utils.iso(now), len(items), channel, int(ok), detail))
        if reschedule:
            upcoming = utils.next_due(profile["deliver_time"], profile["frequency"],
                                      int(profile["tz_offset"] or 330), last_sent=now, after=now)
            conn.execute("UPDATE profiles SET last_sent_at = ?, next_due_at = ? WHERE user_id = ?",
                         (utils.iso(now), utils.iso(upcoming), user_id))
    return {"ok": ok, "detail": detail, "count": len(items), "channel": channel}


def due_users() -> list[int]:
    now = utils.iso(utils.utcnow())
    with db.session() as conn:
        rows = db.all_rows(conn, """SELECT user_id FROM profiles
                                     WHERE paused = 0 AND field <> ''
                                       AND next_due_at IS NOT NULL AND next_due_at <= ?""", (now,))
    return [r["user_id"] for r in rows]


def run_due() -> list[dict]:
    """Send every digest whose time has come. Called by the scheduler."""
    results = []
    for user_id in due_users():
        outcome = send_for_user(user_id)
        results.append({"user_id": user_id, **outcome})
    return results


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    db.migrate()
    args = sys.argv[1:]
    if email := next((a.split("=", 1)[1] for a in args if a.startswith("--email=")), None):
        with db.session() as conn:
            found = db.user_by_email(conn, email)
        if not found:
            print(f"no student enrolled with {email}")
            sys.exit(1)
        print(send_for_user(found["id"], force=True, reschedule="--reschedule" in args))
    else:
        outcomes = run_due()
        print(f"{len(outcomes)} digest(s) due")
        for outcome in outcomes:
            print(" ", outcome)
