"""Admin delivery-override events: admin_engine records them without importing booking_engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

DELIVERY_COMPLETED_OVERRIDE = "delivery.completed_override"


def emit_delivery_override(
    db: Session,
    *,
    order_id: str,
    admin_user_id: str,
    context: dict[str, Any],
) -> None:
    """Timeline/audit only (publish=False) — never fans out customer or merchant messages."""
    from porterchain_api.booking_engine._core import emit_event

    emit_event(
        db,
        event_type=DELIVERY_COMPLETED_OVERRIDE,
        aggregate_type="order",
        aggregate_id=order_id,
        actor_type="admin",
        actor_id=admin_user_id,
        payload=context,
        publish=False,
    )
