"""Fleetbase adapter contract tests — sync, webhook, POD mapping."""

from __future__ import annotations

import hashlib
import hmac
import json

from porterchain_fleetbase_adapter.events import EventTranslator
from porterchain_fleetbase_adapter.events.lifecycle import (
    FLEETBASE_EVENT_TO_STATE,
    FLEETBASE_STATUS_TO_STATE,
)
from porterchain_fleetbase_adapter.webhooks import WebhookService, parse_webhook_body, verify_signature


def test_fleetbase_event_maps_to_porterchain_state():
    assert FLEETBASE_EVENT_TO_STATE["order.delivered"] == "DELIVERED"
    assert FLEETBASE_EVENT_TO_STATE["order.driver_assigned"] == "DRIVER_ASSIGNED"
    assert FLEETBASE_STATUS_TO_STATE["in_transit"] == "IN_TRANSIT"


def test_event_translator_resolves_order_state():
    translator = EventTranslator()
    assert translator.resolve_order_state("order.delivered") == "DELIVERED"
    assert translator.resolve_domain_event("order.delivered") == "order.delivered"


def test_parse_webhook_body_normalizes_envelope():
    body = {
        "event": "order.delivered",
        "data": {"id": "fb-123", "status": "completed", "tracking_number": "PC-001"},
    }
    parsed = parse_webhook_body(body)
    assert parsed["event"] == "order.delivered"
    assert parsed["resource"]["id"] == "fb-123"


def test_webhook_signature_roundtrip():
    secret = "test-webhook-secret"
    payload = b'{"event":"order.delivered","data":{"id":"1"}}'
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_signature(payload, sig, secret)
    assert verify_signature(payload, f"sha256={sig}", secret)
    assert not verify_signature(payload, "bad", secret)


def test_webhook_service_rejects_bad_signature():
    svc = WebhookService(webhook_secret="secret")
    body = {"event": "order.delivered", "data": {"id": "1"}}
    payload = json.dumps(body).encode()
    assert svc.process(payload, body, signature="invalid") is None


def test_webhook_service_accepts_valid_payload():
    svc = WebhookService(webhook_secret="secret")
    body = {"event": "order.delivered", "data": {"id": "1", "status": "completed"}}
    payload = json.dumps(body).encode()
    sig = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
    result = svc.process(payload, body, signature=sig)
    assert result is not None
    assert result.get("target_state") == "DELIVERED"
