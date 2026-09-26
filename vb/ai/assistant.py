from __future__ import annotations

import logging
from typing import Any

import requests

from vb.ai.prompts import SYSTEM_PROMPT, TOOL_SUMMARY_PROMPT
from vb.config.settings import Settings

logger = logging.getLogger("vb.ai")


class LocalAI:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._session = requests.Session()

    def available(self) -> bool:
        try:
            response = self._session.get(f"{self.settings.ai_base_url}/api/tags", timeout=2)
            return response.ok
        except requests.RequestException:
            return False

    def answer(self, user_text: str, *, context: str | None = None) -> str:
        if not self.available():
            return (
                "The local AI is not running. Start Ollama or set VB_AI_MODEL, "
                "or ask a tool command such as weather, SMS, or calculator."
            )
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": user_text})
        return self._chat(messages)

    def summarize_tool(self, user_text: str, result: Any) -> str:
        if not self.available():
            return str(result)
        messages = [
            {"role": "system", "content": TOOL_SUMMARY_PROMPT},
            {"role": "user", "content": f"Request: {user_text}\nResult: {result}"},
        ]
        return self._chat(messages)

    def analyze_image(self, prompt: str, image_b64: str) -> str:
        model = self.settings.vision_model or self.settings.ai_model
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64],
                }
            ],
            "stream": False,
        }
        try:
            response = self._session.post(
                f"{self.settings.ai_base_url}/api/chat",
                json=payload,
                timeout=self.settings.ai_timeout,
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "").strip()
        except requests.RequestException as exc:
            logger.warning("Vision request failed: %s", exc)
            return f"I captured the image but could not analyze it: {exc}"

    def _chat(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.settings.ai_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.settings.ai_temperature},
        }
        try:
            response = self._session.post(
                f"{self.settings.ai_base_url}/api/chat",
                json=payload,
                timeout=self.settings.ai_timeout,
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "").strip()
        except requests.RequestException as exc:
            logger.warning("Local AI request failed: %s", exc)
            return f"The local AI request failed: {exc}"
