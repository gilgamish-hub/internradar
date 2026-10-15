"""Decide whether one posting is worth sending to one student, and say why.

No model is called anywhere here: the score is a set of rules you can read,
argue with and change. Every point it awards or takes away also produces a
line of plain English, because a student who gets ten links with no reason
attached just ignores them.

Rules, out of 100:
  +35  the job title is squarely in the student's field
  +20  the title is adjacent to it (near-miss roles still worth an hour)
  +12  the title is generic ("Graduate Trainee") but at least three of the
       field's own skills run through the description
  +15  it is clearly an internship / trainee / fresher opening
  +4   per skill from the field that appears in the description  (max +40)
  +1   per skill every job asks for - communication, Excel      (max +5)
  +3   per skill the student themselves listed                  (max +15)
  -25  it reads like a paid training course, not a job
  -10  the description is too short to tell anything

Rejected outright (never shown, never emailed):
  any fee, deposit or "placement guarantee"      - these are scams
  a stipend below the student's floor
  unpaid, when the student did not agree to unpaid
  a city the student did not ask for
"""
from __future__ import annotations

import re

import cities
import fields

# Asking a candidate for money is the one thing no genuine employer does.
SCAM = (r"registration fee|training fee|security deposit|refundable deposit|"
        r"pay (a|the)? ?(fee|amount)|processing fee|placement guarantee|"
        r"placement guaranteed|guaranteed placement|certificate course fee")
# The same words appear in honest "we never charge a fee" disclaimers.
NEGATION = r"never|\bnot\b|\bno\b|don'?t|do not|won'?t|beware|fraud|scam|without any"
# Course-style "internships": you learn, they certify, the stipend is vague.
TRAINING = (r"what you'?ll learn|mentor guidance|training program|internship certificate|"
            r"certificate of completion|letter of recommendation|"
            r"stipend:?\W*(based on|performance|unpaid|none|n/?a)")
UNPAID = r"\bunpaid\b|without stipend|no stipend|stipend:?\W*(unpaid|none|nil|n/?a|0)"

PER_INTERVAL_MONTHS = {"yearly": 1 / 12, "monthly": 1, "weekly": 4.33, "daily": 22, "hourly": 8 * 22}


def monthly_stipend(stipend_min, stipend_max, interval: str) -> float | None:
    """Pay as a monthly figure, or None when the posting does not say.

    Judged on the TOP of an advertised range, so a wide band that could clear
    the student's floor is never thrown away on its lower end. The interval
    matters: without it a Rs 12,000/month stipend looks like Rs 12,000/year.
    """
    factor = PER_INTERVAL_MONTHS.get((interval or "monthly").lower(), 1)
    best = None
    for raw in (stipend_max, stipend_min):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value != value or value <= 0:      # value != value catches NaN
            continue
        best = max(best or 0, value * factor)
    return best


def pay_label(stipend_min, stipend_max, interval: str) -> str:
    monthly = monthly_stipend(stipend_min, stipend_max, interval)
    if monthly is None:
        return "Stipend not stated"
    if monthly >= 100_000:
        return f"Rs {monthly * 12 / 100_000:.1f}L/year"
    return f"Rs {monthly:,.0f}/month"


def red_flags(description: str) -> list[str]:
    """Fee / deposit phrases, ignoring the ones inside a disclaimer."""
    low = (description or "").lower()
    return sorted({m.group(0) for m in re.finditer(SCAM, low)
                   if not re.search(NEGATION, low[max(0, m.start() - 80):m.start()])})


def is_internship(title: str, description: str = "") -> bool:
    if re.search(fields.INTERN_TITLE, title or "", re.I):
        return True
    # Some boards put "Internship" only in the body ("Job type: Internship").
    return bool(re.search(r"job type:?\W*internship|this is an internship",
                          (description or "").lower()))


def field_skill_hits(field: str, description: str) -> list[str]:
    """Skills specific to the field - the ones that actually say "this is the job".

    Deliberately excludes the common skills: a marketing internship asking for
    "communication skills" and "teamwork" must not look like a machine learning
    match just because every JD on earth mentions those two.
    """
    low = (description or "").lower()
    spec = fields.FIELDS.get(field)
    if not spec:
        return []
    return [name for name, pattern in spec["skills"].items() if re.search(pattern, low)]


