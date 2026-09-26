from __future__ import annotations

import logging
import webbrowser
from urllib.parse import quote_plus, urlparse

from vb.config.settings import Settings
from vb.security.permissions import PermissionGate

logger = logging.getLogger("vb.browser")

NAMED_SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "wikipedia": "https://www.wikipedia.org",
}


def handle_web(text: str, settings: Settings, gate: PermissionGate) -> str:
    gate.require("WEB_ACCESS")
    lowered = text.lower()
    for name, url in NAMED_SITES.items():
        if name in lowered and "search" not in lowered:
            return _open(url, gate)
    if "http://" in lowered or "https://" in lowered:
        url = next((part for part in text.split() if part.startswith("http")), "")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return "Only complete http or https URLs can be opened."
        return _open(url, gate)
    query = text
    for prefix in ("search the web for", "search the web", "google", "look up online"):
        if query.lower().startswith(prefix):
            query = query[len(prefix) :].strip(" .")
            break
    url = f"https://duckduckgo.com/?q={quote_plus(query)}"
    return _open(url, gate)


def _open(url: str, gate: PermissionGate) -> str:
    gate.confirm("WEB_ACCESS", f"Open browser to {url}?")
    webbrowser.open(url)
    return f"Opened the system browser to {url}."
