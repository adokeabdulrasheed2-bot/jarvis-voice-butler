from __future__ import annotations

import logging
from email.header import decode_header, make_header
from email.mime.text import MIMEText
import imaplib
import smtplib
import re

from vb.config.settings import Settings
from vb.data.contacts import ContactBook
from vb.security.permissions import PermissionGate

logger = logging.getLogger("vb.email")


def handle_email(text: str, settings: Settings, contacts: ContactBook, gate: PermissionGate) -> str:
    gate.require("EMAIL")
    if not settings.email_username or not settings.email_password:
        return "Email is not configured. Set EMAIL_USERNAME and EMAIL_PASSWORD in the environment."
    lowered = text.lower()
    if any(word in lowered for word in ("unread", "new", "latest", "inbox", "summarize", "read")):
        return _read_recent(text, settings)
    target, subject, body = _parse_send(text)
    if not target or not body:
        return "Tell me the recipient and the message. Example: send an email to John saying the report is ready."
    address = contacts.resolve_email(target)
    if not address:
        return f"I do not have an email address for {target}."
    gate.confirm("EMAIL", f"Send email to {address}?")
    return _send(settings, address, subject, body)


def _send(settings: Settings, to_addr: str, subject: str, body: str) -> str:
    if not settings.email_smtp_host:
        return "EMAIL_SMTP_HOST is not set."
    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = settings.email_from or settings.email_username
    message["To"] = to_addr
    try:
        with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(settings.email_username, settings.email_password)
            smtp.send_message(message)
        return f"Email sent to {to_addr}."
    except Exception as exc:
        return f"Email send failed: {exc}"


def _read_recent(text: str, settings: Settings) -> str:
    if not settings.email_imap_host:
        return "EMAIL_IMAP_HOST is not set."
    try:
        mail = imaplib.IMAP4_SSL(settings.email_imap_host, settings.email_imap_port)
        mail.login(settings.email_username, settings.email_password)
        mail.select(settings.email_mailbox)
        status, data = mail.search(None, "UNSEEN" if "unread" in text.lower() or "new" in text.lower() else "ALL")
        if status != "OK":
            mail.logout()
            return "I could not search the mailbox."
        ids = data[0].split()
        if not ids:
            mail.logout()
            return "There are no matching emails."
        latest = ids[-5:]
        summaries = []
        for msg_id in reversed(latest):
            status, payload = mail.fetch(msg_id, "(RFC822.HEADER BODY.PEEK[TEXT])")
            if status != "OK" or not payload:
                continue
            header_bytes = payload[0][1] if isinstance(payload[0], tuple) else b""
            from email import message_from_bytes

            msg = message_from_bytes(header_bytes)
            summaries.append(
                f"From {_decode(msg.get('From', ''))}, subject {_decode(msg.get('Subject', '(no subject)'))}."
            )
        mail.logout()
        return " ".join(summaries) or "I could not read email headers."
    except Exception as exc:
        return f"Email receive failed: {exc}"


def _decode(value: str) -> str:
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _parse_send(text: str) -> tuple[str, str, str]:
    match = re.search(
        r"(?:email|e-mail)\s+(?:to\s+)?(.+?)\s+(?:saying|that|:)\s+(.+)",
        text,
        re.I,
    )
    if not match:
        return "", "Message from VB", ""
    return match.group(1).strip(), "Message from VB", match.group(2).strip()
