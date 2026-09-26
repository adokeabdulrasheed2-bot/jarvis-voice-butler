from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vb.ai.router import Intent, route_intent
from vb.config.settings import Settings
from vb.data.contacts import ContactBook
from vb.hardware.sim808_manager import parse_cgpsinfo, parse_cmgl
from vb.security.permissions import ActionCancelled, PermissionDenied, PermissionGate
from vb.tools.calculator import calculate


def test_local_questions_do_not_use_web() -> None:
    assert route_intent("VB, what is Python?").intent == Intent.LOCAL_AI
    assert route_intent("explain neural networks").intent == Intent.LOCAL_AI


def test_tool_intents() -> None:
    assert route_intent("calculate 25 × 48").intent == Intent.CALCULATOR
    assert route_intent("what's the weather").intent == Intent.WEATHER
    assert route_intent("send John an SMS saying hello").intent == Intent.SMS
    assert route_intent("call John").intent == Intent.CALL
    assert route_intent("where am I").intent == Intent.GPS
    assert route_intent("open VS Code").intent == Intent.DESKTOP
    assert route_intent("search the web for today's AI news").intent == Intent.WEB
    assert route_intent("take a picture").intent == Intent.CAMERA


def test_calculator() -> None:
    assert calculate("calculate 25 × 48") == "25 * 48 = 1200"


def test_calculator_question() -> None:
    assert route_intent("what is 25 x 48").intent == Intent.CALCULATOR


def test_gps_parser_no_fix() -> None:
    fix = parse_cgpsinfo("+CGPSINFO: ,,,,,,,,")
    assert fix.valid is False
    assert "NOT AVAILABLE" in fix.message


def test_gps_parser_fix() -> None:
    raw = "+CGPSINFO: 0156.1234,S,03003.5678,E,260926,181500.0,1500.0,0.5,90.0"
    fix = parse_cgpsinfo(raw)
    assert fix.valid is True
    assert fix.latitude is not None and fix.latitude < 0
    assert fix.longitude is not None and fix.longitude > 0
    assert fix.altitude_m == 1500.0


def test_sms_parser() -> None:
    sample = (
        '+CMGL: 1,"REC UNREAD","+250000000000","","26/09/26,18:00:00"\r\n'
        "Hello from VB\r\nOK\r\n"
    )
    messages = parse_cmgl(sample)
    assert len(messages) == 1
    assert messages[0].sender == "+250000000000"
    assert "Hello" in messages[0].body


def test_contacts(tmp_path: Path) -> None:
    path = tmp_path / "contacts.json"
    path.write_text(
        '{"contacts":[{"name":"John","aliases":["jon"],"phone":"+250111","email":"j@x.com"}]}',
        encoding="utf-8",
    )
    book = ContactBook(path)
    assert book.resolve_phone("John") == "+250111"
    assert book.resolve_email("jon") == "j@x.com"


def test_permissions_block() -> None:
    settings = Settings(permissions={"SMS": False}, confirm={"SMS": True})
    gate = PermissionGate(settings, confirm_fn=lambda _: True)
    with pytest.raises(PermissionDenied):
        gate.require("SMS")


def test_permissions_confirm() -> None:
    settings = Settings(
        permissions={"SMS": True},
        confirm={"SMS": True},
        confirm_sensitive_actions=True,
    )
    gate = PermissionGate(settings, confirm_fn=lambda _: False)
    with pytest.raises(ActionCancelled):
        gate.confirm("SMS", "Send?")
