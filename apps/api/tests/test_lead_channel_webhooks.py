"""Lead channel adapters + Meta signature verify."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

from porterchain_api.collaboration_engine.lead_channel_adapters import (
    event_from_google_lead,
    events_from_meta_payload,
    verify_meta_signature,
)
from porterchain_api.domain.crm_states import LeadSourceChannel


def test_verify_meta_signature() -> None:
    body = b'{"object":"page"}'
    secret = "test-secret"
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_meta_signature(app_secret=secret, raw_body=body, signature_header=sig)
    assert not verify_meta_signature(app_secret=secret, raw_body=body, signature_header="sha256=dead")


def test_meta_leadgen_to_event() -> None:
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "page1",
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": "LG123",
                            "form_id": "F1",
                            "page_id": "page1",
                            "field_data": [
                                {"name": "email", "values": ["ops@acme.test"]},
                                {"name": "full_name", "values": ["Ops Lead"]},
                                {"name": "company_name", "values": ["Acme"]},
                                {"name": "phone_number", "values": ["4165550100"]},
                            ],
                        },
                    }
                ],
            }
        ],
    }
    events = events_from_meta_payload(payload)
    assert len(events) == 1
    ev = events[0]
    assert ev.email == "ops@acme.test"
    assert ev.external_ids.get("meta_lead_id") == "LG123"
    assert ev.channel == LeadSourceChannel.FACEBOOK.value


def test_google_gbp_event() -> None:
    ev = event_from_google_lead(
        {
            "channel": "gbp",
            "email": "hello@shop.test",
            "name": "Shop Owner",
            "company_name": "Shop Co",
            "message": "Need same-day capacity",
            "conversation_id": "gbp-1",
            "lead_id": "g-1",
        }
    )
    assert ev.channel == LeadSourceChannel.GOOGLE_BUSINESS_PROFILE.value
    assert ev.external_ids.get("gbp_conversation_id") == "gbp-1"


def test_meta_webhook_verify_and_ingest(monkeypatch, db):
    from porterchain_api.config import get_settings
    from fastapi.testclient import TestClient
    from porterchain_api.main import create_app

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("META_APP_SECRET", "meta-secret")
    monkeypatch.setenv("META_WEBHOOK_VERIFY_TOKEN", "verify-me")
    get_settings.cache_clear()

    app = create_app()
    c = TestClient(app)
    vr = c.get(
        "/v1/public/leads/webhooks/meta",
        params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "42"},
    )
    assert vr.status_code == 200

    leadgen = f"LG-{uuid.uuid4().hex[:10]}"
    email = f"meta-{uuid.uuid4().hex[:8]}@test.example"
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "p",
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": leadgen,
                            "field_data": [
                                {"name": "email", "values": [email]},
                                {"name": "full_name", "values": ["Meta User"]},
                                {"name": "company_name", "values": ["Meta Co"]},
                            ],
                        },
                    }
                ],
            }
        ],
    }
    raw = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(b"meta-secret", raw, hashlib.sha256).hexdigest()
    res = c.post(
        "/v1/public/leads/webhooks/meta",
        content=raw,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["created"] + body["merged"] >= 1
    get_settings.cache_clear()
