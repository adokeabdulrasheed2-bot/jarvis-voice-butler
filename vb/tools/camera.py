from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from vb.config.settings import Settings
from vb.security.permissions import PermissionGate

logger = logging.getLogger("vb.camera")


def capture_photo(settings: Settings, gate: PermissionGate) -> tuple[Path | None, str]:
    gate.require("CAMERA")
    try:
        import cv2
    except ImportError:
        return None, "OpenCV is not installed, so the camera cannot be used."
    settings.capture_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(settings.camera_index)
    try:
        if not cap.isOpened():
            return None, f"Camera index {settings.camera_index} is not available."
        ok, frame = cap.read()
        if not ok:
            return None, "The camera opened but did not return a frame."
        path = settings.capture_dir / f"vb-{datetime.now().strftime('%Y%m%d-%H%M%S')}.jpg"
        cv2.imwrite(str(path), frame)
        return path, f"Photo saved to {path}."
    finally:
        cap.release()
