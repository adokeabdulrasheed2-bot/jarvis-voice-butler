from __future__ import annotations

import logging
import re

import requests

from vb.config.settings import Settings
from vb.hardware.sim808_manager import Sim808Manager
from vb.security.permissions import PermissionGate
from vb.tools.gps import coordinates_or_default, handle_gps

logger = logging.getLogger("vb.navigation")


def handle_navigation(text: str, settings: Settings, sim: Sim808Manager, gate: PermissionGate) -> str:
    gate.require("GPS")
    lat, lon, source = coordinates_or_default(
        sim, settings.default_latitude, settings.default_longitude
    )
    destination = _destination(text)
    if not destination:
        return handle_gps(sim, gate)
    dest = _geocode(settings, destination)
    if not dest:
        return f"I could not geocode {destination}. This needs internet."
    dlat, dlon, label = dest
    route = _route(settings, lat, lon, dlat, dlon)
    if not route:
        return (
            f"You are using {source} at {lat:.5f}, {lon:.5f}. "
            f"{label} is at {dlat:.5f}, {dlon:.5f}. Routing is unavailable."
        )
    km, minutes = route
    return (
        f"From {source} ({lat:.5f}, {lon:.5f}) to {label}: "
        f"about {km:.1f} kilometres, roughly {minutes:.0f} minutes by road."
    )


def _destination(text: str) -> str:
    match = re.search(
        r"(?:to|towards|near(?:est)?)\s+(.+)$",
        text,
        re.I,
    )
    if match:
        return match.group(1).strip(" .?")
    match = re.search(r"how far is\s+(.+?)(?:\s+from here)?$", text, re.I)
    if match:
        return match.group(1).strip(" .?")
    return ""


def _geocode(settings: Settings, query: str) -> tuple[float, float, str] | None:
    try:
        response = requests.get(
            f"{settings.nominatim_url.rstrip('/')}/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": settings.maps_user_agent},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            return None
        item = data[0]
        return float(item["lat"]), float(item["lon"]), item.get("display_name", query)
    except requests.RequestException as exc:
        logger.warning("Geocode failed: %s", exc)
        return None


def reverse_geocode(settings: Settings, lat: float, lon: float) -> str | None:
    try:
        response = requests.get(
            f"{settings.nominatim_url.rstrip('/')}/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": settings.maps_user_agent},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("display_name")
    except requests.RequestException:
        return None


def _route(settings: Settings, lat: float, lon: float, dlat: float, dlon: float) -> tuple[float, float] | None:
    url = f"{settings.osrm_url.rstrip('/')}/route/v1/driving/{lon},{lat};{dlon},{dlat}"
    try:
        response = requests.get(url, params={"overview": "false"}, timeout=10)
        response.raise_for_status()
        routes = response.json().get("routes") or []
        if not routes:
            return None
        meters = routes[0]["distance"]
        seconds = routes[0]["duration"]
        return meters / 1000.0, seconds / 60.0
    except requests.RequestException as exc:
        logger.warning("Routing failed: %s", exc)
        return None
