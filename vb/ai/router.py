from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    LOCAL_AI = "LOCAL_AI"
    CALCULATOR = "CALCULATOR"
    WEB = "WEB"
    WEATHER = "WEATHER"
    EMAIL = "EMAIL"
    SMS = "SMS"
    CALL = "CALL"
    GPS = "GPS"
    NAVIGATION = "NAVIGATION"
    CAMERA = "CAMERA"
    VISION = "VISION"
    DESKTOP = "DESKTOP"
    SYSTEM = "SYSTEM"
    GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
    GSM_STATUS = "GSM_STATUS"


@dataclass
class Route:
    intent: Intent
    text: str
    confidence: float = 1.0


_PATTERNS: list[tuple[Intent, re.Pattern[str]]] = [
    (Intent.CALL, re.compile(r"\b(answer|reject|hang\s*up|end\s+(the\s+)?call|dial|call)\b", re.I)),
    (Intent.SMS, re.compile(r"\b(sms|text message|text|messages?)\b", re.I)),
    (Intent.EMAIL, re.compile(r"\b(e-?mail|inbox)\b", re.I)),
    (Intent.WEATHER, re.compile(r"\b(weather|temperature|forecast|humidity|wind)\b", re.I)),
    (Intent.NAVIGATION, re.compile(r"\b(navigate|navigation|directions?|how far|nearest|route to)\b", re.I)),
    (Intent.GPS, re.compile(r"\b(where am i|coordinates?|gps|location|latitude|longitude)\b", re.I)),
    (Intent.GSM_STATUS, re.compile(r"\b(signal|operator|imei|sim status|network registration|gsm)\b", re.I)),
    (Intent.CAMERA, re.compile(r"\b(take a (photo|picture)|capture|camera)\b", re.I)),
    (Intent.VISION, re.compile(r"\b(what(?:'s| is) in front|analyze (this |the )?image|describe (the )?(photo|picture|image))\b", re.I)),
    (Intent.WEB, re.compile(r"\b(search the web|google|open (the )?browser|browse|look up online)\b", re.I)),
    (Intent.DESKTOP, re.compile(r"\b(open|launch|close|start)\b.+\b(app|application|calculator|notepad|chrome|edge|vs ?code|explorer|folder|file)\b", re.I)),
    (Intent.DESKTOP, re.compile(r"\b(open|launch|close)\s+(calculator|notepad|chrome|edge|vs ?code|explorer)\b", re.I)),
    (Intent.SYSTEM, re.compile(r"\b(run command|system command)\b", re.I)),
    (Intent.CALCULATOR, re.compile(r"\bcalculate\b|what(?:'s| is)\s+[\d(]|[\d.]+\s*[x×*/+\-]\s*[\d.]", re.I)),
]


def route_intent(text: str) -> Route:
    cleaned = text.strip()
    cleaned = re.sub(r"^\s*(vb|v\.b\.)[,:\s]+", "", cleaned, flags=re.I)
    for intent, pattern in _PATTERNS:
        if pattern.search(cleaned):
            return Route(intent=intent, text=cleaned)
    if re.search(r"^\s*[\d().\s+\-*/x×÷]+\s*$", cleaned):
        return Route(intent=Intent.CALCULATOR, text=cleaned)
    return Route(intent=Intent.LOCAL_AI, text=cleaned)
