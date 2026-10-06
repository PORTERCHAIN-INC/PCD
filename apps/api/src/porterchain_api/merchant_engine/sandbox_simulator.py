"""Sandbox lifecycle simulator — advance test orders without live dispatch.

Partners certify webhook handlers against signed order.* fixtures. Never rebuilds
dispatch/GPS; only transitions PorterChain Order state and fans out to sandbox webhooks.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.domain.sandbox import order_is_sandbox
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.secrets import decrypt_signing_secret
from porterchain_api.merchant_engine.webhook_delivery_service import (
    deliver_webhook_payload,
    log_delivery,
)
from porterchain_api.merchant_models import MerchantWebhook

# Happy path for partner certification (no Fleetbase, no Google ETA).
SANDBOX_HAPPY_PATH: tuple[tuple[OrderState, str], ...] = (
    (OrderState.DISPATCH_READY, "order.dispatch_ready"),
    (OrderState.DRIVER_ASSIGNED, "order.driver_assigned"),
    (OrderState.DRIVER_ACCEPTED, "order.driver_accepted"),
    (OrderState.DRIVER_EN_ROUTE, "order.en_route"),
    (OrderState.AT_PICKUP, "order.arrived_pickup"),
    (OrderState.PICKED_UP, "order.pickup_completed"),
    (OrderState.IN_TRANSIT, "order.in_transit"),
    (OrderState.AT_DESTINATION, "order.near_delivery"),
    (OrderState.DELIVERED, "order.delivered"),
    (OrderState.POD_COMPLETED, "order.pod_completed"),
)


def _sign_headers(body: dict[str, Any], signing_secret: str) -> dict[str, str]:
    body_bytes = json.dumps(body, separators=(",", ":"), default=str).encode()
    timestamp = int(time.time())
    signed = f"{timestamp}.".encode() + body_bytes
    signature = hmac.new(signing_secret.encode(), signed, hashlib.sha256).hexdigest()
    return {
        "X-Porterchain-Signature": signature,
        "X-Porterchain-Timestamp": str(timestamp),
        "Content-Type": "application/json",
    }


def _event_body(order: Order, event_type: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "order_id": order.id,
        "order_number": order.order_number,
        "tracking_number": order.tracking_number,
        "state": order.state,
        "merchant_id": order.merchant_id,
        "is_sandbox": True,
        "occurred_at": datetime.now(UTC).isoformat(),
        "payload": {"simulator": True, **(payload or {})},
    }


def _path_index(state: OrderState) -> int:
    if state == OrderState.BOOKED:
        return -1
    for i, (s, _) in enumerate(SANDBOX_HAPPY_PATH):
        if s == state:
            return i
    return -2


def simulate_sandbox_lifecycle(
    db: Session,
    settings: Settings,
    ctx: MerchantContext,
    order_id: str,
    *,
    deliver_webhooks: bool = True,
    until_state: str | None = None,
) -> dict[str, Any]:
    """Advance a sandbox order along the happy path and optionally POST signed webhooks."""
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.merchant_id == ctx.merchant.id)
        .first()
    )
    if not order:
        raise LookupError("order_not_found")
    if not order_is_sandbox(order):
        raise ValueError("simulator_requires_sandbox_order")
    if order.fleetbase_order_id:
        raise ValueError("simulator_refuses_fleetbase_linked_orders")

    stop_at = OrderState(until_state) if until_state else OrderState.POD_COMPLETED
    current_idx = _path_index(OrderState(order.state))
    if current_idx == -2:
        raise ValueError(f"simulator_unsupported_state:{order.state}")

    steps: list[dict[str, Any]] = []
    fixtures: list[dict[str, Any]] = []

    hooks = (
        db.query(MerchantWebhook)
        .filter(
            MerchantWebhook.merchant_id == ctx.merchant.id,
            MerchantWebhook.is_active.is_(True),
        )
        .all()
        if deliver_webhooks
        else []
    )
    sandbox_hooks = [
        h for h in hooks if (getattr(h, "environment", None) or "production").lower() == "sandbox"
    ]

    start_i = current_idx + 1
    for to_state, event_type in SANDBOX_HAPPY_PATH[start_i:]:
        transition_order_state(
            db,
            order,
            to_state,
            event_type=event_type,
            actor_type="merchant",
            actor_id=ctx.user.id,
            payload={"simulator": True, "is_sandbox": True},
        )
        db.commit()
        db.refresh(order)
        body = _event_body(order, event_type)
        steps.append({"state": order.state, "event_type": event_type})

        fixture_row: dict[str, Any] = {"event_type": event_type, "body": body, "deliveries": []}
        for hook in sandbox_hooks:
            if not hook.encrypted_signing_secret:
                continue
            try:
                secret = decrypt_signing_secret(
                    hook.encrypted_signing_secret, encryption_key=settings.jwt_secret
                )
            except ValueError:
                continue
            headers = _sign_headers(body, secret)
            fixture_row["headers_sample"] = {
                "X-Porterchain-Signature": headers["X-Porterchain-Signature"][:16] + "…",
                "X-Porterchain-Timestamp": headers["X-Porterchain-Timestamp"],
            }
            if deliver_webhooks:
                start = time.perf_counter()
                status, response_text, error = deliver_webhook_payload(hook.url, body, secret)
                duration_ms = int((time.perf_counter() - start) * 1000)
                success = status is not None and status < 400
                log_delivery(
                    db,
                    merchant_id=ctx.merchant.id,
                    webhook_id=hook.id,
                    event_type=event_type,
                    request_body=body,
                    response_status=status,
                    response_body=response_text,
                    attempt=1,
                    success=success,
                    error_message=error,
                    duration_ms=duration_ms,
                )
                fixture_row["deliveries"].append(
                    {
                        "webhook_id": hook.id,
                        "status": status,
                        "success": success,
                        "error": error,
                    }
                )
            else:
                fixture_row["signed_headers"] = headers
        fixtures.append(fixture_row)
        if OrderState(order.state) == stop_at:
            break

    db.commit()
    return {
        "order_id": order.id,
        "tracking_number": order.tracking_number,
        "final_state": order.state,
        "steps": steps,
        "fixtures": fixtures,
        "webhooks_targeted": len(sandbox_hooks),
    }


def sandbox_fixture_preview(order: Order, event_type: str = "order.delivered") -> dict[str, Any]:
    """Body shape for docs / OpenAPI examples."""
    return _event_body(order, event_type, payload={"example": True})
