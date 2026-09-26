from __future__ import annotations

import logging
import re

from vb.data.contacts import ContactBook
from vb.hardware.sim808_manager import Sim808Manager
from vb.security.permissions import PermissionGate

logger = logging.getLogger("vb.sms")


def handle_sms(text: str, sim: Sim808Manager, contacts: ContactBook, gate: PermissionGate) -> str:
    gate.require("SMS")
    lowered = text.lower()
    if any(word in lowered for word in ("new", "inbox", "list", "any message", "messages")):
        try:
            messages = sim.list_sms("ALL")
        except Exception as exc:
            return f"I could not read SMS storage: {exc}"
        unread = [m for m in messages if "UNREAD" in m.status.upper()]
        if "new" in lowered or "unread" in lowered:
            chosen = unread or messages
        else:
            chosen = messages
        if not chosen:
            return "There are no SMS messages on the module."
        lines = [
            f"From {m.sender} at {m.timestamp or 'unknown time'}: {m.body}" for m in chosen[:5]
        ]
        prefix = f"{len(unread)} unread. " if unread else ""
        return prefix + " ".join(lines)
    target, body = _parse_send(text)
    if not target or not body:
        return "Tell me who to text and what to say. For example: send John an SMS saying I will be home at 8."
    number = contacts.resolve_phone(target)
    if not number:
        return f"I do not have a phone number for {target}. Add it to data/contacts.json."
    gate.confirm("SMS", f"Send SMS to {target} ({number}) saying: {body}?")
    ok, detail = sim.send_sms(number, body)
    if ok:
        return f"SMS sent to {target}."
    return f"SMS failed: {detail}"


def _parse_send(text: str) -> tuple[str, str]:
    match = re.search(
        r"(?:send|text)\s+(?:an?\s+sms\s+to\s+|sms\s+to\s+)?(.+?)\s+(?:an?\s+sms\s+)?(?:saying|that|:)\s+(.+)",
        text,
        re.I,
    )
    if match:
        return match.group(1).strip(" ."), match.group(2).strip()
    match = re.search(r"sms\s+(.+?)\s+(.+)", text, re.I)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", ""
