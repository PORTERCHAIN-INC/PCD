"""Mocked NVIDIA NIM HTTP path — no live network."""

from __future__ import annotations

import json

import httpx
import pytest

from porterchain_api.intelligence_engine import nim_client
from porterchain_api.intelligence_engine.copilot_service import suggest_ops_action

json_dumps = json.dumps


class _FakeResp:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> dict:
        return self._payload


def test_chat_completion_success_with_retry(monkeypatch) -> None:
    nim_client._fail_streak = 0
    nim_client._circuit_open_until = 0.0

    monkeypatch.setattr(
        nim_client,
        "get_platform_settings",
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

    calls = {"n": 0}

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            del json  # request body unused in mock
            calls["n"] += 1
            if calls["n"] == 1:
                return _FakeResp(503, {"error": "busy"})
            body = {
                "suggestions": [
                    {
                        "action": "review_day_plan",
                        "rationale": "Confirm driver near pickup",
                        "priority": "p0",
                        "confidence": 0.91,
                        "auto_apply": False,
                    }
                ]
            }
            return _FakeResp(
                200,
                {
                    "id": "chatcmpl-test",
                    "model": "openai/gpt-oss-20b",
                    "choices": [{"message": {"content": json_dumps(body)}}],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 34},
                },
            )

    monkeypatch.setattr(httpx, "Client", _Client)
    out = nim_client.chat_completion(
        messages=[{"role": "user", "content": "stuck order downtown"}],
        max_retries=2,
    )
    assert calls["n"] == 2
    assert out["prompt_tokens"] == 12
    assert out["completion_tokens"] == 34
    assert "review_day_plan" in out["content"]


def test_suggest_via_nim_records_ok(db, monkeypatch) -> None:
    nim_client._fail_streak = 0
    nim_client._circuit_open_until = 0.0

    monkeypatch.setattr(nim_client, "nim_configured", lambda: True)
    monkeypatch.setattr(
        nim_client,
        "nim_status",
        lambda: {
            "configured": True,
            "provider": "nvidia_nim",
            "model": "openai/gpt-oss-20b",
            "api_base": "https://integrate.api.nvidia.com/v1",
            "circuit_open": False,
            "fail_streak": 0,
        },
    )
    monkeypatch.setattr(
        nim_client,
        "chat_completion",
        lambda **kwargs: {
            "content": json.dumps(
                {
                    "suggestions": [
                        {
                            "action": "check_sla_queue",
                            "rationale": "Two at-risk orders",
                            "priority": "p1",
                            "confidence": 0.8,
                        }
                    ]
                }
            ),
            "model": "openai/gpt-oss-20b",
            "prompt_tokens": 5,
            "completion_tokens": 9,
            "latency_ms": 42,
            "raw_id": "x",
        },
    )

    out = suggest_ops_action(
        "SLA risk",
        flags={"intelligence": True},
        db=db,
        actor_type="admin",
        actor_id="test-admin",
    )
    assert out["status"] == "ok"
    assert out["provider"] == "nvidia_nim"
    assert out["suggestions"][0]["action"] == "check_sla_queue"
    assert out["suggestions"][0]["auto_apply"] is False


def test_circuit_open_blocks(monkeypatch) -> None:
    import time

    monkeypatch.setattr(
        nim_client,
        "get_platform_settings",
        lambda: type("S", (), {"nvidia_api_key": "nvapi-test"})(),
    )
    nim_client._fail_streak = 3
    nim_client._circuit_open_until = time.monotonic() + 30
    with pytest.raises(RuntimeError, match="circuit_open"):
        nim_client.chat_completion(messages=[{"role": "user", "content": "x"}])
    nim_client._fail_streak = 0
    nim_client._circuit_open_until = 0.0
