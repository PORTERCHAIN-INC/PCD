"""Webhook service — verification, parsing, and normalization."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from porterchain_fleetbase_adapter.events import EventTranslator

logger = logging.getLogger(__name__)


def verify_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    """Verify Fleetbase webhook HMAC-SHA256 signature."""
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    provided = signature.removeprefix("sha256=").strip()
    return hmac.compare_digest(expected, provided)


def parse_webhook_body(body: dict[str, Any]) -> dict[str, Any]:
    """Normalize Fleetbase webhook envelope."""
    event_name = body.get("event") or ""
    data = body.get("data")
    if isinstance(data, dict) and "event" in data and not event_name:
        event_name = data.get("event", "")
    resource = data if isinstance(data, dict) else {}
    if isinstance(resource.get("data"), dict):
        resource = resource["data"]
    return {
        "event_id": body.get("id") or resource.get("id"),
        "event": event_name,
        "api_version": body.get("api_version"),
        "created_at": body.get("created_at"),
        "resource": resource,
        "raw": body,
    }


class WebhookService:
    """Validate Fleetbase webhooks and translate to Porterchain domain updates."""

    def __init__(self, *, webhook_secret: str = "", api_key: str = "", translator: EventTranslator | None = None) -> None:
        self.webhook_secret = webhook_secret
        self.api_key = api_key
        self.translator = translator or EventTranslator()

    def verify(self, payload: bytes, signature: str | None) -> bool:
        secret = self.webhook_secret or self.api_key
        if not secret:
            return True
        if not signature:
            return False
        return verify_signature(payload, signature, secret)

    def process(self, payload: bytes, body: dict[str, Any], *, signature: str | None = None) -> dict[str, Any] | None:
        if not self.verify(payload, signature):
            logger.warning("Fleetbase webhook signature verification failed")
            return None

        parsed = parse_webhook_body(body)
        event_name = parsed["event"]
        resource = parsed["resource"] if isinstance(parsed["resource"], dict) else {}

        target_state = self.translator.resolve_order_state(event_name)
        domain_event = self.translator.resolve_domain_event(event_name)

        if not target_state and not domain_event:
            logger.debug("Ignoring unmapped Fleetbase event: %s", event_name)
            return None

        return {
            "event_id": parsed.get("event_id"),
            "event": event_name,
            "domain_event": domain_event,
            "target_state": target_state,
            "porterchain_order_id": self.translator.extract_porterchain_order_id(resource),
            "fleetbase_order_id": self.translator.extract_fleetbase_order_id(resource),
            "resource": resource,
            "created_at": parsed.get("created_at"),
        }
