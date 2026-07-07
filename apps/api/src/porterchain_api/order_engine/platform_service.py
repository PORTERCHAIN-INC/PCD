"""Order platform service — Application Service (masterrule §3).

Porterchain owns the order lifecycle mirror. Fleetbase execution data is reached
only via TrackingService → FleetbaseIntegrationBridge, never from UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.order_engine.buckets import (
    ASSIGNED_STATES,
    DONE_STATES,
    FAILED_STATES,
    HIGH_PRIORITY_CENTS,
    IN_FLIGHT,
    PICKED_UP_STATES,
    RETURNED_STATES,
    WAITING_DISPATCH,
)
from porterchain_api.order_engine.filters import OrderFilters
from porterchain_api.admin_models import AdminAuditLog, Claim, Driver, SupportTicket, Vehicle
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.booking_engine.tracking_service import TrackingService
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState, QuoteState
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Booking, Customer, DomainEvent, Invoice, Order, OrderEvent, OrderException, Payment, Quote


class OrderPlatformService:
    def __init__(self) -> None:
        from porterchain_api.admin_engine.control_tower_service import ControlTowerService

        self._tower = ControlTowerService()
        self._tracking = TrackingService()

    # ------------------------------------------------------------------ #
    # Legacy (kept for backward compatibility)
    # ------------------------------------------------------------------ #
    def list_quotes(self, db: Session, *, state: str | None = None, limit: int = 50) -> list[Quote]:
        q = db.query(Quote)
        if state:
            q = q.filter(Quote.state == state)
        return q.order_by(Quote.created_at.desc()).limit(limit).all()

    def list_bookings(self, db: Session, *, limit: int = 50) -> list[Booking]:
        return db.query(Booking).order_by(Booking.created_at.desc()).limit(limit).all()

    def list_orders(
        self,
        db: Session,
        *,
        state: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[Order]:
        q = db.query(Order)
        if state:
            q = q.filter(Order.state == state)
        if search:
            pattern = f"%{search}%"
            q = q.filter(
                (Order.tracking_number.ilike(pattern)) | (Order.order_number.ilike(pattern))
            )
        return q.order_by(Order.created_at.desc()).limit(limit).all()

    def get_order(self, db: Session, order_id: str) -> Order | None:
        return db.query(Order).filter(Order.id == order_id).first()

    def order_full_detail(self, db: Session, order_id: str) -> dict | None:
        """Gather every value captured at booking + payment time for one order."""
        order = self.get_order(db, order_id)
        if not order:
            return None

        quote = (
            db.query(Quote).filter(Quote.id == order.quote_id).first()
            if order.quote_id
            else None
        )
        booking = db.query(Booking).filter(Booking.order_id == order.id).first()
        invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )

        payments = (
            db.query(Payment)
            .filter(Payment.order_id == order.id)
            .order_by(Payment.created_at.desc())
            .all()
        )
        if not payments and order.quote_id:
            payments = (
                db.query(Payment)
                .filter(Payment.quote_id == order.quote_id)
                .order_by(Payment.created_at.desc())
                .all()
            )

        return {
            "order": order,
            "quote": quote,
            "booking": booking,
            "invoice": invoice,
            "customer": customer,
            "payments": payments,
        }

    def order_timeline(self, db: Session, order_id: str) -> list[OrderEvent]:
        return (
            db.query(OrderEvent)
            .filter(OrderEvent.order_id == order_id)
            .order_by(OrderEvent.occurred_at.asc())
            .all()
        )

    def list_invoices(self, db: Session, *, limit: int = 50) -> list[Invoice]:
        return db.query(Invoice).order_by(Invoice.created_at.desc()).limit(limit).all()


    def pending_quotes_count(self, db: Session) -> int:
        return db.query(Quote).filter(Quote.state == QuoteState.QUOTE.value).count()

    # ------------------------------------------------------------------ #
    # Enriched admin platform
    # ------------------------------------------------------------------ #
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

    def dashboard(self, db: Session) -> dict[str, Any]:
        now = self._now()
        sod = datetime.combine(now.date(), time.min)
        stats = self._tower.stats(db)

        def count(states: tuple[str, ...]) -> int:
            return db.query(func.count(Order.id)).filter(Order.state.in_(states)).scalar() or 0

        delivered_today = (
            db.query(func.count(Order.id))
            .filter(Order.state.in_(DONE_STATES), Order.updated_at >= sod)
            .scalar()
            or 0
        )
        open_claims = db.query(func.count(Claim.id)).filter(Claim.status.notin_(("closed", "archived", "rejected"))).scalar() or 0

        sla_met = 0
        sla_total = 0
        for o in db.query(Order).filter(Order.state.in_(DONE_STATES), Order.updated_at >= sod).limit(200).all():
            sla_total += 1
            if self._tower._sla_status(o, now) == "met":
                sla_met += 1
        avg_sla = round((sla_met / sla_total * 100) if sla_total else 100.0, 1)

        return {
            "orders_today": stats["orders_today"],
            "orders_in_progress": stats["active_deliveries"],
            "waiting_dispatch": count(WAITING_DISPATCH),
            "assigned": count(ASSIGNED_STATES),
            "picked_up": count(PICKED_UP_STATES),
            "delivered": delivered_today,
            "failed": count(FAILED_STATES),
            "returned": count(RETURNED_STATES),
            "claims": int(open_claims),
            "revenue_today_cents": stats["revenue_today_cents"],
            "avg_delivery_hours": self._avg_duration_hours(db, "order.picked_up", "order.delivered"),
            "avg_pickup_hours": self._avg_duration_hours(db, "order.driver_assigned", "order.picked_up"),
            "avg_sla_percent": avg_sla,
        }

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
            "display_state": order.state,
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

    def list_enriched(self, db: Session, filters: OrderFilters) -> list[dict[str, Any]]:
        q = db.query(Order).order_by(Order.updated_at.desc())
        if filters.state:
            q = q.filter(Order.state == filters.state)
        if filters.merchant_id:
            q = q.filter(Order.merchant_id == filters.merchant_id)
        if filters.driver_id:
            q = q.filter(Order.assigned_driver_id == filters.driver_id)
        if filters.date_from:
            q = q.filter(Order.created_at >= filters.date_from)
        if filters.date_to:
            q = q.filter(Order.created_at <= filters.date_to)
        if filters.amount_min_cents is not None:
            q = q.filter(Order.amount_cents >= filters.amount_min_cents)
        if filters.amount_max_cents is not None:
            q = q.filter(Order.amount_cents <= filters.amount_max_cents)
        if filters.search:
            like = f"%{filters.search}%"
            customer_ids = [c.id for c in db.query(Customer).filter(Customer.email.ilike(like)).limit(100).all()]
            clauses = [
                Order.tracking_number.ilike(like),
                Order.order_number.ilike(like),
            ]
            if customer_ids:
                clauses.append(Order.customer_id.in_(customer_ids))
            q = q.filter(or_(*clauses))

        merchants = self._merchant_map(db)
        drivers = self._driver_map(db)
        rows: list[dict[str, Any]] = []
        for order in q.offset(filters.offset).limit(filters.limit).all():
            row = self._row(db, order, merchants, drivers)
            if filters.payment_status and row["payment_status"] != filters.payment_status:
                continue
            if filters.invoice_status and row["invoice_status"] != filters.invoice_status:
                continue
            if filters.priority and row["priority"] != filters.priority:
                continue
            if filters.service_type and row["service_type"] != filters.service_type:
                continue
            if filters.city:
                city_like = filters.city.lower()
                pickup = (order.pickup or {}).get("city", "")
                dropoff = (order.dropoff or {}).get("city", "")
                if city_like not in str(pickup).lower() and city_like not in str(dropoff).lower():
                    continue
            rows.append(row)
        return rows

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

    def find_duplicates(self, db: Session, order: Order) -> list[dict[str, Any]]:
        if not order.customer_id:
            return []
        window = order.created_at - timedelta(hours=24) if order.created_at else None
        q = db.query(Order).filter(
            Order.customer_id == order.customer_id,
            Order.id != order.id,
            Order.amount_cents == order.amount_cents,
        )
        if window:
            q = q.filter(Order.created_at >= window)
        return [
            {"order_id": o.id, "order_number": o.order_number, "tracking_number": o.tracking_number, "state": o.state}
            for o in q.limit(10).all()
        ]

    def get_detail_360(self, db: Session, settings: Settings, order_id: str) -> dict[str, Any] | None:
        base = self.order_full_detail(db, order_id)
        if not base:
            return None
        order: Order = base["order"]
        quote: Quote | None = base.get("quote")
        booking: Booking | None = base.get("booking")
        invoice: Invoice | None = base.get("invoice")
        customer: Customer | None = base.get("customer")
        payments: list[Payment] = base.get("payments") or []

        merchant = (
            db.query(Merchant).filter(Merchant.id == order.merchant_id).first()
            if order.merchant_id
            else None
        )
        driver = (
            db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
            if order.assigned_driver_id
            else None
        )
        vehicle = self._vehicle_for_driver(db, order.assigned_driver_id)

        events = self.order_timeline(db, order_id)
        domain_events = (
            db.query(DomainEvent)
            .filter(DomainEvent.aggregate_type == "order", DomainEvent.aggregate_id == order_id)
            .order_by(DomainEvent.occurred_at.asc())
            .all()
        )
        audit_logs = (
            db.query(AdminAuditLog)
            .filter(AdminAuditLog.resource_type == "order", AdminAuditLog.resource_id == order_id)
            .order_by(AdminAuditLog.created_at.asc())
            .all()
        )
        exceptions = (
            db.query(OrderException)
            .filter(OrderException.order_id == order_id)
            .order_by(OrderException.created_at.desc())
            .all()
        )
        claims = db.query(Claim).filter(Claim.order_id == order_id).order_by(Claim.created_at.desc()).all()
        tickets = (
            db.query(SupportTicket)
            .filter(SupportTicket.order_id == order_id)
            .order_by(SupportTicket.created_at.desc())
            .all()
        )

        live_tracking = None
        try:
            live_tracking = self._tracking.get_live_tracking(db, settings, order)
        except Exception:
            live_tracking = None

        timeline = []
        for ev in events:
            timeline.append(
                {
                    "source": "order_event",
                    "event_type": ev.event_type,
                    "label": ev.event_type.replace(".", " ").replace("_", " ").title(),
                    "from_state": ev.from_state,
                    "to_state": ev.to_state,
                    "occurred_at": ev.occurred_at,
                    "actor_type": ev.actor_type,
                    "payload": ev.payload,
                }
            )
        for ev in domain_events:
            timeline.append(
                {
                    "source": "domain_event",
                    "event_type": ev.event_type,
                    "label": ev.event_type.replace(".", " ").replace("_", " ").title(),
                    "occurred_at": ev.occurred_at,
                    "actor_type": ev.actor_type,
                    "payload": ev.payload,
                }
            )
        timeline.sort(key=lambda x: str(x.get("occurred_at") or ""))

        packages = []
        if quote:
            packages.append(
                {
                    "weight_kg": quote.weight_kg,
                    "dimensions": quote.dimensions,
                    "declared_value_cents": quote.declared_value_cents,
                    "package_type": quote.package_type,
                    "vehicle_class": quote.vehicle_class,
                }
            )

        pod_events = [ev for ev in events if "pod" in ev.event_type.lower() or ev.to_state == "POD_COMPLETED"]
        pod = pod_events[-1].payload if pod_events else {}

        booking_draft = (
            db.query(BookingDraft).filter(BookingDraft.quote_id == order.quote_id).first()
            if order.quote_id
            else None
        )
        if not booking_draft and booking:
            booking_draft = db.query(BookingDraft).filter(BookingDraft.order_id == order.id).first()

        customer_360: dict[str, Any] | None = None
        if customer:
            cust_orders = db.query(Order).filter(Order.customer_id == customer.id).all()
            customer_360 = {
                "id": customer.id,
                "email": customer.email,
                "phone": customer.phone,
                "lifetime_orders": len(cust_orders),
                "lifetime_revenue_cents": sum(o.amount_cents for o in cust_orders),
                "recent_orders": [
                    {"order_id": o.id, "order_number": o.order_number, "state": o.state}
                    for o in sorted(cust_orders, key=lambda x: x.created_at, reverse=True)[:5]
                ],
            }

        merchant_360: dict[str, Any] | None = None
        if merchant:
            open_orders = (
                db.query(func.count(Order.id))
                .filter(
                    Order.merchant_id == merchant.id,
                    Order.state.notin_(("CLOSED", "CANCELLED", "REFUNDED")),
                )
                .scalar()
                or 0
            )
            merchant_360 = {
                "id": merchant.id,
                "name": merchant.company_name,
                "email": merchant.email,
                "phone": merchant.phone,
                "payment_terms": merchant.payment_terms,
                "credit_limit_cents": merchant.credit_limit_cents,
                "open_orders": int(open_orders),
            }

        driver_360: dict[str, Any] | None = None
        if driver:
            today_start = datetime.combine(self._now().date(), time.min)
            todays = (
                db.query(func.count(Order.id))
                .filter(Order.assigned_driver_id == driver.id, Order.updated_at >= today_start)
                .scalar()
                or 0
            )
            driver_360 = {
                "id": driver.id,
                "name": driver.full_name,
                "phone": driver.phone,
                "email": driver.email,
                "rating": driver.rating,
                "is_online": driver.is_online,
                "availability": driver.availability,
                "wallet_balance_cents": driver.wallet_balance_cents,
                "todays_deliveries": int(todays),
            }

        vehicle_360: dict[str, Any] | None = None
        if vehicle:
            vehicle_360 = {
                "id": vehicle.id,
                "label": f"{vehicle.make_model or vehicle.vehicle_class} ({vehicle.plate_number})",
                "vehicle_class": vehicle.vehicle_class,
                "plate_number": vehicle.plate_number,
                "make_model": vehicle.make_model,
                "capacity_kg": vehicle.capacity_kg,
                "is_active": vehicle.is_active,
            }

        ledger_entries = (
            db.query(BillingLedgerEntry)
            .filter(BillingLedgerEntry.order_id == order_id)
            .order_by(BillingLedgerEntry.created_at.asc())
            .all()
        )

        automation: list[dict[str, Any]] = []
        communications: list[dict[str, Any]] = []
        api_activity: list[dict[str, Any]] = []
        for item in timeline:
            et = str(item.get("event_type", ""))
            if any(et.startswith(p) for p in ("payment.", "notification.", "fleetbase.", "invoice.", "dispatch.", "order.")):
                automation.append(item)
            if any(k in et for k in ("notification", "email", "sms", "push")):
                communications.append(item)
            if any(k in et for k in ("stripe", "fleetbase", "webhook", "api")):
                api_activity.append(item)
        for le in ledger_entries:
            api_activity.append(
                {
                    "source": "billing_ledger",
                    "event_type": le.kind,
                    "label": le.kind.replace("_", " ").title(),
                    "occurred_at": le.created_at,
                    "amount_cents": le.amount_cents,
                    "status": le.status,
                }
            )

        driver_status = "offline"
        if driver:
            driver_status = driver.availability if driver.is_online else "offline"
        vehicle_status = "assigned" if vehicle and order.assigned_driver_id else "available"

        documents = []
        if invoice and invoice.pdf_url:
            documents.append({"type": "invoice_pdf", "name": invoice.invoice_number, "url": invoice.pdf_url})
        if invoice and invoice.stripe_receipt_url:
            documents.append({"type": "receipt", "name": invoice.invoice_number, "url": invoice.stripe_receipt_url})

        merchants = self._merchant_map(db)
        row = self._row(db, order, merchants, self._driver_map(db))

        return {
            **row,
            "special_instructions": order.special_instructions,
            "fleetbase_order_id": order.fleetbase_order_id,
            "customer_phone": customer.phone if customer else None,
            "booking_id": booking.id if booking else None,
            "booking_draft_id": booking_draft.id if booking_draft else None,
            "booking_draft_number": (
                f"PBD-{booking_draft.id[:8].upper()}" if booking_draft else None
            ),
            "quote_id": quote.id if quote else None,
            "vehicle_class": quote.vehicle_class if quote else None,
            "package_type": quote.package_type if quote else None,
            "weight_kg": quote.weight_kg if quote else None,
            "dimensions": quote.dimensions if quote else None,
            "declared_value_cents": quote.declared_value_cents if quote else None,
            "distance_meters": quote.distance_meters if quote else None,
            "quote_amount_cents": quote.amount_cents if quote else None,
            "pricing_breakdown": quote.pricing_breakdown if quote else None,
            "pickup_detail": order.pickup,
            "dropoff_detail": order.dropoff,
            "additional_stops": (quote.additional_stops or []) if quote else [],
            "payments": [
                {
                    "payment_id": p.id,
                    "status": p.status,
                    "amount_cents": p.amount_cents,
                    "currency": p.currency,
                    "stripe_payment_intent_id": p.stripe_payment_intent_id,
                    "stripe_checkout_session_id": p.stripe_checkout_session_id,
                    "receipt_url": p.receipt_url,
                    "failure_reason": p.failure_reason,
                    "retry_count": p.retry_count,
                    "created_at": p.created_at,
                }
                for p in payments
            ],
            "invoice_number": invoice.invoice_number if invoice else None,
            "invoice_amount_cents": invoice.amount_cents if invoice else None,
            "invoice_receipt_url": invoice.stripe_receipt_url if invoice else None,
            "invoice_pdf_url": invoice.pdf_url if invoice else None,
            "merchant": merchant_360 or (
                {
                    "id": merchant.id,
                    "name": merchant.company_name,
                    "email": merchant.email,
                }
                if merchant
                else None
            ),
            "customer_360": customer_360,
            "driver": driver_360 or (
                {
                    "id": driver.id,
                    "name": driver.full_name,
                    "phone": driver.phone,
                    "rating": driver.rating,
                    "is_online": driver.is_online,
                }
                if driver
                else None
            ),
            "vehicle": vehicle_360 or (
                {
                    "id": vehicle.id,
                    "label": f"{vehicle.make_model or vehicle.vehicle_class} ({vehicle.plate_number})",
                    "vehicle_class": vehicle.vehicle_class,
                    "plate_number": vehicle.plate_number,
                }
                if vehicle
                else None
            ),
            "driver_status": driver_status,
            "vehicle_status": vehicle_status,
            "parcel_count": len(packages) or 1,
            "timeline": timeline,
            "tracking": live_tracking,
            "packages": packages,
            "incidents": [
                {
                    "id": ex.id,
                    "type": ex.type,
                    "status": ex.status,
                    "evidence": ex.evidence,
                    "created_at": ex.created_at,
                }
                for ex in exceptions
            ],
            "claims": [
                {
                    "id": c.id,
                    "claim_type": c.claim_type,
                    "status": c.status,
                    "description": c.description,
                    "created_at": c.created_at,
                }
                for c in claims
            ],
            "support_tickets": [
                {
                    "id": t.id,
                    "subject": t.subject,
                    "status": t.status,
                    "priority": t.priority,
                    "created_at": t.created_at,
                }
                for t in tickets
            ],
            "documents": documents,
            "proof_of_delivery": pod,
            "domain_events": [
                {
                    "event_type": ev.event_type,
                    "occurred_at": ev.occurred_at,
                    "payload": ev.payload,
                }
                for ev in domain_events
            ],
            "audit_log": [
                {
                    "action": a.action,
                    "actor_user_id": a.actor_user_id,
                    "payload": a.payload,
                    "created_at": a.created_at,
                }
                for a in audit_logs
            ],
            "internal_notes": [],
            "automation": automation,
            "communications": communications,
            "api_activity": api_activity,
            "duplicates": self.find_duplicates(db, order),
            "smart": self._smart_insights(order, quote, events),
        }

    def reports(self, db: Session) -> dict[str, Any]:
        now = self._now()
        month_start = datetime(now.year, now.month, 1)
        merchants = self._merchant_map(db)
        drivers = self._driver_map(db)

        by_merchant: dict[str, int] = {}
        by_driver: dict[str, int] = {}
        for o in db.query(Order).filter(Order.created_at >= month_start).all():
            if o.merchant_id:
                name = merchants.get(o.merchant_id, o.merchant_id)
                by_merchant[name] = by_merchant.get(name, 0) + 1
            if o.assigned_driver_id:
                name = drivers[o.assigned_driver_id].full_name if o.assigned_driver_id in drivers else o.assigned_driver_id
                by_driver[name] = by_driver.get(name, 0) + 1

        failed = db.query(func.count(Order.id)).filter(Order.state.in_(FAILED_STATES), Order.created_at >= month_start).scalar() or 0
        returns = db.query(func.count(Order.id)).filter(Order.state.in_(RETURNED_STATES), Order.created_at >= month_start).scalar() or 0
        claims = db.query(func.count(Claim.id)).filter(Claim.created_at >= month_start).scalar() or 0
        revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.created_at >= month_start, Order.state.notin_(("CANCELLED", "REFUNDED")))
            .scalar()
            or 0
        )

        return {
            "monthly_orders": db.query(func.count(Order.id)).filter(Order.created_at >= month_start).scalar() or 0,
            "monthly_revenue_cents": int(revenue),
            "failed_deliveries": int(failed),
            "returns": int(returns),
            "claims": int(claims),
            "avg_delivery_hours": self._avg_duration_hours(db, "order.picked_up", "order.delivered"),
            "top_merchants": sorted(by_merchant.items(), key=lambda x: -x[1])[:10],
            "top_drivers": sorted(by_driver.items(), key=lambda x: -x[1])[:10],
        }

    def order_tracking(self, db: Session, settings: Settings, order_id: str) -> dict[str, Any] | None:
        order = self.get_order(db, order_id)
        if not order:
            return None
        live = None
        try:
            live = self._tracking.get_live_tracking(db, settings, order)
        except Exception:
            pass
        return {
            "order_id": order.id,
            "tracking_number": order.tracking_number,
            "state": order.state,
            "scheduled_at": order.scheduled_at,
            "live": live,
            "history": [
                {
                    "event_type": ev.event_type,
                    "to_state": ev.to_state,
                    "occurred_at": ev.occurred_at,
                    "payload": ev.payload,
                }
                for ev in self.order_timeline(db, order_id)
            ],
        }
