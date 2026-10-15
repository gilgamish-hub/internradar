# InternRadar

**Internships in your field, delivered at the time you choose.**

A student enrolls once — their field, the cities they can work in, the lowest
stipend worth their time, and an hour of the day. From then on InternRadar
watches the job boards for them, scores every internship it finds against
their profile, and emails them only the ones that fit, at that hour, every
day. No logging in to check. No spreadsheets.

It runs on one laptop with Python and SQLite. There is no cloud account to
open, no API key to buy, and no AI model in the loop — the matching is a set
of rules you can read in one file and argue with.

```
┌──────────────┐   every 8h    ┌─────────────┐   at your time   ┌──────────┐
│ LinkedIn     │ ───────────►  │  the pool   │ ───────────────► │ your     │
│ Naukri       │   one scrape  │  (SQLite)   │   scored, with   │ inbox +  │
│ Indeed       │   per field   │             │   reasons        │ email    │
└──────────────┘               └─────────────┘                  └──────────┘
```

---

## Table of contents

- [Run it in three steps](#run-it-in-three-steps)
- [What happens next](#what-happens-next)
- [Turning email on](#turning-email-on)
- [Keeping it running](#keeping-it-running)
- [Settings](#settings)
- [How the matching works](#how-the-matching-works)
- [Adding your own field](#adding-your-own-field)
- [Using it outside India](#using-it-outside-india)
- [Deploying it](#deploying-it)
- [The files](#the-files)
- [Troubleshooting](#troubleshooting)
- [What it does not do](#what-it-does-not-do)

---

## Run it in three steps

You need **Python 3.10 or newer**. Check with `python --version`
(`python3 --version` on macOS/Linux). If you don't have it, get it from
[python.org/downloads](https://www.python.org/downloads/) — on Windows tick
**"Add Python to PATH"** in the installer.

**1. Get the project and open a terminal in its folder.**

```bash
git clone <this-repo> internradar
cd internradar
```

(No git? Download the ZIP, unzip it, then open a terminal in that folder.)

**2. Set it up** — this builds a private virtual environment and installs the
three packages. It takes a minute or two.

```bash
python setup.py
```

**3. Start it.**

| Your computer | Command |
|---|---|
| Windows | `start_portal.cmd` (or double-click it) |
| macOS / Linux | `./start.sh` |
| Anywhere | `.venv/bin/python app.py` — on Windows `.venv\Scripts\python app.py` |

Then open **<http://127.0.0.1:8700>** and press **Enroll**.

> **Who is the operator?** The portal ships with no accounts at all — the first
> person to enroll becomes the operator and gets the `/admin` page, where you
> can see every student, every field's pool, and force a scan.
>
> If you would rather decide that in advance (so it does not depend on who
> signs up first), put the addresses in `.env`:
>
> ```ini
> ADMIN_EMAILS=you@example.com,cofounder@example.com
> ```
>
> Anyone enrolling with one of those is an operator, whenever they enroll.
> Everyone else is an ordinary student. You can also promote someone later
> with `python manage.py admin their@email.com`.

### Want to look around first, without waiting for a scan?

A first real scan takes a few minutes. To see the portal full of internships
immediately, open `.env`, set `DEMO_MODE=1`, and restart. That loads 23
realistic sample internships — including a fee-charging scam the portal must
refuse to pass on, and a course-style "internship" it must flag rather than
hide. Set it back to `0` when you want real ones.

---

## What happens next

Nothing, which is the point. Leave the window open and:

1. **Within a minute**, the scheduler notices your field has never been
   scanned and starts one. It searches 3 boards × 4 search terms, so give it
   a few minutes. Watch it in the terminal, or on `/admin`.
2. **Internships appear in your inbox** on the dashboard as they are scored.
3. **At the hour you chose**, the digest goes out — by email if you set that
   up, otherwise it is written to `data/outbox` as an `.html` file you can
   open, and it is on the dashboard either way.
4. **Every 8 hours** the pool refreshes, and tomorrow's digest contains only
   things you have not already been sent.

On the dashboard each internship can be marked **I applied**, **Save**, or
**Not interested**. Settings changes apply to the next digest. **Pause** stops
deliveries during exams without losing anything. **Delete the account** takes
every row with it.

---

## Turning email on

**Email ships switched off, and that is deliberate.** Sending needs a
credential only you can create, so the portal is built not to depend on it:
with no SMTP settings every digest is written to `data/outbox` as an `.html`
file you can open in a browser, and it appears on the student's dashboard
either way. Turning email on is an upgrade, not a prerequisite.

Gmail stopped accepting ordinary account passwords from apps in 2022. You need
a 16-character **app password**.

**1. Turn on 2-Step Verification** on the account you want to send *from* —
<https://myaccount.google.com/security>. The app-password page does not exist
until this is on.

**2. Create the app password** — <https://myaccount.google.com/apppasswords>.
Name it anything. Google shows 16 characters in four blocks; copy them and
**delete the spaces**.

**3. Put them in `.env`**, uncommenting both lines:

```ini
SMTP_USER=yourname@gmail.com
SMTP_PASS=abcdefghijklmnop
```

**4. Restart the portal.** `.env` is read once, at startup.

**5. Check it.** Either `/admin` → **Test the email login**, or:

```bash
.venv/bin/python mailer.py          # Windows: .venv\Scripts\python mailer.py
```

It prints one line: the login worked, or exactly why it was refused.

### Things that commonly go wrong

| Symptom | Cause |
|---|---|
| `535 Username and Password not accepted` | You used the Google account password, not the app password. |
| The app-passwords page says it is unavailable | 2-Step Verification is off, **or** this is a college/work Google Workspace account whose admin has disabled app passwords. Bennett, and most universities, do. Use a personal Gmail — the sending address does not have to belong to any student. |
| Login works, nothing arrives | Check `/admin` → recent deliveries. A digest with 0 items means nothing new scored above `MIN_SCORE`, not a mail failure. |
| Digests still land in `data/outbox` | The portal was not restarted after editing `.env`. |

Nothing is ever lost to a mail failure: a refused login still writes the digest
to `data/outbox` and records the error on `/admin`.

Not on Gmail? Set `SMTP_HOST` and `SMTP_PORT` — Outlook is
`smtp.office365.com` port `587`.

**Gmail sends roughly 500 messages a day**, which is hundreds of students on a
daily digest. Past that, point the same `SMTP_*` settings at a sending service
(Resend, SES, Postmark).

---

## Keeping it running

The portal only scrapes and emails while the process is alive.

**Windows** — register it to start at every logon, with no console window:

```powershell
powershell -ExecutionPolicy Bypass -File install_tasks.ps1
```

Remove it later with `install_tasks.ps1 -Remove`.

**macOS / Linux** — the simplest version is to leave `./start.sh` running in a
terminal, or use `nohup ./start.sh &`. For a proper service, a systemd unit:

```ini
# /etc/systemd/system/internradar.service
[Unit]
Description=InternRadar
After=network.target

[Service]
WorkingDirectory=/home/you/internradar
ExecStart=/home/you/internradar/.venv/bin/python app.py
Restart=always
User=you

[Install]
WantedBy=multi-user.target
```

Then `sudo systemctl enable --now internradar`.

**Any computer** — use Docker, see [Deploying it](#deploying-it).

---

## Running it for other people

The portal is multi-user from the start: everyone who enrolls gets their own
field, cities, stipend floor, delivery time and inbox, and nobody can see
anyone else's. There is no account baked into the project — a fresh clone has
an empty database.

`manage.py` is the operator's toolkit, so you never need to open the database
by hand. On Windows put `.venv\Scripts\python` in front; on macOS/Linux
`.venv/bin/python`.

```bash
python manage.py stats                  # what is in the database, is email on
python manage.py users                  # every account, their field and schedule
python manage.py admin you@example.com  # make someone an operator
python manage.py unadmin them@ex.com    # take it away
python manage.py send you@example.com   # build and send one digest right now
python manage.py scan                   # scrape now instead of waiting
python manage.py scan cybersecurity     # just one field
python manage.py delete-user them@ex.com
python manage.py reset-users            # remove every account, keep the pool
python manage.py reset-all              # back to a completely empty database
```

Anything destructive copies the database first (`data/portal.backup-*.db`) and
asks you to type `yes`. Add `--force` to skip the question in a script.

**Handing the project to someone else?** Run `python manage.py reset-users`
before you do. It clears every account while keeping the internships already
scraped, so whoever enrolls next gets matches immediately instead of waiting
for a first scan.

---

## Settings

All optional, all in `.env` (copy `.env.example` if you don't have one). The
portal reads it at startup, so restart after a change.

| Setting | Default | What it does |
|---|---|---|
| `SMTP_USER` / `SMTP_PASS` | unset | Email. Unset means digests go to `data/outbox`. |
| `SMTP_HOST` / `SMTP_PORT` | `smtp.gmail.com` / `587` | Your mail provider. |
| `PORTAL_PORT` | `8700` | Change if something else owns that port. |
| `PORTAL_HOST` | `127.0.0.1` | `0.0.0.0` lets other devices on your wifi open it. |
| `PORTAL_BASE_URL` | `http://127.0.0.1:8700` | The links inside the emails. |
| `PORTAL_BRAND` | `InternRadar` | Rename it to whatever you like. |
| `ADMIN_EMAILS` | unset | Who gets `/admin`. Unset = the first account created. |
| `SCAN_SITES` | `linkedin,naukri,indeed` | Boards to search. `glassdoor` also works. |
| `SCAN_COUNTRY` / `SCAN_LOCATION` | `India` | Where to look. |
| `SCAN_DAYS` | `7` | How old a posting may be. |
| `SCAN_FIELD_TTL_HOURS` | `8` | Minimum gap between two scans of one field. |
| `SCAN_RESULTS_PER_QUERY` | `20` | Results per board per search term. |
| `MIN_SCORE` | `35` | Below this, a posting is not called a match. |
| `DEFAULT_MAX_ITEMS` | `10` | Internships per digest, for new students. |
| `DEMO_MODE` | `0` | `1` loads samples instead of scraping. |

---

## How the matching works

No model is called anywhere. Every point is a rule in the docstring at the top
of [`matcher.py`](matcher.py), and every point produces a line of plain English
that the student sees next to the internship — because ten links with no
reason attached just get ignored.

Out of 100:

| | |
|---|---|
| **+35** | the job title is squarely in the student's field |
| **+20** | the title is adjacent to it |
| **+12** | the title is generic ("Graduate Trainee") but three or more of the field's own skills run through the description |
| **+15** | it is clearly an internship / trainee / fresher opening |
| **+4** | per skill from the field found in the description (max +40) |
| **+3** | per skill the student said they already have (max +15) |
| **+1** | per skill every job asks for — communication, Excel (max +5) |
| **−25** | it reads like a paid training course rather than a job |
| **−10** | the description is too short to tell anything |

**Rejected outright, never shown and never emailed:**

- anything mentioning a **registration fee, security deposit or "guaranteed
  placement"** — no genuine employer asks a candidate for money
- a stipend below the student's floor
- unpaid work, unless the student ticked that they are open to it
- a city the student did not ask for

Course-style "internships" — the ones selling you a certificate — are
deliberately **not** hidden. They are delivered with a visible warning,
because sometimes they are the only thing going and the student should decide
knowing exactly what it is.

Two details that matter more than they look:

- **Field skills are counted separately from common ones.** A marketing
  internship asking for "communication skills" and "teamwork" must not look
  like a machine learning match. Pooling them was the single biggest source of
  junk matches during development.
- **A posting is identified by company + title, not by its URL.** Boards
  re-post the same opening with a fresh link every few days, and
  "Arham Web Work" and "Arham Web Works" are one employer.

---

## Adding your own field

One entry in [`fields.py`](fields.py) and nothing else changes — the signup
dropdown, the scraper's search terms and the matcher all read that one table.

```python
"biotech": {
    "label": "Biotechnology / Life Sciences",
    "queries": ["biotechnology intern", "life sciences intern", "lab intern"],
    "titles": r"biotech|life scien|microbiolog|molecular|genomic",
    "near":   r"research assistant|\blab\b|quality control",
    "skills": {
        "pcr": r"\bpcr\b",
        "cell culture": r"cell culture",
        "elisa": r"\belisa\b|western blot",
    },
},
```

- `queries` are what gets typed into the job boards. Keep it to 3–4: each one
  is a separate request per board, per scan.
- `titles` is the strong signal — "this job really is in my field".
- `near` is for adjacent roles, worth fewer points.
- `skills` are matched against the description. Each hit adds points *and*
  gets shown to the student as a reason.

Restart the portal and the new field is in the dropdown.

---

## Using it outside India

The portal ships pointed at India: `SCAN_COUNTRY`, `SCAN_LOCATION` and the
city table in [`cities.py`](cities.py) are all Indian. To move it elsewhere:

1. In `.env`, set `SCAN_COUNTRY` and `SCAN_LOCATION` to your country, and drop
   `naukri` from `SCAN_SITES` — it is an Indian board.
2. Replace the `CITIES` table in `cities.py` with your own cities. Each entry
   is `key: (label, regex, region)`, and the regex should cover every spelling
   the boards use, including state codes.
3. Stipends are compared as plain monthly numbers with no currency conversion,
   so set the floor in whatever your boards advertise in.

Until you do step 2, students outside India should pick **"Anywhere"** as
their city, which accepts everything.

---

## Deploying it

### Docker (any machine, including a cheap VPS)

```bash
docker compose up -d        # build and start
docker compose logs -f      # watch scans and digests
docker compose down         # stop; the data volume survives
```

The database lives in a named volume, so rebuilding the image does not lose
your students. Put your `SMTP_*` values in `docker-compose.yml` under
`environment:`, or point it at an env file.

### A hosting platform (Render, Railway, Fly.io)

The app already does what these platforms expect: it reads `$PORT`, binds
`0.0.0.0` when `$PORT` is set, and answers `/healthz`. Point the platform at
this repo with the Dockerfile, or use:

- **Build:** `pip install -r requirements.txt`
- **Start:** `python app.py`

Then set these in the platform's environment variables:

```
PORTAL_BASE_URL=https://your-app.onrender.com
PORTAL_SECRET=<any long random string>
SMTP_USER=...
SMTP_PASS=...
```

Two things to get right before anyone else uses it:

- **Attach a persistent disk mounted at `/app/data`.** Free tiers usually have
  an ephemeral filesystem — without a disk, every student and every match
  disappears on each redeploy.
- **Set `PORTAL_SECRET`.** Otherwise the session key is regenerated on each
  restart and everyone is signed out.

Free tiers that sleep when idle are a poor fit: a sleeping app does not scrape
and does not send the 9am digest. A small always-on instance, or a laptop you
leave on, works better.

### Before you let strangers in

This is a small, honest app, not a hardened SaaS. If it is going to be public:

- it stores passwords with PBKDF2-SHA256 (200k iterations) and nothing else of
  value, but there is **no email verification** — anyone can enroll with any
  address, including someone else's
- there is no password reset flow; the operator would have to help
- it rate-limits failed sign-ins per IP and sets `SameSite=Lax` cookies, which
  is enough for a classroom, not for the open internet
- **put it behind HTTPS.** The platforms above do this for you.

---

## The files

| File | What it is |
|---|---|
| `app.py` | the website: enroll, sign in, dashboard, settings, admin |
| `scheduler.py` | the loop that refreshes the pool and sends digests on time |
| `scraper.py` | talks to the job boards, fills the shared pool |
| `matcher.py` | the scoring rules and the reasons shown to the student |
| `digest.py` | builds one student's digest and sends it |
| `fields.py` | **the field catalogue** — 21 fields, their search terms and skills |
| `cities.py` | cities, and every spelling the boards use for them |
| `mailer.py` | SMTP, with the `data/outbox` fallback |
| `db.py` | the SQLite schema |
| `config.py` | every setting, read from `.env` |
| `demo_data.py` | the sample internships behind `DEMO_MODE` |
| `manage.py` | operator commands: accounts, admins, resets, manual scans |
| `setup.py` | one-command setup, any OS |
| `data/portal.db` | students, pool, matches, delivery history |

**`data/portal.db` is the one file worth backing up.** `data/` and `.env` are
in `.gitignore` — they hold real people's accounts and your email password, so
never commit them.

---

## Troubleshooting

**`python: command not found` / `'python' is not recognized`**
Python is not installed, or not on your PATH. Try `python3` instead. On
Windows, reinstall from python.org with **"Add Python to PATH"** ticked.

**Setup fails while installing**
You are probably on Python 3.9 or older — check `python --version`. The error
usually names a package that has no wheel for your version.

**The page will not open**
Check the terminal actually says `InternRadar is running at ...`. If something
else owns port 8700, set `PORTAL_PORT=8701` in `.env` and restart. Use
`127.0.0.1:8700`, not `localhost:8700`, if your machine resolves localhost oddly.

**"Your field has not been scanned yet" and nothing arrives**
That is normal for the first few minutes. If it persists, open `/admin` and
look at the field pool table. `postings seen: 0` on every board means the
boards are refusing requests from your IP — LinkedIn rate-limits hardest and
returns HTTP 429 after a few queries in one run. Drop `linkedin` from
`SCAN_SITES` and the other two carry it.

**Lots in the pool, nothing in your inbox**
Your filters are too tight. A high stipend floor plus one city plus "remote
only" rejects nearly everything. The dashboard shows the pool size for your
field next to your inbox count, so the gap is visible. Note that most postings
never state a stipend — those are kept and flagged, not dropped.

**Digests never arrive**
`/admin` shows the last scheduler tick and every delivery with its error. If
the channel says `outbox`, email is either not configured or the login failed —
the digest is in `data/outbox` either way. Test the login from `/admin`.

**It sent me something irrelevant**
Raise `MIN_SCORE` in `.env`, or tighten the field's `titles` regex in
`fields.py`. Press **Not interested** and it will not come back.

---

## What it does not do

Said plainly, so nothing here is a surprise:

- **It does not apply for you.** It finds and ranks; a human writes the
  application. Anything that auto-applies on your behalf gets you filtered out.
- **It does not see every internship.** It sees what LinkedIn, Naukri and
  Indeed return for its search terms. Internshala, Unstop and company career
  pages are not covered.
- **It cannot verify an employer.** It drops the obvious money-asking scams
  and flags course-style postings, but a convincing fake will get through.
  Never pay anyone for an internship.
- **It does not scale to thousands of students on a laptop.** SQLite and one
  thread are comfortable for a few hundred. Past that, move the scheduler to
  its own process and the pool to Postgres.

---

## Licence

MIT — see [LICENSE](LICENSE). Use it, change it, run it for your college.
