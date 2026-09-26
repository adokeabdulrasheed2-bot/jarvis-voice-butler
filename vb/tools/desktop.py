from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from vb.config.settings import Settings
from vb.security.permissions import PermissionGate

logger = logging.getLogger("vb.desktop")


def handle_desktop(text: str, settings: Settings, gate: PermissionGate) -> str:
    gate.require("DESKTOP_CONTROL")
    lowered = text.lower()
    if lowered.startswith("close "):
        return _close(text, settings)
    app = _app_name(text)
    if app:
        command = settings.allowed_apps.get(app)
        if not command:
            return f"{app} is not in the allowed applications list."
        return _launch(command)
    path = _path_in_text(text)
    if path:
        gate.require("FILESYSTEM")
        return _open_path(path, settings, gate)
    return "I can open allowlisted apps such as Calculator or VS Code, or files under allowed roots."


def _app_name(text: str) -> str:
    match = re.search(
        r"\b(?:open|launch|start|close)\s+(?:the\s+)?(.+?)(?:\s+app(?:lication)?)?$",
        text.strip(),
        re.I,
    )
    if not match:
        return ""
    name = match.group(1).strip(" .").lower()
    name = re.sub(r"^(the\s+)", "", name)
    return name


def _launch(command: str) -> str:
    executable = shutil.which(command) or command
    try:
        if sys.platform == "win32":
            os.startfile(executable)  # type: ignore[attr-defined]
        else:
            subprocess.Popen([executable], start_new_session=True)
        return f"Opened {command}."
    except Exception as exc:
        return f"Could not open {command}: {exc}"


def _close(text: str, settings: Settings) -> str:
    app = _app_name(text.replace("close", "open", 1))
    command = settings.allowed_apps.get(app)
    if not command:
        return f"{app} is not in the allowed applications list."
    if sys.platform == "win32":
        image = Path(command).name
        if not image.endswith(".exe"):
            image = f"{image}.exe"
        try:
            subprocess.run(["taskkill", "/IM", image], check=False, capture_output=True)
            return f"Asked Windows to close {image}."
        except Exception as exc:
            return str(exc)
    return "Close is only implemented for Windows process names in this version."


def _path_in_text(text: str) -> str:
    match = re.search(r"(?:open|folder|file)\s+(.+)$", text, re.I)
    return match.group(1).strip(" .") if match else ""


def _open_path(raw: str, settings: Settings, gate: PermissionGate) -> str:
    path = Path(raw).expanduser()
    if not path.exists():
        return f"{path} does not exist."
    if settings.allowed_roots:
        resolved = path.resolve()
        if not any(_is_relative_to(resolved, root.resolve()) for root in settings.allowed_roots):
            return "That path is outside the allowed filesystem roots."
    gate.confirm("FILESYSTEM", f"Open {path}?")
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return f"Opened {path}."
    except Exception as exc:
        return str(exc)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
