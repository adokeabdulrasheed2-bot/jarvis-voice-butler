from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from vb.config.settings import Settings


class PermissionDenied(Exception):
    pass


class ActionCancelled(Exception):
    pass


ConfirmFn = Callable[[str], bool]


@dataclass
class PermissionGate:
    settings: Settings
    confirm_fn: ConfirmFn | None = None

    def allowed(self, permission: str) -> bool:
        return bool(self.settings.permissions.get(permission, False))

    def require(self, permission: str) -> None:
        if not self.allowed(permission):
            raise PermissionDenied(f"{permission} is disabled in VB configuration.")

    def needs_confirm(self, permission: str) -> bool:
        if not self.settings.confirm_sensitive_actions:
            return False
        return bool(self.settings.confirm.get(permission, False))

    def confirm(self, permission: str, prompt: str) -> None:
        self.require(permission)
        if not self.needs_confirm(permission):
            return
        if self.confirm_fn is None:
            raise ActionCancelled("Confirmation is required but no prompt is available.")
        if not self.confirm_fn(prompt):
            raise ActionCancelled("Cancelled.")
