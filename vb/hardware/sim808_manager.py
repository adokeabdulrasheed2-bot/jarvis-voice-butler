from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from vb.config.settings import Settings

logger = logging.getLogger("vb.sim808")

try:
    import serial
except ImportError:  # pragma: no cover
    serial = None  # type: ignore[assignment]


class Sim808Error(Exception):
    pass


@dataclass
class GpsFix:
    valid: bool
    raw: str
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    speed_kmh: float | None = None
    course_deg: float | None = None
    timestamp: str | None = None
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude_m": self.altitude_m,
            "speed_kmh": self.speed_kmh,
            "course_deg": self.course_deg,
            "timestamp": self.timestamp,
            "raw": self.raw,
            "message": self.message,
        }


@dataclass
class SmsMessage:
    index: str
    status: str
    sender: str
    timestamp: str
    body: str


@dataclass
class Sim808Manager:
    """Persistent SIM808 serial client.

    AT command sequences are taken from sim_app.py (GPS power, CGPSINFO,
    ATD voice dial, AT+CHUP hangup, CMGF/CMGS SMS) and extended with
    status, inbox, and call-control commands. Flask HTTP is not used.
    """

    settings: Settings
    on_sms: Callable[[str], None] | None = None
    on_call: Callable[[str], None] | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _port: Any = None
    _gps_thread: threading.Thread | None = field(default=None, init=False)
    _gps_active: bool = field(default=False, init=False)
    last_gps: GpsFix = field(
        default_factory=lambda: GpsFix(valid=False, raw="", message="GPS not started")
    )
    last_error: str | None = None
    incoming_events: list[str] = field(default_factory=list)

    def connect(self) -> bool:
        if serial is None:
            self.last_error = "pyserial is not installed"
            logger.warning(self.last_error)
            return False
        try:
            self._port = serial.Serial(
                self.settings.sim808_port,
                self.settings.sim808_baudrate,
                timeout=self.settings.sim808_timeout,
            )
            time.sleep(1)
            probe = self.send_at("AT", wait_time=1)
            if "OK" not in probe.upper():
                self.last_error = f"No AT OK from {self.settings.sim808_port}: {probe!r}"
                logger.warning(self.last_error)
            else:
                self.last_error = None
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self._port = None
            logger.warning("Failed to open SIM808 port %s: %s", self.settings.sim808_port, exc)
            return False

    @property
    def connected(self) -> bool:
        return self._port is not None and getattr(self._port, "is_open", False)

    def close(self) -> None:
        self._gps_active = False
        if self._gps_thread and self._gps_thread.is_alive():
            self._gps_thread.join(timeout=2)
        if self._port is not None:
            try:
                self._port.close()
            except Exception:
                logger.debug("Error closing serial port", exc_info=True)
            self._port = None

    def send_at(self, command: str, wait_time: float = 2) -> str:
        """Thread-safe AT send; same lock + write + sleep + read_all pattern as sim_app.py."""
        if not self.connected:
            raise Sim808Error(self.last_error or "SIM808 is not connected")
        with self._lock:
            self._port.reset_input_buffer()
            self._port.write((command + "\r\n").encode())
            time.sleep(wait_time)
            response = self._port.read_all().decode(errors="ignore")
        self._note_urc(response)
        return response

    def command_ok(self, command: str, wait_time: float = 2) -> tuple[bool, str]:
        try:
            response = self.send_at(command, wait_time)
        except Sim808Error as exc:
            return False, str(exc)
        ok = "OK" in response.upper() and "ERROR" not in response.upper()
        return ok, response

    def module_info(self) -> dict[str, str]:
        info = {
            "connected": str(self.connected),
            "port": self.settings.sim808_port,
            "baudrate": str(self.settings.sim808_baudrate),
        }
        if not self.connected:
            info["error"] = self.last_error or "not connected"
            return info
        mapping = {
            "ati": "ATI",
            "imei": "AT+CGSN",
            "sim": "AT+CPIN?",
            "registration": "AT+CREG?",
            "signal": "AT+CSQ",
            "operator": "AT+COPS?",
        }
        for key, cmd in mapping.items():
            try:
                info[key] = self.send_at(cmd, 1).strip()
            except Sim808Error as exc:
                info[key] = str(exc)
        return info

    def start_gps(self) -> None:
        if not self.connected:
            self.last_gps = GpsFix(valid=False, raw="", message="SIM808 not connected")
            return
        if self._gps_thread and self._gps_thread.is_alive():
            return
        self._gps_active = True
        self._gps_thread = threading.Thread(target=self._gps_worker, daemon=True)
        self._gps_thread.start()

    def _gps_worker(self) -> None:
        logger.info("Starting GPS background tracker")
        try:
            self.send_at("AT+CGPS=1", 3)
        except Sim808Error as exc:
            self.last_gps = GpsFix(valid=False, raw="", message=str(exc))
            return
        while self._gps_active:
            try:
                resp = self.send_at("AT+CGPSINFO", 2)
                self.last_gps = parse_cgpsinfo(resp)
            except Sim808Error as exc:
                self.last_gps = GpsFix(valid=False, raw="", message=str(exc))
            time.sleep(self.settings.gps_poll_seconds)

    def get_gps(self, *, force: bool = False) -> GpsFix:
        if force and self.connected:
            try:
                resp = self.send_at("AT+CGPSINFO", 2)
                self.last_gps = parse_cgpsinfo(resp)
            except Sim808Error as exc:
                self.last_gps = GpsFix(valid=False, raw="", message=str(exc))
        return self.last_gps

    def send_sms(self, number: str, message: str) -> tuple[bool, str]:
        if not self.connected:
            return False, self.last_error or "SIM808 is not connected"
        try:
            with self._lock:
                self._port.write(b"AT+CMGF=1\r\n")
                time.sleep(1)
                self._port.write(f'AT+CMGS="{number}"\r\n'.encode())
                time.sleep(1)
                self._port.write((message + "\x1A").encode())
                time.sleep(4)
                response = self._port.read_all().decode(errors="ignore")
        except Exception as exc:
            return False, str(exc)
        success = "+CMGS" in response.upper() or "OK" in response.upper()
        if "ERROR" in response.upper():
            success = False
        return success, response.strip() or ("SMS accepted" if success else "No confirmation from module")

    def list_sms(self, which: str = "ALL") -> list[SmsMessage]:
        ok, response = self.command_ok("AT+CMGF=1", 1)
        if not ok:
            raise Sim808Error(response)
        response = self.send_at(f'AT+CMGL="{which}"', 3)
        return parse_cmgl(response)

    def read_sms(self, index: int) -> SmsMessage | None:
        self.send_at("AT+CMGF=1", 1)
        response = self.send_at(f"AT+CMGR={index}", 2)
        messages = parse_cmgl(response.replace("+CMGR:", f'+CMGL: {index},'))
        return messages[0] if messages else None

    def delete_sms(self, index: int) -> tuple[bool, str]:
        return self.command_ok(f"AT+CMGD={index}", 2)

    def dial(self, number: str) -> tuple[bool, str]:
        response = self.send_at(f"ATD{number};", 1)
        failed = "ERROR" in response.upper() or "NO CARRIER" in response.upper()
        return (not failed), response.strip()

    def hangup(self) -> tuple[bool, str]:
        return self.command_ok("AT+CHUP", 2)

    def answer(self) -> tuple[bool, str]:
        return self.command_ok("ATA", 2)

    def reject(self) -> tuple[bool, str]:
        return self.hangup()

    def _note_urc(self, response: str) -> None:
        if "RING" in response.upper():
            clip = _extract_clip(response)
            event = f"Incoming call {clip or ''}".strip()
            self.incoming_events.append(event)
            if self.on_call:
                self.on_call(event)
        if "+CMTI" in response.upper():
            event = "New SMS received"
            self.incoming_events.append(event)
            if self.on_sms:
                self.on_sms(event)


