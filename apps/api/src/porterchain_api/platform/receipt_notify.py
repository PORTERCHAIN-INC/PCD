"""Receipt notify — merchant/billing may publish without importing booking/notification engines."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

RECEIPT_GENERATED = "receipt.generated"


def emit_receipt_generated(
    db: Session,
    *,
    invoice_id: str,
    correlation_id: str,
    payload: dict[str, Any],
) -> None:
    """Persist booking-domain receipt event + best-effort notification fan-out."""
    from porterchain_api.booking_engine._core import emit_event

    emit_event(
        db,
        event_type=RECEIPT_GENERATED,
        aggregate_type="invoice",
        aggregate_id=invoice_id,
        correlation_id=correlation_id,
        actor_type="system",
        actor_id=None,
        payload=payload,
        publish=True,
    )
    try:
        from porterchain_api.notification_engine.event_router import handle_domain_event

        handle_domain_event(
            {
                "event_type": RECEIPT_GENERATED,
                "aggregate_type": "invoice",
                "aggregate_id": invoice_id,
                "correlation_id": correlation_id,
                "payload": payload,
            }
        )
    except Exception:
        pass
