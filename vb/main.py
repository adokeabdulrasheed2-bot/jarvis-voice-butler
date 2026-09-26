from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vb.ai.assistant import LocalAI
from vb.config.settings import load_settings
from vb.data.contacts import ContactBook
from vb.hardware.sim808_manager import Sim808Manager
from vb.security.permissions import PermissionGate
from vb.tools.runtime import ToolRuntime
from vb.voice.text_to_speech import SpeechToText, TextToSpeech


def _setup_logging(level: str) -> None:
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "vb.log", encoding="utf-8"),
        ],
    )


def _confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def build_runtime(voice: bool = False) -> tuple[ToolRuntime, TextToSpeech, SpeechToText]:
    settings = load_settings()
    _setup_logging(settings.log_level)
    ai = LocalAI(settings)
    contacts = ContactBook(settings.contacts_path)
    sim = Sim808Manager(settings)
    if settings.sim808_enabled:
        if sim.connect() and sim.last_error is None:
            sim.start_gps()
        else:
            logging.getLogger("vb").warning("SIM808 unavailable; local tools still work.")
    gate = PermissionGate(settings, confirm_fn=_confirm)
    runtime = ToolRuntime(settings, ai, sim, contacts, gate)
    tts = TextToSpeech(settings) if (voice or settings.voice_enabled) else TextToSpeech(settings)
    stt = SpeechToText(settings)
    return runtime, tts, stt


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="VB local-first desktop assistant")
    parser.add_argument("--text", action="store_true", help="Text REPL (default)")
    parser.add_argument("--voice", action="store_true", help="Microphone + TTS loop")
    parser.add_argument("utterance", nargs="*", help="Single command then exit")
    args = parser.parse_args(argv)

    runtime, tts, stt = build_runtime(voice=args.voice)
    print("VB ready. Local AI, tools, and optional SIM808. Type quit to exit.")

    def once(text: str) -> None:
        reply = runtime.handle(text)
        print(f"VB: {reply}")
        if args.voice or runtime.settings.voice_enabled:
            tts.speak(reply)

    if args.utterance:
        once(" ".join(args.utterance))
        runtime.sim.close()
        return

    try:
        while True:
            if args.voice:
                try:
                    user = stt.listen_once()
                    print(f"You: {user}")
                except RuntimeError as exc:
                    print(exc)
                    break
            else:
                try:
                    user = input("You: ").strip()
                except EOFError:
                    break
            if not user:
                continue
            if user.lower() in {"quit", "exit", "goodbye"}:
                print("VB: Goodbye.")
                break
            once(user)
    finally:
        runtime.sim.close()


if __name__ == "__main__":
    main()
