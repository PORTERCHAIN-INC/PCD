"""Fleetbase webhook ingress was removed. The retired stub is a no-op."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.platform.retired_sync import WebhookIngressService


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


def test_accept_is_a_noop(db: Session) -> None:
    svc = WebhookIngressService()
    raw = b'{"event": "order.completed", "data": {"id": "order_x"}}'
    assert svc.accept(db, _settings(), raw_body=raw, signature="sha256=deadbeef") is None
    assert svc.accept(db, _settings(fleetbase_webhook_secret=""), raw_body=raw, signature=None) is None
    assert svc.accept(db, _settings(), raw_body=raw, signature="sha256=" + "ab" * 32) is None
