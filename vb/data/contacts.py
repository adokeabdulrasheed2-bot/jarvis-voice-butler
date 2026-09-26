from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Contact:
    name: str
    aliases: list[str]
    phone: str = ""
    email: str = ""

    def matches(self, query: str) -> bool:
        q = query.strip().casefold()
        names = [self.name, *self.aliases]
        return any(q == n.casefold() or q in n.casefold() for n in names)


class ContactBook:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.contacts: list[Contact] = []
        self.reload()

    def reload(self) -> None:
        if not self.path.exists():
            self.contacts = []
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        items = data.get("contacts", data if isinstance(data, list) else [])
        self.contacts = [
            Contact(
                name=str(item.get("name", "")),
                aliases=[str(a) for a in item.get("aliases", [])],
                phone=str(item.get("phone", "") or ""),
                email=str(item.get("email", "") or ""),
            )
            for item in items
            if item.get("name")
        ]

    def find(self, query: str) -> Contact | None:
        query = query.strip()
        if not query:
            return None
        for contact in self.contacts:
            if contact.matches(query):
                return contact
        return None

    def resolve_phone(self, query: str) -> str | None:
        if _looks_like_phone(query):
            return _normalize_phone(query)
        contact = self.find(query)
        return contact.phone if contact and contact.phone else None

    def resolve_email(self, query: str) -> str | None:
        if "@" in query:
            return query.strip()
        contact = self.find(query)
        return contact.email if contact and contact.email else None


def _looks_like_phone(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return len(digits) >= 7 and re.fullmatch(r"[\d+\-\s()]+", value.strip()) is not None


def _normalize_phone(value: str) -> str:
    value = value.strip()
    if value.startswith("+"):
        return "+" + re.sub(r"\D", "", value)
    return re.sub(r"\D", "", value)
