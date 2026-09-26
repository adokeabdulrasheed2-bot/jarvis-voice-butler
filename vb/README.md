# VB — local-first desktop assistant

VB is a modular, local-first assistant. It answers ordinary questions with a local LLM (Ollama), and uses dedicated tools for GSM/SMS/calls/GPS (SIM808), weather, email, camera, and allowlisted desktop apps.

The older LiveKit/Gemini butler remains in `jarvis_new/` as a reference. It is **not** the VB runtime.

## Architecture

```text
Voice or text
    → intent router
        → LOCAL_AI | CALCULATOR | WEATHER | SMS | CALL | GPS | ...
            → specialized tool
                → SIM808 / APIs / local services
                    → spoken or printed reply
```

Normal questions never open a browser.

## Setup

```powershell
cd C:\ado\jarvis-voice-butler
python -m venv .venv
.\.venv\Scripts\activate
pip install -r vb\requirements.txt
copy vb\.env.example vb\.env
```

Install [Ollama](https://ollama.com) and pull a small model:

```powershell
ollama pull llama3.2
```

Edit `vb/config.yaml` and `vb/.env`:

- `SIM808_PORT` — `COM3` on Windows, `/dev/serial0` or `/dev/ttyUSB0` on Raspberry Pi/Linux
- `SIM808_BAUDRATE` — `115200` (same as `sim_app.py`)
- Email credentials via environment variables only
- Contacts in `vb/data/contacts.json` (do not hardcode in Python)

## Run

From the repository root:

```powershell
python -m vb --text
python -m vb where am I
python -m vb --voice
```

`--voice` needs `voice.enabled: true` and a Vosk model path in `config.yaml`.

## SIM808

`vb/hardware/sim808_manager.py` reuses the working AT sequences from `C:\sim_app.py`:

- GPS: `AT+CGPS=1`, `AT+CGPSINFO` (background worker, thread lock)
- Voice call: `ATD{number};`, hangup `AT+CHUP`
- SMS: `AT+CMGF=1`, `AT+CMGS`, Ctrl-Z

Flask was not copied. VB talks to the module through the manager, not a web dashboard.

If the serial port is missing, VB still answers local questions.

## Tests

```powershell
pip install pytest
python -m pytest vb\tests -q
```

These tests do **not** require SIM808 hardware, Ollama, a camera, or internet.

## Status

| Feature | Status |
|---|---|
| Intent routing | WORKING (unit tested) |
| Calculator | WORKING (unit tested) |
| Local AI (Ollama) | REQUIRES local Ollama + model |
| SIM808 connect / GSM / SMS / calls / GPS | REQUIRES HARDWARE |
| Weather (Open-Meteo) | REQUIRES INTERNET |
| Maps / routing (Nominatim, OSRM) | REQUIRES INTERNET |
| Email IMAP/SMTP | REQUIRES credentials |
| Camera | REQUIRES webcam + OpenCV |
| Vision analysis | REQUIRES vision model |
| Desktop apps | PARTIALLY WORKING (allowlist; Windows `os.startfile`) |
| Browser | Only on explicit web intent |
| Voice STT | NOT TESTED on this machine (Vosk optional) |
| Voice TTS | PARTIALLY WORKING (pyttsx3 if installed) |

Never claimed hardware-tested unless a SIM808 was attached to this session (it was not).