def common_skill_hits(description: str) -> list[str]:
    low = (description or "").lower()
    return [name for name, pattern in fields.COMMON_SKILLS.items() if re.search(pattern, low)]


def score(posting: dict, profile: dict) -> dict | None:
    """-> {score, fit, reasons, warnings} or None when the posting is rejected.

    posting  a row from the postings table (or the dict the scraper builds)
    profile  the student's row from the profiles table, as a dict
    """
    field = profile.get("field") or ""
    spec = fields.FIELDS.get(field)
    if not spec:
        return None

    title = (posting.get("title") or "").strip()
    desc = posting.get("description") or ""
    low_title, low_desc = title.lower(), desc.lower()
    points, reasons, warnings = 0, [], []

    # 1. Is it even in this field?
    if re.search(spec["titles"], low_title):
        points += 35
        reasons.append(f"Title is {spec['label']}")
    elif re.search(spec.get("near", r"(?!x)x"), low_title):
        points += 20
        reasons.append(f"Close to {spec['label']}")
    elif re.search(fields.INTERN_TITLE, low_title) and len(field_skill_hits(field, desc)) >= 3:
        # A title like "Graduate Trainee" says nothing, so the description has
        # to carry it - and carry it on several of the field's own skills, not
        # on one stray keyword.
        points += 12
        reasons.append("Generic title, but your field's skills run through the description")
    else:
        return None

    # 2. Is it an internship?
    if is_internship(title, desc):
        points += 15
        reasons.append("Internship / trainee opening")

    # 3. Never pass on a posting that asks the student for money.
    if red_flags(desc):
        return None
    if re.search(TRAINING, low_desc):
        points -= 25
        warnings.append("Reads like a paid training course - ask about the stipend before applying")

    # 4. Skills.
    hits = field_skill_hits(field, desc)
    common = common_skill_hits(desc)
    points += min(40, 4 * len(hits))
    points += min(5, len(common))      # worth something, never enough to qualify
    if hits:
        reasons.append(f"{len(hits)} skills from your field: " + ", ".join(hits[:6]))
    mine = [s.lower() for s in (profile.get("skills") or [])]
    overlap = [h for h in hits + common if h in mine]
    if overlap:
        points += min(15, 3 * len(overlap))
        reasons.append("You already have: " + ", ".join(overlap[:6]))
    if len(desc.strip()) < 200:
        points -= 10
        warnings.append("Short description - open the link to read the real requirements")

    # 5. Money.
    monthly = monthly_stipend(posting.get("stipend_min"), posting.get("stipend_max"),
                              posting.get("pay_interval") or "")
    floor = int(profile.get("min_stipend") or 0)
    allow_unpaid = bool(profile.get("allow_unpaid"))
    explicitly_unpaid = bool(re.search(UNPAID, low_desc))
    if monthly is not None:
        if monthly < floor and not (allow_unpaid and monthly == 0):
            return None
        reasons.append(pay_label(posting.get("stipend_min"), posting.get("stipend_max"),
                                 posting.get("pay_interval") or ""))
    elif explicitly_unpaid:
        if not allow_unpaid:
            return None
        warnings.append("Unpaid")
    elif floor > 0:
        warnings.append("Stipend not stated - ask before you invest time")

    # 6. Place.
    city_key, city_name = cities.identify(posting.get("location") or "",
                                          bool(posting.get("is_remote")))
    wanted = profile.get("cities") or []
    # "Remote internships are fine" is a separate tick from the city list, so a
    # student who turned it off gets no work-from-home roles even though their
    # city list would otherwise accept them.
    if city_key == "remote" and not profile.get("remote_ok", 1) and cities.REMOTE_ONLY not in wanted:
        return None
    ok, note = cities.accepts(wanted, city_key)
    if not ok:
        return None
    reasons.append(city_name or "Location not stated")
    if note:
        warnings.append(note)

    points = max(0, min(100, points))
    fit = "Strong" if points >= 65 else "Good" if points >= 50 else "Fair"
    return {"score": points, "fit": fit, "reasons": reasons, "warnings": warnings,
            "city_key": city_key, "city_label": city_name}
