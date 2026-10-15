"""Fill the shared pool of internships.

One scrape per field, not per student: if forty students have picked Web
Development they all read the same pool, so the boards see one set of requests
instead of forty. A field is only scraped when at least one un-paused student
is waiting on it, and not again until FIELD_TTL_HOURS have passed.

jobspy does the talking to LinkedIn / Naukri / Indeed. It is the one piece
here that touches the network, so every call is wrapped: one board refusing a
query must never end the scan.
"""
from __future__ import annotations

import re
import sys
import time
from datetime import timedelta

import cities
import config
import db
import fields
import matcher
import utils


def log(message: str) -> None:
    # Under Task Scheduler stdout is cp1252, and a title like "Nagpur" spelled
    # with a long vowel would otherwise raise UnicodeEncodeError and kill the
    # scan silently.
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        print(message.encode("ascii", "replace").decode(), flush=True)


def _scrape_one(site: str, query: str, location: str, days: int):
    from jobspy import scrape_jobs
    return scrape_jobs(
        site_name=[site], search_term=query, location=location,
        results_wanted=config.RESULTS_PER_QUERY, hours_old=days * 24,
        country_indeed=config.SCAN_COUNTRY, linkedin_fetch_description=True, verbose=0,
    )


def _row_to_posting(row, field: str) -> dict | None:
    """One scraped record -> a pool row, or None if it does not belong here."""
    title = utils.text(row.get("title"))
    company = utils.text(row.get("company"))
    if not title or not company:
        return None
    description = utils.text(row.get("description"))
    if not matcher.is_internship(title, description):
        return None            # the portal is for internships only
    if matcher.red_flags(description):
        return None            # asks for a fee - never goes in the pool
    is_remote = row.get("is_remote") is True or utils.text(row.get("is_remote")) == "True"
    location = utils.text(row.get("location"))
    _, city_label = cities.identify(location, is_remote)
    # The boards answer a query loosely: searching "AI intern" returns HR and
    # marketing internships too. Rather than throw those away, tag each posting
    # with every field its title actually fits, so the HR student sees the HR
    # internship that an AI search happened to surface.
    tags = sorted({field} | fields_matching_title(title))
    return {
        "key": utils.posting_key(company, title),
        "title": title, "company": company, "location": location,
        "city_label": city_label, "is_remote": int(is_remote), "is_intern": 1,
        "stipend_min": _num(row.get("min_amount")), "stipend_max": _num(row.get("max_amount")),
        "pay_interval": utils.text(row.get("interval")) or "monthly",
        "pay_label": matcher.pay_label(row.get("min_amount"), row.get("max_amount"),
                                       utils.text(row.get("interval"))),
        "source": utils.text(row.get("site")), "link": utils.text(row.get("job_url")),
        "posted": utils.text(row.get("date_posted"))[:10],
        "description": description, "found_for": ",".join(tags),
    }


def fields_matching_title(title: str) -> set[str]:
    """Every field whose own title pattern the posting's title satisfies."""
    low = (title or "").lower()
    return {key for key, spec in fields.FIELDS.items() if re.search(spec["titles"], low)}


