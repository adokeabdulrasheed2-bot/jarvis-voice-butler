from __future__ import annotations

import base64
from pathlib import Path

from vb.ai.assistant import LocalAI
from vb.config.settings import Settings
from vb.security.permissions import PermissionGate
from vb.tools.camera import capture_photo


def analyze_image(settings: Settings, ai: LocalAI, gate: PermissionGate, path: Path | None = None) -> str:
    if path is None:
        path, status = capture_photo(settings, gate)
        if path is None:
            return status
    if not settings.vision_model:
        return f"Image saved at {path}. Configure ai.vision_model for local vision analysis."
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return ai.analyze_image("Describe what is in this camera image for VB.", data)
