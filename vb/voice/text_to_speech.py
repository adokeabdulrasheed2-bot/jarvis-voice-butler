from __future__ import annotations

import logging

from vb.config.settings import Settings

logger = logging.getLogger("vb.voice")


class TextToSpeech:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._engine = None
        if settings.tts_engine == "pyttsx3":
            try:
                import pyttsx3

                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", settings.tts_rate)
            except Exception as exc:
                logger.warning("TTS unavailable: %s", exc)

    def speak(self, text: str) -> None:
        if not self._engine:
            return
        self._engine.say(text)
        self._engine.runAndWait()


class SpeechToText:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def listen_once(self) -> str:
        engine = self.settings.stt_engine.lower()
        if engine in {"", "none"}:
            raise RuntimeError("Voice STT is disabled. Use text mode or configure voice.stt_engine.")
        if engine == "vosk":
            return self._vosk()
        raise RuntimeError(f"Unsupported STT engine: {engine}")

    def _vosk(self) -> str:
        if not self.settings.vosk_model_path:
            raise RuntimeError("Set voice.vosk_model_path for offline Vosk STT.")
        try:
            import json
            import queue

            import sounddevice as sd
            from vosk import KaldiRecognizer, Model
        except ImportError as exc:
            raise RuntimeError("Install vosk and sounddevice for offline STT.") from exc

        model = Model(self.settings.vosk_model_path)
        rec = KaldiRecognizer(model, 16000)
        audio: queue.Queue[bytes] = queue.Queue()

        def callback(indata, frames, time, status):  # type: ignore[no-untyped-def]
            audio.put(bytes(indata))

        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=callback):
            while True:
                data = audio.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        return text