def _num(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f != f or f <= 0 else f


UPSERT = """
INSERT INTO postings (key, title, company, location, city_label, is_remote, is_intern,
                      stipend_min, stipend_max, pay_interval, pay_label, source, link,
                      posted, description, found_for, first_seen, last_seen)
VALUES (:key, :title, :company, :location, :city_label, :is_remote, :is_intern,
        :stipend_min, :stipend_max, :pay_interval, :pay_label, :source, :link,
        :posted, :description, :found_for, :now, :now)
ON CONFLICT(key) DO UPDATE SET
    last_seen    = :now,
    -- Boards sometimes hand back a truncated description. Keeping the longest
    -- one ever seen stops a posting silently losing its skill matches, and its
    -- score, between scans.
    description  = CASE WHEN length(excluded.description) > length(postings.description)
                        THEN excluded.description ELSE postings.description END,
    stipend_min  = COALESCE(postings.stipend_min, excluded.stipend_min),
    stipend_max  = COALESCE(postings.stipend_max, excluded.stipend_max),
    pay_label    = CASE WHEN postings.pay_label = 'Stipend not stated'
                        THEN excluded.pay_label ELSE postings.pay_label END,
    link         = CASE WHEN postings.link = '' THEN excluded.link ELSE postings.link END,
    city_label   = CASE WHEN postings.city_label IN ('', 'City not stated')
                        THEN excluded.city_label ELSE postings.city_label END,
    found_for    = :found_for,
    source       = :source
"""


def _merge_lists(old: str, new: str, joiner: str = ",") -> str:
    """Union of two comma lists, order kept stable so the rows stay readable."""
    seen, out = set(), []
    for item in f"{old or ''},{new or ''}".split(","):
        clean = item.strip()
        if clean and clean not in seen:
            seen.add(clean)
            out.append(clean)
    return joiner.join(out)


def save_postings(rows: list[dict]) -> int:
    """-> how many of them the pool had never seen before.

    The field tags and the source list are merged here rather than in SQL,
    because a posting can arrive carrying several field tags at once and the
    union of two comma lists is not something SQLite expresses well.
    """
    if not rows:
        return 0
    now = utils.iso(utils.utcnow())
    added = 0
    with db.session() as conn:
        for row in rows:
            existing = db.one(conn, "SELECT found_for, source FROM postings WHERE key = ?",
                              (row["key"],))
            if existing is None:
                added += 1
            conn.execute(UPSERT, {
                **row, "now": now,
                "found_for": _merge_lists(existing["found_for"] if existing else "",
                                          row["found_for"]),
                "source": _merge_lists(existing["source"] if existing else "",
                                       row["source"], joiner=", "),
            })
    return added


def scan_field(field: str, locations: list[str] | None = None,
               days: int | None = None) -> dict:
    """Scrape one field across every configured board and query."""
    spec = fields.FIELDS.get(field)
    if not spec:
        return {"field": field, "scraped": 0, "kept": 0, "detail": "unknown field"}
    locations = locations or [config.SCAN_LOCATION]
    days = days or config.SCAN_DAYS
    scraped, rows, problems = 0, {}, []

    for site in config.SITES:
        for query in spec["queries"]:
            for location in locations:
                try:
                    frame = _scrape_one(site, query, location, days)
                except Exception as exc:        # one bad board must not kill the scan
                    problems.append(f"{site}/{query}: {str(exc)[:60]}")
                    continue
                count = 0 if frame is None else len(frame)
                scraped += count
                log(f"  {site:9} {query:32} {location:12} {count:3}")
                for _, record in (frame.iterrows() if count else []):
                    posting = _row_to_posting(record, field)
                    if posting:
                        # Within one scan the longest description wins too.
                        old = rows.get(posting["key"])
                        if not old or len(posting["description"]) > len(old["description"]):
                            rows[posting["key"]] = posting
                time.sleep(2)                   # be a polite scraper

    new_count = save_postings(list(rows.values()))
    detail = "; ".join(problems[:4])
    with db.session() as conn:
        conn.execute("""INSERT INTO field_scans (field, last_scan_at, scraped, kept, detail)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(field) DO UPDATE SET
                          last_scan_at = excluded.last_scan_at, scraped = excluded.scraped,
                          kept = excluded.kept, detail = excluded.detail""",
                     (field, utils.iso(utils.utcnow()), scraped, len(rows), detail))
    log(f"{fields.label(field)}: {scraped} postings seen, {len(rows)} internships kept, "
        f"{new_count} new to the pool")
    return {"field": field, "scraped": scraped, "kept": len(rows), "new": new_count, "detail": detail}


def fields_due(force: bool = False) -> list[str]:
    """Fields with a waiting student whose pool is stale."""
    now = utils.utcnow()
    with db.session() as conn:
        active = db.active_fields(conn)
        if force:
            return active
        scans = {r["field"]: utils.parse_iso(r["last_scan_at"])
                 for r in db.all_rows(conn, "SELECT field, last_scan_at FROM field_scans")}
    due = []
    for field in active:
        last = scans.get(field)
        if last is None or (now - last).total_seconds() >= config.FIELD_TTL_HOURS * 3600:
            due.append(field)
    return due


def locations_for(field: str) -> list[str]:
    """What to type into the boards' location box for this field.

    Searching "India" returns the whole country, which is right when the
    waiting students are spread out. When they all want one or two cities,
    naming those cities surfaces local postings the national search buries.
    """
    with db.session() as conn:
        rows = db.all_rows(conn, "SELECT cities_json FROM profiles WHERE paused = 0 AND field = ?",
                           (field,))
    wanted: set[str] = set()
    for row in rows:
        wanted.update(db.jload(row["cities_json"]))
    if not wanted or cities.ANYWHERE in wanted:
        return [config.SCAN_LOCATION]
    named = [c for c in wanted if c in cities.CITIES]
    return (cities.search_locations(sorted(named)) if 0 < len(named) <= 2
            else [config.SCAN_LOCATION])


def prune() -> int:
    """Drop postings nobody has seen in POSTING_TTL_DAYS. A student's own
    saved / applied rows keep their posting alive."""
    cutoff = utils.iso(utils.utcnow() - timedelta(days=config.POSTING_TTL_DAYS))
    with db.session() as conn:
        cur = conn.execute("""DELETE FROM postings WHERE last_seen < ? AND key NOT IN
                              (SELECT posting_key FROM matches
                               WHERE status IN ('saved','applied'))""", (cutoff,))
        return cur.rowcount


def scan_all(force: bool = False, locations: list[str] | None = None) -> list[dict]:
    db.migrate()
    if config.DEMO_MODE:
        import demo_data
        added = demo_data.seed()
        log(f"DEMO_MODE: seeded {added} sample internships, no boards were contacted")
        # Stamp the scan against every waiting field, or the TTL never starts
        # and the samples are re-seeded on every scheduler tick.
        with db.session() as conn:
            for field in db.active_fields(conn):
                conn.execute("""INSERT INTO field_scans (field, last_scan_at, scraped, kept, detail)
                                VALUES (?, ?, ?, ?, 'DEMO_MODE: sample data')
                                ON CONFLICT(field) DO UPDATE SET
                                  last_scan_at = excluded.last_scan_at,
                                  scraped = excluded.scraped, kept = excluded.kept,
                                  detail = excluded.detail""",
                             (field, utils.iso(utils.utcnow()), added, added))
        return [{"field": "demo", "scraped": added, "kept": added, "new": added, "detail": ""}]
    due = fields_due(force)
    if not due:
        log("no field is due for a scan (everything is fresh, or nobody has enrolled yet)")
        return []
    log(f"scanning {len(due)} field(s): {', '.join(fields.label(f) for f in due)}")
    results = [scan_field(field, locations or locations_for(field)) for field in due]
    dropped = prune()
    if dropped:
        log(f"pruned {dropped} postings older than {config.POSTING_TTL_DAYS} days")
    return results


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    force = "--force" in sys.argv
    only = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--field=")), None)
    db.migrate()
    if only:
        scan_field(only)
    else:
        scan_all(force=force)