def parse_cgpsinfo(response: str) -> GpsFix:
    """Parse SIM808 +CGPSINFO: lat,N/S,lon,E/W,date,utc,alt,speed,course"""
    line = ""
    for candidate in response.splitlines():
        if "+CGPSINFO:" in candidate.upper():
            line = candidate
            break
    if not line:
        return GpsFix(valid=False, raw=response.strip(), message="No GPS fix or reading error.")
    payload = line.split(":", 1)[1].strip()
    if not payload or payload.replace(",", "") == "":
        return GpsFix(
            valid=False,
            raw=payload,
            message="GPS FIX NOT AVAILABLE. Searching for satellites.",
        )
    parts = [p.strip() for p in payload.split(",")]
    while len(parts) < 9:
        parts.append("")
    lat_raw, ns, lon_raw, ew, date, utc, alt, speed, course = parts[:9]
    if not lat_raw or not lon_raw:
        return GpsFix(
            valid=False,
            raw=payload,
            message="GPS FIX NOT AVAILABLE. Searching for satellites.",
        )
    try:
        latitude = nmea_to_decimal(lat_raw, ns)
        longitude = nmea_to_decimal(lon_raw, ew)
    except ValueError:
        return GpsFix(valid=False, raw=payload, message="GPS data could not be parsed.")
    timestamp = None
    if date and utc:
        timestamp = f"{date} {utc} UTC"
    return GpsFix(
        valid=True,
        raw=payload,
        latitude=latitude,
        longitude=longitude,
        altitude_m=_to_float(alt),
        speed_kmh=_to_float(speed),
        course_deg=_to_float(course),
        timestamp=timestamp,
        message="GPS FIX AVAILABLE",
    )


def nmea_to_decimal(raw: str, hemisphere: str) -> float:
    hemisphere = hemisphere.upper()
    if hemisphere in {"N", "S"}:
        degrees = int(raw[:2])
        minutes = float(raw[2:])
    else:
        degrees = int(raw[:3])
        minutes = float(raw[3:])
    value = degrees + minutes / 60.0
    if hemisphere in {"S", "W"}:
        value = -value
    return value


def parse_cmgl(response: str) -> list[SmsMessage]:
    messages: list[SmsMessage] = []
    blocks = re.split(r"\r?\n(?=\+CMGL:)", response)
    for block in blocks:
        if "+CMGL:" not in block:
            continue
        header, *body_lines = block.splitlines()
        match = re.search(
            r'\+CMGL:\s*(\d+)\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"(?:\s*,\s*"([^"]*)")?(?:\s*,\s*"([^"]*)")?',
            header,
        )
        if not match:
            continue
        index, status, sender, field4, field5 = match.groups()
        timestamp = field5 or field4 or ""
        body = "\n".join(line for line in body_lines if line.strip() and line.strip() != "OK")
        messages.append(
            SmsMessage(
                index=index,
                status=status,
                sender=sender,
                timestamp=timestamp,
                body=body.strip(),
            )
        )
    return messages


def _to_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _extract_clip(response: str) -> str:
    match = re.search(r'\+CLIP:\s*"([^"]+)"', response)
    return match.group(1) if match else ""
