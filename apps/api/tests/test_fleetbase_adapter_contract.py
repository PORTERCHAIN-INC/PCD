"""Fleetbase adapter contract tests (§2.1.4)."""

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


def test_webhook_service_accepts_valid_payload():
    svc = WebhookService(webhook_secret="secret")
    body = {"event": "order.delivered", "data": {"id": "1", "status": "completed"}}
    payload = json.dumps(body).encode()
    sig = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
    result = svc.process(payload, body, signature=sig)
    assert result is not None
    assert result.get("target_state") == "DELIVERED"
