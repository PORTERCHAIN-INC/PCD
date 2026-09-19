"""Comms + AI gap fills: NIM stub path, sandbox notify tags, Twilio SMS config."""

from __future__ import annotations

from porterchain_api.intelligence_engine.copilot_service import (
    _normalize_action,
    _parse_suggestions,
    suggest_ops_action,
)
from porterchain_api.intelligence_engine.nim_client import nim_configured, nim_status
from porterchain_api.notification_engine.delivery_service import DeliveryService


def test_suggest_ops_action_phase2_disabled() -> None:
    out = suggest_ops_action("stuck order", flags={})
    assert out["status"] == "phase2_disabled"
    assert out["suggestions"] == []


def test_suggest_ops_action_stub_without_nim(db, monkeypatch) -> None:
    monkeypatch.setattr(
        "porterchain_api.intelligence_engine.nim_client.nim_configured",
        lambda: False,
    )
    monkeypatch.setattr(
        "porterchain_api.intelligence_engine.nim_client.nim_status",
        lambda: {
            "configured": False,
            "provider": "nvidia_nim",
            "model": "openai/gpt-oss-20b",
            "api_base": "https://integrate.api.nvidia.com/v1",
            "circuit_open": False,
            "fail_streak": 0,
        },
    )
    out = suggest_ops_action(
        "SLA risk on downtown pickup",
        flags={"intelligence": True},
        db=db,
    )
    assert out["status"] == "stub"
    assert out["suggestions"]
    assert out["suggestions"][0]["auto_apply"] is False
    assert out["suggestions"][0]["priority"] in {"p0", "p1", "p2"}


def test_nim_configured_respects_settings(monkeypatch) -> None:
    monkeypatch.setattr(
        "porterchain_api.intelligence_engine.nim_client.get_platform_settings",
        lambda: type("S", (), {"nvidia_api_key": ""})(),
    )
    assert nim_configured() is False

    monkeypatch.setattr(
        "porterchain_api.intelligence_engine.nim_client.get_platform_settings",
        lambda: type(
            "S",
            (),
            {
                "nvidia_api_key": "nvapi-test",
                "nvidia_model": "openai/gpt-oss-20b",
                "nvidia_api_base": "https://integrate.api.nvidia.com/v1",
            },
        )(),
    )
    assert nim_configured() is True
    status = nim_status()
    assert status["configured"] is True
    assert status["provider"] == "nvidia_nim"


def test_parse_suggestions_allowlist_and_sort() -> None:
    raw = """{
      "suggestions": [
        {"action": "reassign", "rationale": "Nearby spare", "priority": "p2", "confidence": 0.4},
        {"action": "review_fleetbase_console", "rationale": "Confirm GPS", "priority": "p0", "confidence": 0.9},
        {"action": "hack_stripe", "rationale": "nope", "priority": "p0", "confidence": 0.99}
      ]
    }"""
    rows = _parse_suggestions(raw)
    assert rows[0]["action"] == "review_fleetbase_console"
    assert rows[0]["priority"] == "p0"
    assert any(r["action"] == "reassign_candidate" for r in rows)
    assert all(r["action"] != "hack_stripe" for r in rows)
    assert all(r["auto_apply"] is False for r in rows)
    assert _normalize_action("call_merchant") == "contact_merchant"


def test_sandbox_blocks_push_delivery(db) -> None:
    log = DeliveryService().deliver(
        {
            "channel": "push",
            "template": "delivery_update",
            "recipient_type": "driver",
            "recipient_id": "drv-1",
            "recipient": "fake-token",
            "context": {"is_sandbox": True, "title": "Hi", "body": "Test"},
        }
    )
    assert log.status == "deferred"
    assert log.error == "sandbox_push_sms_blocked"


def test_sandbox_email_gets_test_prefix(monkeypatch) -> None:
    captured: dict = {}

    def _smtp(**kwargs):
        captured.update(kwargs)

    svc = DeliveryService()
    monkeypatch.setattr(svc, "_send_email_smtp", _smtp)
    monkeypatch.setattr(
        "porterchain_api.notification_engine.delivery_service.get_platform_settings",
        lambda: type(
            "S",
            (),
            {
                "smtp_host": "localhost",
                "smtp_password": "",
                "smtp_from_for": lambda self, alias=None: "ops@test",
                "smtp_from_name": "PorterChain",
                "resolve_mail_transport": lambda self: "smtp",
            },
        )(),
    )
    monkeypatch.setattr(
        "porterchain_api.notification_engine.delivery_service.render_email",
        lambda template, context: ("Update", "Body text", "<p>Body</p>"),
    )
    svc._send_email("a@b.com", "delivery_update", {"is_sandbox": True})
    assert captured["subject"].startswith("[TEST]")
    assert "TEST" in captured["from_name"].upper()
