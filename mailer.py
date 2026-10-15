"""Sending a digest.

With SMTP credentials in .env the digest is emailed. Without them nothing
fails: the same HTML is written to data/outbox so you can open it in a
browser, and the dashboard still shows the digest. That way the portal is
usable the moment it starts, and email is an upgrade rather than a
prerequisite.
"""
from __future__ import annotations

import re
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

import config
import utils


def _outbox_path(to: str, subject: str) -> Path:
    config.ensure_dirs()
    stamp = utils.utcnow().strftime("%Y%m%d-%H%M%S")
    safe_to = re.sub(r"[^a-zA-Z0-9._-]", "_", to)
    safe_subject = re.sub(r"[^a-zA-Z0-9]+", "-", subject).strip("-")[:50]
    return config.OUTBOX / f"{stamp}_{safe_to}_{safe_subject}.html"


def write_outbox(to: str, subject: str, html: str) -> Path:
    path = _outbox_path(to, subject)
    header = (f"<!-- To: {to} -->\n<!-- Subject: {subject} -->\n"
              f"<!-- Written {utils.iso(utils.utcnow())} -->\n")
    path.write_text(header + html, encoding="utf-8")
    return path


def send(to: str, subject: str, html: str, text: str = "") -> tuple[str, bool, str]:
    """-> (channel, ok, detail).  channel is 'email' or 'outbox'."""
    if not config.EMAIL_ENABLED:
        path = write_outbox(to, subject, html)
        return "outbox", True, f"email not configured, written to {path.name}"

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((config.MAIL_FROM_NAME, config.MAIL_FROM))
    message["To"] = to
    message.set_content(text or re.sub(r"<[^>]+>", " ", html))
    message.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=45) as server:
            server.ehlo()
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASS)
            server.send_message(message)
        return "email", True, f"sent to {to}"
    except Exception as exc:
        # A bad password or a blocked port must not lose the digest.
        path = write_outbox(to, subject, html)
        return "outbox", False, f"SMTP failed ({str(exc)[:120]}), written to {path.name}"


def check() -> str:
    """One line on whether email will work, for the admin page and setup."""
    if not config.EMAIL_ENABLED:
        return ("Email is off: SMTP_USER / SMTP_PASS are not set in .env. "
                "Digests are being written to data/outbox instead.")
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASS)
        return f"Email is working: {config.SMTP_USER} via {config.SMTP_HOST}."
    except Exception as exc:
        return f"Email is configured but the login failed: {str(exc)[:160]}"


if __name__ == "__main__":
    print(check())
