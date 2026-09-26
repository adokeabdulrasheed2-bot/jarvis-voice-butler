from __future__ import annotations

import logging
from dataclasses import dataclass

from vb.ai.assistant import LocalAI
from vb.ai.router import Intent, route_intent
from vb.config.settings import Settings
from vb.data.contacts import ContactBook
from vb.hardware.sim808_manager import Sim808Manager
from vb.security.permissions import ActionCancelled, PermissionDenied, PermissionGate
from vb.tools import browser, calculator, calls, camera, desktop, email, gps, navigation, sms, vision, weather

logger = logging.getLogger("vb.runtime")


@dataclass
class ToolRuntime:
    settings: Settings
    ai: LocalAI
    sim: Sim808Manager
    contacts: ContactBook
    gate: PermissionGate

    def handle(self, text: str) -> str:
        route = route_intent(text)
        try:
            result = self._dispatch(route.intent, route.text)
        except PermissionDenied as exc:
            return str(exc)
        except ActionCancelled as exc:
            return str(exc)
        except Exception as exc:
            logger.exception("Tool failure")
            return f"That action failed: {exc}"
        if route.intent == Intent.LOCAL_AI:
            return result
        return result

    def _dispatch(self, intent: Intent, text: str) -> str:
        if intent == Intent.CALCULATOR:
            return calculator.calculate(text)
        if intent == Intent.WEATHER:
            return weather.handle_weather(self.settings, self.sim)
        if intent == Intent.SMS:
            return sms.handle_sms(text, self.sim, self.contacts, self.gate)
        if intent == Intent.CALL:
            return calls.handle_call(text, self.sim, self.contacts, self.gate)
        if intent == Intent.GPS:
            reply = gps.handle_gps(self.sim, self.gate)
            fix = self.sim.get_gps(force=False)
            if fix.valid and fix.latitude is not None:
                place = navigation.reverse_geocode(self.settings, fix.latitude, fix.longitude)
                if place:
                    reply += f" Approximate place: {place}."
            return reply
        if intent == Intent.NAVIGATION:
            return navigation.handle_navigation(text, self.settings, self.sim, self.gate)
        if intent == Intent.EMAIL:
            return email.handle_email(text, self.settings, self.contacts, self.gate)
        if intent == Intent.CAMERA:
            _, status = camera.capture_photo(self.settings, self.gate)
            return status
        if intent == Intent.VISION:
            return vision.analyze_image(self.settings, self.ai, self.gate)
        if intent == Intent.DESKTOP:
            return desktop.handle_desktop(text, self.settings, self.gate)
        if intent == Intent.WEB:
            return browser.handle_web(text, self.settings, self.gate)
        if intent == Intent.GSM_STATUS:
            info = self.sim.module_info()
            return str(info)
        if intent == Intent.SYSTEM:
            self.gate.require("SYSTEM_COMMANDS")
            return "Arbitrary system commands are disabled. Use allowlisted desktop tools."
        return self.ai.answer(text)
