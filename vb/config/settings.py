from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PACKAGE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PACKAGE_DIR.parent


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    assistant_name: str = "VB"
    log_level: str = "INFO"
    confirm_sensitive_actions: bool = True
    default_location_name: str = "Kigali"
    default_latitude: float = -1.9441
    default_longitude: float = 30.0619
    ai_provider: str = "ollama"
    ai_base_url: str = "http://127.0.0.1:11434"
    ai_model: str = "llama3.2"
    vision_model: str = ""
    ai_timeout: int = 60
    ai_temperature: float = 0.4
    voice_enabled: bool = False
    stt_engine: str = "none"
    tts_engine: str = "pyttsx3"
    vosk_model_path: str = ""
    tts_rate: int = 175
    wake_word: str = "vb"
    sim808_enabled: bool = True
    sim808_port: str = "COM3"
    sim808_baudrate: int = 115200
    sim808_timeout: int = 2
    gps_poll_seconds: int = 3
    email_imap_host: str = ""
    email_imap_port: int = 993
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_from: str = ""
    email_mailbox: str = "INBOX"
    weather_timeout: int = 10
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    osrm_url: str = "https://router.project-osrm.org"
    maps_user_agent: str = "VB-local-assistant/1.0"
    camera_index: int = 0
    capture_dir: Path = field(default_factory=lambda: PACKAGE_DIR / "captures")
    contacts_path: Path = field(default_factory=lambda: PACKAGE_DIR / "data" / "contacts.json")
    permissions: dict[str, bool] = field(default_factory=dict)
    confirm: dict[str, bool] = field(default_factory=dict)
    allowed_apps: dict[str, str] = field(default_factory=dict)
    allowed_roots: list[Path] = field(default_factory=list)
    browser_headless: bool = False
    browser_timeout_ms: int = 15000

    @property
    def package_dir(self) -> Path:
        return PACKAGE_DIR


def load_settings(config_path: Path | None = None) -> Settings:
    load_dotenv(PACKAGE_DIR / ".env")
    load_dotenv(PROJECT_ROOT / ".env")
    path = config_path or PACKAGE_DIR / "config.yaml"
    raw: dict[str, Any] = {}
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}

    ai = raw.get("ai") or {}
    voice = raw.get("voice") or {}
    sim = raw.get("sim808") or {}
    email = raw.get("email") or {}
    maps = raw.get("maps") or {}
    camera = raw.get("camera") or {}
    desktop = raw.get("desktop") or {}
    loc = raw.get("default_location") or {}
    browser = raw.get("browser") or {}

    settings = Settings(
        assistant_name=str(raw.get("assistant_name", "VB")),
        log_level=str(raw.get("log_level", "INFO")),
        confirm_sensitive_actions=_as_bool(raw.get("confirm_sensitive_actions"), True),
        default_location_name=str(loc.get("name", "Kigali")),
        default_latitude=float(loc.get("latitude", -1.9441)),
        default_longitude=float(loc.get("longitude", 30.0619)),
        ai_provider=str(ai.get("provider", "ollama")),
        ai_base_url=os.getenv("OLLAMA_BASE_URL", str(ai.get("base_url", "http://127.0.0.1:11434"))),
        ai_model=os.getenv("VB_AI_MODEL", str(ai.get("model", "llama3.2"))),
        vision_model=str(ai.get("vision_model", "") or ""),
        ai_timeout=int(ai.get("timeout_seconds", 60)),
        ai_temperature=float(ai.get("temperature", 0.4)),
        voice_enabled=_as_bool(voice.get("enabled"), False),
        stt_engine=str(voice.get("stt_engine", "none")),
        tts_engine=str(voice.get("tts_engine", "pyttsx3")),
        vosk_model_path=str(voice.get("vosk_model_path", "") or ""),
        tts_rate=int(voice.get("rate", 175)),
        wake_word=str(voice.get("wake_word", "vb")),
        sim808_enabled=_as_bool(sim.get("enabled"), True),
        sim808_port=os.getenv("SIM808_PORT", str(sim.get("port", "COM3"))),
        sim808_baudrate=int(os.getenv("SIM808_BAUDRATE", sim.get("baudrate", 115200))),
        sim808_timeout=int(sim.get("timeout", 2)),
        gps_poll_seconds=int(sim.get("gps_poll_seconds", 3)),
        email_imap_host=os.getenv("EMAIL_IMAP_HOST", str(email.get("imap_host", "") or "")),
        email_imap_port=int(email.get("imap_port", 993)),
        email_smtp_host=os.getenv("EMAIL_SMTP_HOST", str(email.get("smtp_host", "") or "")),
        email_smtp_port=int(email.get("smtp_port", 587)),
        email_username=os.getenv("EMAIL_USERNAME", str(email.get("username", "") or "")),
        email_password=os.getenv("EMAIL_PASSWORD", ""),
        email_from=os.getenv("EMAIL_FROM", str(email.get("from_address", "") or "")),
        email_mailbox=str(email.get("mailbox", "INBOX")),
        weather_timeout=int((raw.get("weather") or {}).get("timeout_seconds", 10)),
        nominatim_url=str(maps.get("nominatim_url", "https://nominatim.openstreetmap.org")),
        osrm_url=str(maps.get("osrm_url", "https://router.project-osrm.org")),
        maps_user_agent=str(maps.get("user_agent", "VB-local-assistant/1.0")),
        camera_index=int(camera.get("index", 0)),
        capture_dir=PACKAGE_DIR / str(camera.get("capture_dir", "captures")),
        permissions=dict(raw.get("permissions") or {}),
        confirm=dict(raw.get("confirm") or {}),
        allowed_apps={str(k).lower(): str(v) for k, v in (desktop.get("allowed_apps") or {}).items()},
        allowed_roots=[Path(p).expanduser() for p in (desktop.get("allowed_roots") or [])],
        browser_headless=_as_bool(browser.get("headless"), False),
        browser_timeout_ms=int(browser.get("timeout_ms", 15000)),
    )
    return settings
