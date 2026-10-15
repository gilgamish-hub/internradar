"""Indian internship hubs, spelled every way the job boards spell them.

The boards are inconsistent: Naukri and Indeed often give only a state ("KA,
IN"), LinkedIn gives "Bengaluru East, Karnataka, India", and plenty of posts
say nothing but "India". Matching on a plain string would throw away real
openings, so each city carries a pattern, and a posting whose city cannot be
read at all is kept and flagged rather than dropped.
"""
from __future__ import annotations

import re

# key -> (label shown to the student, pattern, the wider region it sits in)
CITIES: dict[str, tuple[str, str, str]] = {
    "delhi-ncr": ("Delhi NCR", r"\bncr\b|national capital region|delhi[- ]ncr|\bnew delhi\b|\bdelhi\b|\bnoida\b|greater noida|\bgurugram\b|\bgurgaon\b|\bghaziabad\b|\bfaridabad\b|\bdl,?\s*in\b", "North"),
    "bengaluru": ("Bengaluru", r"\bbengaluru\b|\bbangalore\b|\bblr\b|\bka,?\s*in\b|\bkarnataka\b", "South"),
    "hyderabad": ("Hyderabad", r"\bhyderabad\b|\bsecunderabad\b|\bhyd\b|\bts,?\s*in\b|telangana", "South"),
    "chennai": ("Chennai", r"\bchennai\b|\bmadras\b|\btn,?\s*in\b|tamil nadu", "South"),
    "mumbai": ("Mumbai", r"\bmumbai\b|\bbombay\b|navi mumbai|\bthane\b|andheri|powai", "West"),
    "pune": ("Pune", r"\bpune\b|\bpimpri\b|hinjewadi|\bmh,?\s*in\b|maharashtra", "West"),
    "kolkata": ("Kolkata", r"\bkolkata\b|\bcalcutta\b|\bwb,?\s*in\b|west bengal|salt lake", "East"),
    "ahmedabad": ("Ahmedabad", r"\bahmedabad\b|\bgandhinagar\b|\bsurat\b|\bvadodara\b|\bgj,?\s*in\b|gujarat", "West"),
    "jaipur": ("Jaipur", r"\bjaipur\b|\brj,?\s*in\b|rajasthan|\bjodhpur\b|\budaipur\b", "North"),
    "indore": ("Indore", r"\bindore\b|\bbhopal\b|\bmp,?\s*in\b|madhya pradesh", "Central"),
    "chandigarh": ("Chandigarh / Mohali", r"\bchandigarh\b|\bmohali\b|\bpanchkula\b|\bzirakpur\b", "North"),
    "lucknow": ("Lucknow / Kanpur", r"\blucknow\b|\bkanpur\b|\bvaranasi\b|\bprayagraj\b", "North"),
    "kochi": ("Kochi / Trivandrum", r"\bkochi\b|\bcochin\b|\bernakulam\b|\btrivandrum\b|thiruvananthapuram|\bkl,?\s*in\b|kerala", "South"),
    "coimbatore": ("Coimbatore", r"\bcoimbatore\b|\bmadurai\b|\btrichy\b|tiruchirappalli", "South"),
    "bhubaneswar": ("Bhubaneswar", r"\bbhubaneswar\b|\bcuttack\b|\bor,?\s*in\b|odisha", "East"),
    "nagpur": ("Nagpur", r"\bnagpur\b|\bnashik\b|\baurangabad\b", "West"),
    "dehradun": ("Dehradun", r"\bdehradun\b|\bharidwar\b|\brishikesh\b|uttarakhand", "North"),
    "guwahati": ("Guwahati", r"\bguwahati\b|\bassam\b|\bshillong\b", "East"),
}

DEFAULT_LOCATION = "India"   # what the boards are asked for when no city is named
ANYWHERE = "anywhere"           # the student will take any city in India
REMOTE_ONLY = "remote-only"     # the student only wants work-from-home

REMOTE_PATTERN = r"\bremote\b|work from home|\bwfh\b|anywhere in india|virtual internship"
# "India", "IN" and blanks say nothing about the city - ask, do not reject.
UNKNOWN_PATTERN = r"^\s*(india|in|remote,? in|hybrid)?\s*$"


def choices() -> list[tuple[str, str]]:
    """(key, label) for the city picker, with the two special options first."""
    rest = sorted(((k, v[0]) for k, v in CITIES.items()), key=lambda p: p[1])
    return [(ANYWHERE, "Anywhere in India"), (REMOTE_ONLY, "Remote / work from home only")] + rest


def label(key: str) -> str:
    if key == ANYWHERE:
        return "Anywhere in India"
    if key == REMOTE_ONLY:
        return "Remote only"
    return CITIES.get(key, (key, "", ""))[0]


def labels(keys: list[str]) -> str:
    return ", ".join(label(k) for k in keys) or "not set"


def identify(location: str, is_remote: bool = False) -> tuple[str, str]:
    """-> (city key or '', label to show).

    '' as the key means "could not tell" - either remote, or the posting never
    named a city. The caller decides what to do with that.
    """
    loc = (location or "").strip()
    low = loc.lower()
    if is_remote or re.search(REMOTE_PATTERN, low):
        return "remote", "Remote"
    for key, (name, pattern, _) in CITIES.items():
        if re.search(pattern, low):
            return key, name
    if re.match(UNKNOWN_PATTERN, low):
        return "", "City not stated"
    return "", loc


def accepts(wanted: list[str], city_key: str) -> tuple[bool, str]:
    """Does this student's city list accept a posting in city_key?

    -> (accepted, note). An empty or unreadable city is accepted with a note,
    because about a third of postings never name one.
    """
    wanted = wanted or [ANYWHERE]
    if city_key == "remote":
        if REMOTE_ONLY in wanted or ANYWHERE in wanted or any(w in CITIES for w in wanted):
            return True, ""
        return False, "remote role"
    if REMOTE_ONLY in wanted and ANYWHERE not in wanted:
        return False, "on-site, you asked for remote only"
    if ANYWHERE in wanted:
        return True, ""
    if not city_key:
        return True, "city not stated - check the posting"
    if city_key in wanted:
        return True, ""
    return False, f"{label(city_key)} is not in your cities"


def search_locations(wanted: list[str]) -> list[str]:
    """What to type into the boards' location box for this set of cities.

    One scrape per location is expensive, so the list is capped: the pool is
    filtered per student afterwards anyway.
    """
    wanted = wanted or [ANYWHERE]
    if ANYWHERE in wanted or REMOTE_ONLY in wanted or not wanted:
        return [DEFAULT_LOCATION]
    named = [CITIES[w][0] for w in wanted if w in CITIES][:3]
    return named or [DEFAULT_LOCATION]
