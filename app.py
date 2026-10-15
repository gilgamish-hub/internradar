"""The portal: enrol, say what you want, and the internships arrive by
themselves at the time you picked.

Run it with:  .venv\\Scripts\\python app.py
Then open:    http://127.0.0.1:8700

The scheduler (the part that scrapes and emails) starts in a background thread
unless NO_SCHEDULER=1 is set, so this one command is the whole portal.
"""
from __future__ import annotations

import functools
import os
import sys
import threading

from flask import (Flask, flash, redirect, render_template, request, session, url_for)

import cities
import config
import db
import digest
import fields
import mailer
import scheduler
import scraper
import utils

app = Flask(__name__)
app.secret_key = config.secret_key()
app.config.update(
    # Lax is what stops another site POSTing to these forms with the student's
    # cookie attached, which is this app's CSRF defence.
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=config.BASE_URL.startswith("https://"),
    MAX_CONTENT_LENGTH=256 * 1024,
)
app.jinja_env.globals.update(
    brand=config.BRAND, fields=fields, cities=cities, utils=utils,
    frequencies=utils.FREQUENCIES, email_enabled=config.EMAIL_ENABLED,
    # The skills picker is rebuilt in the browser when the field changes, so
    # the whole table goes to the page once instead of a round trip per change.
    skills_by_field={key: sorted(fields.skills_for(key)) for key in fields.FIELDS},
)


# --- plumbing --------------------------------------------------------------

def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with db.session() as conn:
        return db.one(conn, "SELECT * FROM users WHERE id = ?", (user_id,))


