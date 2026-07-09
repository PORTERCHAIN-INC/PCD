"""Medical / cold-chain compliance actions (§8.1.3)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.compliance_metadata import (
    append_temperature_reading,
    is_temperature_excursion,
)
from porterchain_api.config import Settings
from porterchain_api.models import Order
from porterchain_shared.events.catalog import DomainEventType


class MedicalComplianceService:
    def record_temperature(
        self,
        db: Session,
        settings: Settings,
        order_id: str,
        *,
        celsius: float,
        actor_type: str = "admin",
        actor_id: str | None = None,
    ) -> dict:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")

        recorded_at = datetime.now(UTC)
        prior = dict(order.compliance_metadata or {})
        order.compliance_metadata = append_temperature_reading(
            prior,
            celsius=celsius,
            recorded_at=recorded_at,
        )
        excursion = is_temperature_excursion(order.compliance_metadata, celsius)

        emit_event(
            db,
            event_type="order.temperature_recorded",
            aggregate_type="order",
            aggregate_id=order.id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"celsius": celsius, "excursion": excursion},
        )

        if excursion:
            cold = (order.compliance_metadata or {}).get("cold_chain") or {}
            emit_event(
                db,
                event_type=DomainEventType.ORDER_TEMP_EXCURSION,
                aggregate_type="order",
                aggregate_id=order.id,
                actor_type=actor_type,
                actor_id=actor_id,
                payload={
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "tracking_number": order.tracking_number,
                    "merchant_id": order.merchant_id,
                    "celsius": celsius,
                    "min_c": cold.get("min_c"),
                    "max_c": cold.get("max_c"),
                },
            )

        db.commit()
        db.refresh(order)
        return {
            "order_id": order.id,
            "tracking_number": order.tracking_number,
            "celsius": celsius,
            "excursion": excursion,
            "compliance_metadata": order.compliance_metadata,
        }
