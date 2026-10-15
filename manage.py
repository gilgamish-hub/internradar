"""Operator commands, for whoever is running this portal.

    python manage.py stats                     what is in the database
    python manage.py users                     list the accounts
    python manage.py admin <email>             make someone an operator
    python manage.py unadmin <email>           take it away
    python manage.py delete-user <email>       remove one account and its data
    python manage.py reset-users               remove ALL accounts, keep the pool
    python manage.py reset-all                 empty the database completely
    python manage.py send <email>              build and send a digest now
    python manage.py scan [field]              scrape now, without waiting

Anything destructive makes a timestamped copy of the database first and asks
you to type "yes", unless you pass --force.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import config
import db
import fields
import utils


def backup() -> Path | None:
    """A copy beside the database, named for the moment it was taken."""
    if not config.DB_PATH.exists():
        return None
    stamp = utils.utcnow().strftime("%Y%m%d-%H%M%S")
    target = config.DB_PATH.with_name(f"{config.DB_PATH.stem}.backup-{stamp}.db")
    shutil.copyfile(config.DB_PATH, target)
    print(f"  database copied to {target.name} first")
    return target


def confirm(question: str) -> bool:
    if "--force" in sys.argv:
        return True
    try:
        return input(f"{question} Type yes to go ahead: ").strip().lower() == "yes"
    except EOFError:
        return False


def cmd_stats() -> None:
    with db.session() as conn:
        counts = {name: db.one(conn, f"SELECT COUNT(*) AS n FROM {name}")["n"]
                  for name in ("users", "profiles", "postings", "matches", "digests")}
        scans = db.all_rows(conn, "SELECT * FROM field_scans ORDER BY last_scan_at DESC")
    print(f"\n  database  {config.DB_PATH}")
    for name, count in counts.items():
        print(f"  {name:10} {count}")
    print(f"\n  email     {'on, via ' + config.SMTP_USER if config.EMAIL_ENABLED else 'off (digests go to data/outbox)'}")
    print(f"  admins    {', '.join(sorted(config.ADMIN_EMAILS)) or 'not set - the first account created is the operator'}")
    if scans:
        print("\n  field pools:")
        for row in scans:
            print(f"    {fields.label(row['field']):42} {row['kept']:4} kept   "
                  f"{utils.ago(utils.parse_iso(row['last_scan_at']))}")


def cmd_users() -> None:
    with db.session() as conn:
        rows = db.all_rows(conn, """
            SELECT u.id, u.email, u.name, u.is_admin, p.field, p.deliver_time, p.frequency,
                   p.paused, p.next_due_at,
                   (SELECT COUNT(*) FROM matches m WHERE m.user_id = u.id) AS matches
              FROM users u LEFT JOIN profiles p ON p.user_id = u.id ORDER BY u.id""")
    if not rows:
        print("\n  nobody has enrolled yet.")
        return
    print(f"\n  {'id':>3}  {'email':34} {'field':24} {'when':14} {'matches':>7}")
    for row in rows:
        when = f"{row['deliver_time'] or '-'} {row['frequency'] or ''}".strip()
        flags = " [operator]" if row["is_admin"] else ""
        flags += " [paused]" if row["paused"] else ""
        print(f"  {row['id']:>3}  {row['email'][:34]:34} "
              f"{fields.label(row['field'])[:24] if row['field'] else '-':24} "
              f"{when[:14]:14} {row['matches']:>7}{flags}")


def set_admin(email: str, value: int) -> None:
    with db.session() as conn:
        user = db.user_by_email(conn, email)
        if not user:
            sys.exit(f"  no account with {email}")
        conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (value, user["id"]))
    print(f"  {email} is {'now an operator' if value else 'no longer an operator'}")
    if value and config.ADMIN_EMAILS and email.lower() not in config.ADMIN_EMAILS:
        print("  note: ADMIN_EMAILS is set in .env and does not list this address, so a\n"
              "        fresh enrolment with it would not be an operator. Add it there too.")


def cmd_delete_user(email: str) -> None:
    with db.session() as conn:
        user = db.user_by_email(conn, email)
        if not user:
            sys.exit(f"  no account with {email}")
    if not confirm(f"\n  Delete {email} and everything belonging to it?"):
        return print("  left alone")
    backup()
    with db.session() as conn:
        conn.execute("DELETE FROM users WHERE email = ?", (email.strip().lower(),))
    print(f"  {email} deleted")


def cmd_reset_users() -> None:
    with db.session() as conn:
        count = db.one(conn, "SELECT COUNT(*) AS n FROM users")["n"]
    if not count:
        return print("  there are no accounts to remove.")
    if not confirm(f"\n  Remove all {count} account(s)? The pool of internships is kept."):
        return print("  left alone")
    backup()
    with db.session() as conn:
        conn.execute("DELETE FROM users")       # profiles, matches, digests cascade
    print(f"  {count} account(s) removed. The internship pool and the scan history are intact,\n"
          "  so the next person to enrol gets matched straight away.")


def cmd_reset_all() -> None:
    if not confirm("\n  Empty the entire database - accounts, pool, history?"):
        return print("  left alone")
    backup()
    with db.session() as conn:
        for table in ("digests", "matches", "profiles", "users", "postings", "field_scans"):
            conn.execute(f"DELETE FROM {table}")
    print("  database emptied. It is now exactly as a fresh install.")


def cmd_send(email: str) -> None:
    import digest
    with db.session() as conn:
        user = db.user_by_email(conn, email)
    if not user:
        sys.exit(f"  no account with {email}")
    outcome = digest.send_for_user(user["id"], force=True, reschedule=False)
    print(f"  {outcome['count']} internship(s) via {outcome.get('channel')}: {outcome['detail']}")


def cmd_scan(field: str | None) -> None:
    import scraper
    if field and field not in fields.FIELDS:
        sys.exit(f"  unknown field '{field}'. Known: {', '.join(sorted(fields.FIELDS))}")
    if field:
        scraper.scan_field(field)
    else:
        scraper.scan_all(force=True)


COMMANDS = {
    "stats": (cmd_stats, 0), "users": (cmd_users, 0),
    "admin": (lambda e: set_admin(e, 1), 1), "unadmin": (lambda e: set_admin(e, 0), 1),
    "delete-user": (cmd_delete_user, 1), "reset-users": (cmd_reset_users, 0),
    "reset-all": (cmd_reset_all, 0), "send": (cmd_send, 1), "scan": (cmd_scan, -1),
}


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args or args[0] not in COMMANDS:
        print(__doc__)
        return
    db.migrate()
    action, needs = COMMANDS[args[0]]
    if needs == 1:
        if len(args) < 2:
            sys.exit(f"  {args[0]} needs an email address")
        action(args[1])
    elif needs == -1:
        action(args[1] if len(args) > 1 else None)
    else:
        action()


if __name__ == "__main__":
    main()
