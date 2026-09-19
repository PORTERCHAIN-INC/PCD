"""HS-12 / API-P-04 — Fleetbase webhook signature reject + status translate."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.webhook_ingress_service import WebhookIngressService


def _settings(**overrides) -> Settings:
    base = dict(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt",
        fleetbase_dispatch_bridge=True,
        fleetbase_webhook_secret="test-fleetbase-webhook-secret",
        fleetbase_api_key="flb_test",
    )
    base.update(overrides)
    return Settings(**base)


def _sign(raw: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def test_accept_rejects_bad_signature(db: Session) -> None:
    raw = json.dumps({"event": "order.completed", "data": {"id": "order_x"}}).encode()
    svc = WebhookIngressService()
    with pytest.raises(ValueError, match="invalid_signature"):
        svc.accept(db, _settings(), raw_body=raw, signature="sha256=deadbeef")


def test_accept_rejects_missing_signature_when_secret_set(db: Session) -> None:
    raw = json.dumps({"event": "order.completed", "data": {"id": "order_x"}}).encode()
    svc = WebhookIngressService()
    with pytest.raises(ValueError, match="invalid_signature"):
        svc.accept(db, _settings(), raw_body=raw, signature=None)


def test_accept_valid_signature_emits_webhook_received(db: Session) -> None:
    settings = _settings()
    secret = settings.fleetbase_webhook_secret
    body = {
        "event": "order.dispatched",
        "data": {
            "id": "order_abc",
            "status": "dispatched",
            "meta": {"porterchain_order_id": "pc-order-1"},
        },
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    sig = _sign(raw, secret)

    with patch(
        "porterchain_api.fleetbase_engine.webhook_ingress_service.emit_event"
    ) as emit, patch(
        "porterchain_api.fleetbase_engine.webhook_ingress_service.get_fleetbase_integration"
    ) as get_int:
        integration = MagicMock()
        integration.webhooks.verify.return_value = True
        integration.process_webhook.return_value = {
            "event": "order.dispatched",
            "porterchain_order_id": "pc-order-1",
            "fleetbase_order_id": "order_abc",
            "target_state": "DISPATCH_READY",
        }
        get_int.return_value = integration
        out = WebhookIngressService().accept(db, settings, raw_body=raw, signature=sig)

    assert out["status"] == "accepted"
    assert out["order_id"] == "pc-order-1"
    emit.assert_called_once()
    db.rollback()
