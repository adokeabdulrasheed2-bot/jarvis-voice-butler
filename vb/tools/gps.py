from __future__ import annotations

from vb.hardware.sim808_manager import GpsFix, Sim808Manager
from vb.security.permissions import PermissionGate


def handle_gps(sim: Sim808Manager, gate: PermissionGate, *, force: bool = True) -> str:
    gate.require("GPS")
    fix = sim.get_gps(force=force)
    return format_fix(fix)


def format_fix(fix: GpsFix) -> str:
    if not fix.valid:
        return fix.message or "GPS FIX NOT AVAILABLE."
    parts = [
        "GPS FIX AVAILABLE.",
        f"Latitude {fix.latitude:.6f}, longitude {fix.longitude:.6f}.",
    ]
    if fix.altitude_m is not None:
        parts.append(f"Altitude {fix.altitude_m:.1f} metres.")
    if fix.speed_kmh is not None:
        parts.append(f"Speed {fix.speed_kmh:.1f} kilometres per hour.")
    if fix.course_deg is not None:
        parts.append(f"Course {fix.course_deg:.0f} degrees.")
    if fix.timestamp:
        parts.append(f"Timestamp {fix.timestamp}.")
    return " ".join(parts)


def coordinates_or_default(sim: Sim808Manager, lat: float, lon: float) -> tuple[float, float, str]:
    fix = sim.get_gps(force=True)
    if fix.valid and fix.latitude is not None and fix.longitude is not None:
        return fix.latitude, fix.longitude, "SIM808 GPS"
    return lat, lon, "configured default location"
