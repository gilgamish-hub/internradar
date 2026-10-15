"""Time, text and identity helpers shared by the web app and the scanner."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone

FREQUENCIES = {
    "daily": "Every day",
    "weekdays": "Weekdays only (Mon-Fri)",
    "alternate": "Every 2 days",
    "weekly": "Once a week (Monday)",
}


# --- time ------------------------------------------------------------------

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime | None) -> str:
    return "" if dt is None else dt.replace(microsecond=0).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def local_now(tz_offset: int) -> datetime:
    """Wall-clock time for a student whose zone is tz_offset minutes from UTC."""
    return utcnow().astimezone(timezone(timedelta(minutes=tz_offset)))


def parse_hhmm(value: str, default: tuple[int, int] = (9, 0)) -> tuple[int, int]:
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", value or "")
    if not m:
        return default
    h, mi = int(m.group(1)), int(m.group(2))
    return (h, mi) if 0 <= h < 24 and 0 <= mi < 60 else default


def next_due(deliver_time: str, frequency: str, tz_offset: int,
             last_sent: datetime | None = None, after: datetime | None = None) -> datetime:
    """The next moment (UTC) this student's digest should go out.

    Walks forward a day at a time instead of doing arithmetic on weekdays, so
    "weekdays only" and "every 2 days" need no special cases and a student who
    changes their time never lands in the past.
    """
    tz = timezone(timedelta(minutes=tz_offset))
    now_local = (after or utcnow()).astimezone(tz)
    hour, minute = parse_hhmm(deliver_time)
    last_local_date = last_sent.astimezone(tz).date() if last_sent else None

    candidate = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    for _ in range(15):
        if candidate > now_local and _frequency_allows(frequency, candidate, last_local_date):
            return candidate.astimezone(timezone.utc)
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc)


def _frequency_allows(frequency: str, candidate: datetime, last_date) -> bool:
    if frequency == "weekdays":
        return candidate.weekday() < 5
    if frequency == "weekly":
        return candidate.weekday() == 0
    if frequency == "alternate":
        return last_date is None or (candidate.date() - last_date).days >= 2
    return True


def when_text(dt: datetime | None, tz_offset: int = 330) -> str:
    """'Today 09:00' / 'Tomorrow 09:00' / 'Thu 17 Oct, 09:00' in the student's clock."""
    if dt is None:
        return "not scheduled"
    tz = timezone(timedelta(minutes=tz_offset))
    local = dt.astimezone(tz)
    today = utcnow().astimezone(tz).date()
    days = (local.date() - today).days
    if days == 0:
        return f"today {local:%H:%M}"
    if days == 1:
        return f"tomorrow {local:%H:%M}"
    if days == -1:
        return f"yesterday {local:%H:%M}"
    return f"{local:%a %d %b}, {local:%H:%M}"


def ago(dt: datetime | None) -> str:
    if dt is None:
        return "never"
    secs = (utcnow() - dt).total_seconds()
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} h ago"
    return f"{int(secs // 86400)} d ago"


# --- text and identity -----------------------------------------------------

# Legal forms and generic suffixes that make one employer look like three
# ("Discover Dollar" / "Discover Dollar Inc" / "Discover Dollar Technologies").
COMPANY_NOISE = re.compile(
    r"^(inc|incorporated|ltd|limited|pvt|private|llp|plc|corp|corporation|co|company|"
    r"technologies|technology|tech|labs|lab|solutions|solution|systems|system|"
    r"services|service|consulting|consultancy|group|global|india|indian|digital|ventures)$")


def text(value) -> str:
    """Scraped fields arrive as None, '' or NaN. Treat all three as empty."""
    if value is None or (isinstance(value, float) and value != value):
        return ""
    return str(value)


def company_key(name) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", text(name).lower()).split()
    core = [w for w in words if not COMPANY_NOISE.match(w)]
    # "Arham Web Work" and "Arham Web Works" are one employer posting one
    # internship, so a trailing plural comes off every word long enough for
    # that to be safe.
    core = [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
            for w in (core or words)]
    return "".join(core)


def posting_key(company, title) -> str:
    """Identifies one opening across scrapes and across boards. The link alone
    cannot: boards re-post the same opening with a fresh URL every few days."""
    raw = company_key(company) + "|" + re.sub(r"[^a-z0-9]", "", text(title).lower())
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def hash_password(password: str, salt: str | None = None) -> str:
    """pbkdf2-sha256, stdlib only. Stored as salt$hex."""
    import os
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"{salt}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    import hmac
    if not stored or "$" not in stored:
        return False
    salt, _ = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, salt), stored)


def valid_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$", (value or "").strip()))


def shorten(value: str, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", text(value)).strip()
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"
