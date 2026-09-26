from __future__ import annotations

import logging

import requests

from vb.config.settings import Settings
from vb.hardware.sim808_manager import Sim808Manager
from vb.tools.gps import coordinates_or_default

logger = logging.getLogger("vb.weather")

WMO = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "rime fog",
    51: "light drizzle",
    61: "rain",
    71: "snow",
    80: "rain showers",
    95: "thunderstorm",
}


def handle_weather(settings: Settings, sim: Sim808Manager) -> str:
    lat, lon, source = coordinates_or_default(
        sim, settings.default_latitude, settings.default_longitude
    )
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,precipitation",
    }
    try:
        response = requests.get(url, params=params, timeout=settings.weather_timeout)
        response.raise_for_status()
        current = response.json().get("current") or {}
    except requests.RequestException as exc:
        return f"Weather is online-only and failed: {exc}"
    condition = WMO.get(int(current.get("weather_code") or 0), "unknown conditions")
    return (
        f"Weather near {source}: {condition}, "
        f"{current.get('temperature_2m')} degrees, feels like {current.get('apparent_temperature')}, "
        f"humidity {current.get('relative_humidity_2m')} percent, "
        f"wind {current.get('wind_speed_10m')} kilometres per hour, "
        f"precipitation {current.get('precipitation')} millimetres."
    )
