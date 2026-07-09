"""Order 360° detail view — full lifecycle, parties, and activity."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminAuditLog, Claim, Driver, SupportTicket
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.config import Settings
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Booking, Customer, DomainEvent, Invoice, Order, OrderException, Payment, Quote


class OrderPlatformDetailMixin:
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
