"""WebhookIngressService — Fleetbase webhook ingress (router delegates here only)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.config import Settings
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration
from porterchain_shared.events.catalog import DomainEventType


class WebhookIngressService:
    def accept(
        self,
        db: Session,
        settings: Settings,
        *,
        raw_body: bytes,
        signature: str | None,
    ) -> dict[str, str]:
        if not settings.fleetbase_dispatch_bridge:
            return {"status": "ignored", "reason": "bridge_disabled"}

        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid_json") from exc

        if not isinstance(body, dict):
            raise ValueError("invalid_payload")

        integration = get_fleetbase_integration(settings)
        # HS-12 / API-P-04: when a webhook secret is configured, reject bad/missing
        # signatures (do not soft-ignore — that hides auth failures as "ignored").
        if settings.fleetbase_webhook_secret:
            if not integration.webhooks.verify(raw_body, signature):
                raise ValueError("invalid_signature")

        update = integration.process_webhook(raw_body, body, signature=signature)
        if not update:
            return {"status": "ignored"}

        order_id = update.get("porterchain_order_id") or update.get("fleetbase_order_id") or "unknown"
        emit_event(
            db,
            event_type=DomainEventType.WEBHOOK_RECEIVED,
            aggregate_type="webhook",
            aggregate_id=str(order_id),
            payload={"source": "fleetbase", "update": update, "raw": body},
        )
        db.commit()
        return {
            "status": "accepted",
            "order_id": update.get("porterchain_order_id")
            or update.get("fleetbase_order_id")
            or "",
        }