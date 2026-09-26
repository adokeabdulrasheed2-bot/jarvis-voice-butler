from __future__ import annotations

import re

from vb.data.contacts import ContactBook
from vb.hardware.sim808_manager import Sim808Manager
from vb.security.permissions import PermissionGate


def handle_call(text: str, sim: Sim808Manager, contacts: ContactBook, gate: PermissionGate) -> str:
    gate.require("PHONE_CALLS")
    lowered = text.lower()
    if re.search(r"\bhang\s*up\b|\bend (the )?call\b", lowered):
        ok, detail = sim.hangup()
        return "Call ended." if ok else f"Hang up failed: {detail}"
    if "reject" in lowered:
        ok, detail = sim.reject()
        return "Call rejected." if ok else f"Reject failed: {detail}"
    if "answer" in lowered:
        ok, detail = sim.answer()
        return "Answering." if ok else f"Answer failed: {detail}"
    target = _parse_target(text)
    if not target:
        return "Who should I call?"
    number = contacts.resolve_phone(target)
    if not number:
        return f"I do not have a phone number for {target}."
    gate.confirm("PHONE_CALLS", f"Call {target} at {number}?")
    ok, detail = sim.dial(number)
    if ok:
        return f"Calling {target}."
    return f"Call failed: {detail}"


def _parse_target(text: str) -> str:
    match = re.search(r"\b(?:call|dial)\s+(.+)$", text, re.I)
    if not match:
        return ""
    return match.group(1).strip(" .")