def login_required(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please sign in first.", "warn")
            return redirect(url_for("login", next=request.path))
        return view(user, *args, **kwargs)
    return wrapper


@app.context_processor
def inject_user():
    return {"user": current_user()}


def form_profile(defaults: dict | None = None) -> tuple[dict, list[str]]:
    """Read the preference part of a form. -> (values, errors).

    Used by both signup and settings so the two can never drift apart.
    """
    defaults = defaults or {}
    form = request.form
    errors: list[str] = []

    field = (form.get("field") or defaults.get("field") or "").strip()
    if field not in fields.FIELDS:
        errors.append("Pick the field you want internships in.")

    chosen_cities = form.getlist("cities") or defaults.get("cities") or []
    if cities.ANYWHERE in chosen_cities:
        chosen_cities = [cities.ANYWHERE]        # "anywhere" makes the rest noise
    if not chosen_cities:
        errors.append("Pick at least one city, or 'Anywhere in India'.")

    skills = [s for s in form.getlist("skills") if s][:40]

    try:
        min_stipend = max(0, int(form.get("min_stipend") or 0))
    except ValueError:
        min_stipend = 0
        errors.append("Minimum stipend must be a number.")

    deliver_time = form.get("deliver_time") or "09:00"
    hour, minute = utils.parse_hhmm(deliver_time, (-1, -1))
    if hour < 0:
        errors.append("Delivery time must look like 09:00.")
        deliver_time = "09:00"

    frequency = form.get("frequency") or "daily"
    if frequency not in utils.FREQUENCIES:
        frequency = "daily"

    # The browser tells us the student's own offset, so "deliver at 09:00"
    # means nine in the morning where they are, not where the server is.
    try:
        tz_offset = int(form.get("tz_offset"))
        if not -840 <= tz_offset <= 840:
            raise ValueError
    except (TypeError, ValueError):
        tz_offset = int(defaults.get("tz_offset") or config.TZ_OFFSET_MINUTES)

    try:
        max_items = min(25, max(3, int(form.get("max_items") or config.DEFAULT_MAX_ITEMS)))
    except ValueError:
        max_items = config.DEFAULT_MAX_ITEMS

    return {
        "field": field, "skills": skills, "cities": chosen_cities,
        "min_stipend": min_stipend, "allow_unpaid": 1 if form.get("allow_unpaid") else 0,
        "remote_ok": 1 if form.get("remote_ok") else 0,
        "deliver_time": f"{hour:02d}:{minute:02d}" if hour >= 0 else deliver_time,
        "frequency": frequency, "max_items": max_items,
        "email_on": 1 if form.get("email_on") else 0,
        "college": (form.get("college") or "").strip()[:120],
        "grad_year": (form.get("grad_year") or "").strip()[:12],
        "phone": (form.get("phone") or "").strip()[:20],
        "linkedin": (form.get("linkedin") or "").strip()[:200],
        "resume_link": (form.get("resume_link") or "").strip()[:300],
        "tz_offset": tz_offset,
    }, errors


def save_profile(conn, user_id: int, values: dict, *, paused: int | None = None) -> None:
    upcoming = utils.next_due(values["deliver_time"], values["frequency"], values["tz_offset"])
    row = db.profile(conn, user_id)
    paused_value = row["paused"] if (paused is None and row) else (paused or 0)
    conn.execute("""
        INSERT INTO profiles (user_id, field, skills_json, cities_json, remote_ok, min_stipend,
                              allow_unpaid, college, grad_year, phone, linkedin, resume_link,
                              deliver_time, frequency, tz_offset, max_items, email_on, paused,
                              next_due_at, updated_at)
        VALUES (:user_id, :field, :skills_json, :cities_json, :remote_ok, :min_stipend,
                :allow_unpaid, :college, :grad_year, :phone, :linkedin, :resume_link,
                :deliver_time, :frequency, :tz_offset, :max_items, :email_on, :paused,
                :next_due_at, :updated_at)
        ON CONFLICT(user_id) DO UPDATE SET
            field = :field, skills_json = :skills_json, cities_json = :cities_json,
            remote_ok = :remote_ok, min_stipend = :min_stipend, allow_unpaid = :allow_unpaid,
            college = :college, grad_year = :grad_year, phone = :phone, linkedin = :linkedin,
            resume_link = :resume_link, deliver_time = :deliver_time, frequency = :frequency,
            tz_offset = :tz_offset, max_items = :max_items, email_on = :email_on,
            paused = :paused, next_due_at = :next_due_at, updated_at = :updated_at
    """, {**values, "user_id": user_id, "skills_json": db.jdump(values["skills"]),
          "cities_json": db.jdump(values["cities"]), "paused": paused_value,
          "next_due_at": utils.iso(upcoming), "updated_at": utils.iso(utils.utcnow())})


# --- public pages ----------------------------------------------------------

@app.get("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    with db.session() as conn:
        pool = db.one(conn, "SELECT COUNT(*) AS n FROM postings")["n"]
        students = db.one(conn, "SELECT COUNT(*) AS n FROM users")["n"]
    return render_template("index.html", pool=pool, students=students,
                           field_choices=fields.field_choices())


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", values={}, city_choices=cities.choices(),
                               field_choices=fields.field_choices(), errors=[])

    name = (request.form.get("name") or "").strip()[:80]
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    values, errors = form_profile()
    if not name:
        errors.insert(0, "Your name, please.")
    if not utils.valid_email(email):
        errors.insert(0, "That email address does not look right.")
    if len(password) < 8:
        errors.insert(0, "Use a password of at least 8 characters.")

    with db.session() as conn:
        if db.user_by_email(conn, email):
            errors.insert(0, "Someone has already enrolled with that email. Sign in instead.")
        if errors:
            return render_template("signup.html", values={**values, "name": name, "email": email},
                                   city_choices=cities.choices(),
                                   field_choices=fields.field_choices(), errors=errors), 400
        # Operators are whoever is listed in ADMIN_EMAILS. With no list set,
        # the first account to be created takes the role, so a fresh install
        # can always reach its own admin page.
        if config.ADMIN_EMAILS:
            is_admin = email in config.ADMIN_EMAILS
        else:
            is_admin = db.one(conn, "SELECT COUNT(*) AS n FROM users")["n"] == 0
        cur = conn.execute("""INSERT INTO users (email, name, password_hash, created_at, is_admin)
                              VALUES (?, ?, ?, ?, ?)""",
                           (email, name, utils.hash_password(password),
                            utils.iso(utils.utcnow()), int(is_admin)))
        user_id = cur.lastrowid
        save_profile(conn, user_id, values, paused=0)
        # Score whatever is already pooled, so the dashboard is never empty on
        # arrival when another student in the same field has already pulled one.
        digest.refresh_matches(conn, user_id, {**values, "skills": values["skills"],
                                               "cities": values["cities"]})

    session["user_id"] = user_id
    flash("You are enrolled. Your first digest is scheduled - you can also send one now.", "ok")
    return redirect(url_for("dashboard"))


# Failed sign-ins per IP. In memory on purpose: it costs nothing, it clears on
# restart, and it is enough to make guessing a password by brute force useless
# on a portal this size.
_FAILED_LOGINS: dict[str, list] = {}
LOGIN_LIMIT = 8
LOGIN_WINDOW_SECONDS = 600


def _login_blocked(ip: str) -> bool:
    cutoff = utils.utcnow().timestamp() - LOGIN_WINDOW_SECONDS
    attempts = [t for t in _FAILED_LOGINS.get(ip, []) if t > cutoff]
    _FAILED_LOGINS[ip] = attempts
    return len(attempts) >= LOGIN_LIMIT


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    ip = request.remote_addr or "?"
    if _login_blocked(ip):
        flash("Too many failed attempts. Wait ten minutes and try again.", "warn")
        return render_template("login.html"), 429
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    with db.session() as conn:
        user = db.user_by_email(conn, email)
    if not user or not utils.check_password(password, user["password_hash"]):
        _FAILED_LOGINS.setdefault(ip, []).append(utils.utcnow().timestamp())
        flash("Wrong email or password.", "warn")
        return render_template("login.html", email=email), 401
    _FAILED_LOGINS.pop(ip, None)
    session["user_id"] = user["id"]
    # Only ever redirect inside this site: an open redirect here would let a
    # phishing link bounce a signed-in student somewhere else.
    target = request.args.get("next") or ""
    return redirect(target if target.startswith("/") and not target.startswith("//")
                    else url_for("dashboard"))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# --- the student's own pages ----------------------------------------------

@app.get("/dashboard")
@login_required
def dashboard(user):
    status = request.args.get("status", "inbox")
    with db.session() as conn:
        row = db.profile(conn, user["id"])
        if not row:
            return redirect(url_for("settings"))
        profile = digest.profile_dict(row)
        # Pick up anything scraped since the last digest, so the inbox is live
        # rather than only as fresh as the last email.
        digest.refresh_matches(conn, user["id"], profile)

        where = {"inbox": "m.status = 'new'", "saved": "m.status = 'saved'",
                 "applied": "m.status = 'applied'", "hidden": "m.status = 'hidden'",
                 "all": "1=1"}.get(status, "m.status = 'new'")
        rows = db.all_rows(conn, f"""
            SELECT m.id, m.score, m.fit, m.reasons_json, m.status, m.sent_at, p.*
              FROM matches m JOIN postings p ON p.key = m.posting_key
             WHERE m.user_id = ? AND {where}
             ORDER BY m.score DESC, p.last_seen DESC LIMIT 200""", (user["id"],))
        items = []
        for match in rows:
            data = dict(match)
            data["reasons"] = db.jload(match["reasons_json"], {"good": [], "warn": []})
            data["sent_ago"] = utils.ago(utils.parse_iso(match["sent_at"]))
            items.append(data)

        counts = {name: db.one(conn, "SELECT COUNT(*) AS n FROM matches WHERE user_id = ? AND status = ?",
                               (user["id"], name))["n"] for name in ("new", "saved", "applied", "hidden")}
        waiting = db.one(conn, """SELECT COUNT(*) AS n FROM matches
                                   WHERE user_id = ? AND sent_at IS NULL AND status <> 'hidden'""",
                         (user["id"],))["n"]
        scan = db.one(conn, "SELECT * FROM field_scans WHERE field = ?", (profile["field"],))
        last_digest = db.one(conn, """SELECT * FROM digests WHERE user_id = ?
                                       ORDER BY created_at DESC LIMIT 1""", (user["id"],))
        pool_size = db.one(conn, "SELECT COUNT(*) AS n FROM postings WHERE (',' || found_for || ',') LIKE ?",
                           (f"%,{profile['field']},%",))["n"]

    return render_template(
        "dashboard.html", profile=profile, items=items, counts=counts, status=status,
        waiting=waiting, pool_size=pool_size,
        first_scan_pending=scan is None,
        next_due=utils.parse_iso(row["next_due_at"]),
        last_digest=last_digest,
        last_scan=utils.parse_iso(scan["last_scan_at"]) if scan else None,
    )


@app.post("/match/<int:match_id>/<action>")
@login_required
def mark(user, match_id: int, action: str):
    allowed = {"save": "saved", "apply": "applied", "hide": "hidden", "reset": "new"}
    if action not in allowed:
        flash("Unknown action.", "warn")
        return redirect(url_for("dashboard"))
    with db.session() as conn:
        conn.execute("UPDATE matches SET status = ? WHERE id = ? AND user_id = ?",
                     (allowed[action], match_id, user["id"]))
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings(user):
    with db.session() as conn:
        row = db.profile(conn, user["id"])
    current = digest.profile_dict(row) if row else {}

    if request.method == "POST":
        values, errors = form_profile(current)
        if errors:
            return render_template("settings.html", values={**current, **values}, errors=errors,
                                   city_choices=cities.choices(),
                                   field_choices=fields.field_choices()), 400
        with db.session() as conn:
            save_profile(conn, user["id"], values)
        flash("Saved. Your next digest follows the new schedule.", "ok")
        return redirect(url_for("settings"))

    return render_template("settings.html", values=current, errors=[],
                           city_choices=cities.choices(), field_choices=fields.field_choices(),
                           next_due=utils.parse_iso(row["next_due_at"]) if row else None)


@app.post("/settings/pause")
@login_required
def toggle_pause(user):
    with db.session() as conn:
        row = db.profile(conn, user["id"])
        new_value = 0 if row and row["paused"] else 1
        conn.execute("UPDATE profiles SET paused = ? WHERE user_id = ?", (new_value, user["id"]))
    flash("Digests paused." if new_value else "Digests resumed.", "ok")
    return redirect(url_for("settings"))


@app.post("/send-now")
@login_required
def send_now(user):
    # force: ignore the schedule. reschedule=False: a manual send must not push
    # the student's real delivery time to tomorrow.
    outcome = digest.send_for_user(user["id"], force=True, reschedule=False)
    if outcome["count"] == 0:
        flash("Nothing new to send yet - the next scan will fill it up.", "warn")
    elif outcome["channel"] == "email":
        flash(f"Sent {outcome['count']} internships to {user['email']}.", "ok")
    else:
        flash(f"{outcome['count']} internships are on your dashboard. {outcome['detail']}", "warn")
    return redirect(url_for("dashboard"))


@app.get("/digests")
@login_required
def digest_history(user):
    with db.session() as conn:
        rows = db.all_rows(conn, """SELECT * FROM digests WHERE user_id = ?
                                     ORDER BY created_at DESC LIMIT 60""", (user["id"],))
    return render_template("digests.html", rows=rows)


@app.post("/account/delete")
@login_required
def delete_account(user):
    if (request.form.get("confirm") or "").strip().lower() != "delete":
        flash('Type "delete" to confirm.', "warn")
        return redirect(url_for("settings"))
    with db.session() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    session.clear()
    flash("Your account and everything in it is gone.", "ok")
    return redirect(url_for("index"))


# --- operator page ---------------------------------------------------------

@app.get("/admin")
@login_required
def admin(user):
    if not user["is_admin"]:
        flash("That page is for the operator.", "warn")
        return redirect(url_for("dashboard"))
    with db.session() as conn:
        pool = db.one(conn, "SELECT COUNT(*) AS n FROM postings")["n"]
        scans = db.all_rows(conn, "SELECT * FROM field_scans ORDER BY last_scan_at DESC")
        students = db.all_rows(conn, """
            SELECT u.id, u.email, u.name, p.field, p.deliver_time, p.frequency, p.paused,
                   p.next_due_at, p.last_sent_at,
                   (SELECT COUNT(*) FROM matches m WHERE m.user_id = u.id) AS matches
              FROM users u LEFT JOIN profiles p ON p.user_id = u.id ORDER BY u.id""")
        recent = db.all_rows(conn, """SELECT d.*, u.email FROM digests d JOIN users u ON u.id = d.user_id
                                       ORDER BY d.created_at DESC LIMIT 20""")
    return render_template("admin.html", pool=pool, scans=scans, students=students, recent=recent,
                           mail_status=session.pop("mail_status", ""), last_tick=scheduler.LAST_TICK,
                           due_fields=scraper.fields_due())


@app.post("/admin/scan")
@login_required
def admin_scan(user):
    if not user["is_admin"]:
        return redirect(url_for("dashboard"))
    threading.Thread(target=scraper.scan_all, kwargs={"force": True}, daemon=True).start()
    flash("Scan started in the background. It takes a few minutes per field - "
          "refresh this page to see it land.", "ok")
    return redirect(url_for("admin"))


@app.post("/admin/mailcheck")
@login_required
def admin_mailcheck(user):
    if not user["is_admin"]:
        return redirect(url_for("dashboard"))
    session["mail_status"] = mailer.check()
    return redirect(url_for("admin"))


@app.post("/admin/tick")
@login_required
def admin_tick(user):
    if not user["is_admin"]:
        return redirect(url_for("dashboard"))
    result = scheduler.tick()
    flash(f"Checked now: {len(result['sent'])} digest(s) were due.", "ok")
    return redirect(url_for("admin"))


@app.get("/healthz")
def healthz():
    """What a hosting platform pings to know the app is alive."""
    try:
        with db.session() as conn:
            pool = db.one(conn, "SELECT COUNT(*) AS n FROM postings")["n"]
            students = db.one(conn, "SELECT COUNT(*) AS n FROM users")["n"]
        return {"ok": True, "students": students, "pool": pool,
                "scheduler": bool(scheduler.LAST_TICK.get("at")),
                "last_tick": scheduler.LAST_TICK.get("at")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}, 500


# --- small filters ---------------------------------------------------------

@app.template_filter("when")
def when_filter(value, tz_offset=330):
    return utils.when_text(value, tz_offset)


@app.template_filter("short")
def short_filter(value, limit=200):
    return utils.shorten(value, limit)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:          # very old Python, or a redirected stream
        pass
    db.migrate()
    scheduler.backfill_due_times()
    if os.environ.get("NO_SCHEDULER") != "1":
        scheduler.start_thread()
        print("scheduler thread started (scrapes and sends digests)")
    print(f"\n  {config.BRAND} is running at {config.BASE_URL}\n")
    print(mailer.check())
    print("\nPress Ctrl+C to stop.\n")

    # waitress is a real WSGI server and ships as a wheel on every platform.
    # Flask's own server is the fallback: fine for one person on a laptop, not
    # for anything anyone else can reach.
    try:
        from waitress import serve
        serve(app, host=config.HOST, port=config.PORT, threads=8, ident=config.BRAND)
    except ImportError:
        print("(waitress is not installed - using the development server)")
        app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
