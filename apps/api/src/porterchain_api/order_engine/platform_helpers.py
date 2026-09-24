"""Shared helpers for order platform enrichment and risk scoring."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver, Vehicle
from porterchain_api.merchant_models import Merchant
from porterchain_api.booking_models import Booking, Customer, Invoice, Order, OrderEvent, Payment, Quote
from porterchain_api.domain.catalog_labels import order_source_label, order_state_label


def shopify_snapshot(order: Order) -> dict[str, Any] | None:
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    raw = meta.get("shopify") if isinstance(meta.get("shopify"), dict) else None
    source = str(getattr(order, "order_source", "") or "").upper()
    if raw:
        return {
            "shop_domain": raw.get("shop_domain"),
            "order_id": str(raw.get("order_id") or "") or None,
            "order_name": raw.get("order_name") or raw.get("name"),
            "fulfillment_id": str(raw.get("fulfillment_id") or "") or None,
            "last_tracking_push_at": raw.get("last_tracking_push_at"),
            "last_tracking_state": raw.get("last_tracking_state"),
            "last_fulfillment_error": raw.get("last_fulfillment_error"),
            "held_for_ops": bool(raw.get("held_for_ops")),
            "auto_dispatch": raw.get("auto_dispatch"),
            "last_repush_at": raw.get("last_repush_at"),
        }
    if source == "SHOPIFY":
        return {
            "shop_domain": None,
            "order_id": order.purchase_order_number,
            "order_name": order.internal_reference,
            "fulfillment_id": None,
            "last_tracking_push_at": None,
            "last_tracking_state": None,
            "last_fulfillment_error": None,
            "held_for_ops": order.state == "BOOKED",
            "auto_dispatch": None,
            "last_repush_at": None,
        }
    return None


def ops_timeline_label(*, event_type: str, to_state: str | None = None, payload: Any = None) -> str:
    data = payload if isinstance(payload, dict) else {}
    invoiced = "invoic" in (event_type or "").lower() or str(to_state or "").upper() == "INVOICED"
    if invoiced:
        number = data.get("invoice_number")
        amount = data.get("amount_display")
        parts = ["Invoice"]
        if number:
            parts.append(str(number))
        if amount:
            parts.append(str(amount))
        return " · ".join(parts) if len(parts) > 1 else "Invoice finalized"
    if event_type:
        return event_type.replace(".", " ").replace("_", " ").title()
    return "Event"
from porterchain_api.order_engine.buckets import (
    DONE_STATES,
    FAILED_STATES,
    HIGH_PRIORITY_CENTS,
    IN_FLIGHT,
    WAITING_DISPATCH,
)


class OrderPlatformHelpersMixin:
    def _now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def _merchant_map(self, db: Session) -> dict[str, str]:
        return {m.id: m.company_name for m in db.query(Merchant).all()}

    def _driver_map(self, db: Session) -> dict[str, Driver]:
        return {d.id: d for d in db.query(Driver).all()}

    def _vehicle_for_driver(self, db: Session, driver_id: str | None) -> Vehicle | None:
        if not driver_id:
            return None
        return (
            db.query(Vehicle)
            .filter(Vehicle.driver_id == driver_id, Vehicle.is_active == True)  # noqa: E712
            .first()
        )

    def _payment_status(self, db: Session, order: Order) -> str | None:
        payment = (
            db.query(Payment)
            .filter(Payment.order_id == order.id)
            .order_by(Payment.created_at.desc())
            .first()
        )
        if not payment and order.quote_id:
            payment = (
                db.query(Payment)
                .filter(Payment.quote_id == order.quote_id)
                .order_by(Payment.created_at.desc())
                .first()
            )
        return payment.status if payment else None

    def _invoice_status(self, db: Session, order: Order) -> str:
        invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
        if invoice:
            return "generated"
        if order.state in ("INVOICED", "CLOSED"):
            return "generated"
        return "none"

    def _priority(self, order: Order) -> str:
        return "high" if order.amount_cents >= HIGH_PRIORITY_CENTS else "normal"

    def _addr_label(self, addr: dict | None) -> str:
        if not addr:
            return "—"
        return str(addr.get("formatted") or addr.get("city") or addr.get("address") or "—")

    def _avg_duration_hours(self, db: Session, from_type: str, to_type: str) -> float:
        """Heuristic avg hours between first matching order events."""
        events = (
            db.query(OrderEvent)
            .filter(OrderEvent.event_type.in_((from_type, to_type)))
            .order_by(OrderEvent.occurred_at.asc())
            .all()
        )
        by_order: dict[str, dict[str, datetime]] = {}
        for ev in events:
            bucket = by_order.setdefault(ev.order_id, {})
            if ev.event_type not in bucket:
                bucket[ev.event_type] = ev.occurred_at.replace(tzinfo=None) if ev.occurred_at.tzinfo else ev.occurred_at
        deltas: list[float] = []
        for times in by_order.values():
            if from_type in times and to_type in times:
                delta = (times[to_type] - times[from_type]).total_seconds() / 3600
                if delta >= 0:
                    deltas.append(delta)
        return round(sum(deltas) / len(deltas), 1) if deltas else 0.0

    def _row(self, db: Session, order: Order, merchants: dict[str, str], drivers: dict[str, Driver]) -> dict[str, Any]:
        booking = db.query(Booking).filter(Booking.order_id == order.id).first()
        quote = db.query(Quote).filter(Quote.id == order.quote_id).first() if order.quote_id else None
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )
        driver = drivers.get(order.assigned_driver_id) if order.assigned_driver_id else None
        vehicle = self._vehicle_for_driver(db, order.assigned_driver_id)
        now = self._now()
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "booking_number": booking.booking_number if booking else None,
            "merchant_id": order.merchant_id,
            "merchant_name": merchants.get(order.merchant_id) if order.merchant_id else None,
            "customer_id": order.customer_id,
            "customer_email": customer.email if customer else None,
            "driver_id": order.assigned_driver_id,
            "driver_name": driver.full_name if driver else None,
            "vehicle_label": f"{vehicle.make_model or vehicle.vehicle_class} ({vehicle.plate_number})" if vehicle else None,
            "pickup": self._addr_label(order.pickup),
            "destination": self._addr_label(order.dropoff),
            "service_type": quote.vehicle_class if quote else None,
            "priority": self._priority(order),
            "state": order.state,
            "display_state": order_state_label(order.state),
            "payment_status": self._payment_status(db, order),
            "invoice_status": self._invoice_status(db, order),
            "amount_cents": order.amount_cents,
            "currency": order.currency,
            "eta": order.scheduled_at,
            "sla_status": self._tower._sla_status(order, now),
            "fraud_risk_score": self._fraud_risk(order, quote),
            "delay_risk_score": self._delay_risk(order, now),
            "scheduled_at": order.scheduled_at,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "purchase_order_number": order.purchase_order_number,
            "cost_centre": order.cost_centre,
            "internal_reference": order.internal_reference,
            "order_source": getattr(order, "order_source", None),
            "order_source_label": order_source_label(getattr(order, "order_source", None)),
            "shopify": shopify_snapshot(order),
            "is_sandbox": bool(getattr(order, "is_sandbox", False)),
        }

    def _fraud_risk(self, order: Order, quote: Quote | None) -> int:
        score = 10
        if order.amount_cents >= 50000:
            score += 25
        if quote and quote.declared_value_cents and quote.declared_value_cents >= 100000:
            score += 20
        if order.state in FAILED_STATES:
            score += 15
        return min(100, score)

    def _delay_risk(self, order: Order, now: datetime) -> int:
        if order.state in DONE_STATES or order.state in ("CANCELLED", "REFUNDED"):
            return 0
        sla = self._tower._sla_status(order, now)
        if sla == "breached":
            return 90
        if sla == "at_risk":
            return 55
        if order.state in IN_FLIGHT:
            return 25
        return 10

    def _smart_insights(self, order: Order, quote: Quote | None, events: list[OrderEvent]) -> dict[str, Any]:
        now = self._now()
        delay = self._delay_risk(order, now)
        fraud = self._fraud_risk(order, quote)
        summary = (
            f"Order {order.order_number} is {order.state.replace('_', ' ').lower()} "
            f"for {order.amount_cents / 100:.2f} {order.currency.upper()}."
        )
        if delay >= 55:
            summary += " SLA is at risk or breached — prioritize dispatch or customer contact."
        suggestion = "Monitor tracking" if order.state in IN_FLIGHT else "Review payment and dispatch readiness"
        if order.state in WAITING_DISPATCH:
            suggestion = "Assign nearest available driver"
        elif order.state in FAILED_STATES:
            suggestion = "Open incident review and notify merchant"
        return {
            "ai_summary": summary,
            "delay_prediction_hours": round(delay / 30, 1),
            "fraud_risk_score": fraud,
            "delay_risk_score": delay,
            "priority_suggestion": self._priority(order),
            "suggested_action": suggestion,
            "event_count": len(events),
        }
