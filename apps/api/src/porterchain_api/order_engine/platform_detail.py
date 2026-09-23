"""Order 360° detail view — full lifecycle, parties, and activity."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminAuditLog, Claim, Driver, SupportTicket
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.booking_engine.invoice_service import public_document_url
from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.pod_normalize import normalize_pod
from porterchain_api.merchant_models import Merchant
from porterchain_api.booking_models import Booking, Customer, DomainEvent, Invoice, Order, OrderException, Payment, Quote
from porterchain_api.order_engine.platform_helpers import ops_timeline_label


def resolve_order_additional_stops(order: Order, quote: Quote | None = None) -> list[Any]:
    """Stop SoT for Order 360: compliance.stops → legacy additional_stops → quote."""
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    rich = meta.get("stops")
    if isinstance(rich, list) and rich:
        pickup = order.pickup if isinstance(order.pickup, dict) else {}
        dropoff = order.dropoff if isinstance(order.dropoff, dict) else {}
        ends = {
            str(pickup.get("formatted") or pickup.get("address") or "").strip().lower(),
            str(dropoff.get("formatted") or dropoff.get("address") or "").strip().lower(),
        }
        ordered = sorted(
            (s for s in rich if isinstance(s, dict)),
            key=lambda s: int(s.get("sequence") or 0),
        )
        middles: list[Any] = []
        for s in ordered:
            label = str(s.get("formatted") or s.get("address") or "").strip().lower()
            if label and label in ends:
                continue
            middles.append(
                {
                    "formatted": s.get("formatted") or s.get("address"),
                    "lat": s.get("lat"),
                    "lng": s.get("lng"),
                    "city": s.get("city"),
                    "type": s.get("type"),
                    "sequence": s.get("sequence"),
                    "id": s.get("id"),
                }
            )
        return middles
    legacy = meta.get("additional_stops")
    if isinstance(legacy, list) and legacy:
        return legacy
    if quote and isinstance(quote.additional_stops, list):
        return quote.additional_stops
    return []


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
        live_raw: dict[str, Any] | None = None
        try:
            from porterchain_api.fleetbase_engine.tracking_facade import TrackingFacade

            live_raw = self._tracking.get_live_tracking(db, settings, order)
            snapshot = TrackingFacade.translate_live(live_raw)
            live_tracking = {**snapshot, "driver_location": snapshot.get("location")}
        except Exception:
            live_tracking = None

        fb_status = (live_tracking or {}).get("fleetbase_status")
        fb_mapped = None
        proofs: list[dict[str, Any]] = []
        if isinstance(live_raw, dict):
            raw_proofs = live_raw.get("proofs")
            if isinstance(raw_proofs, list):
                proofs = [p for p in raw_proofs if isinstance(p, dict)]
        if order.fleetbase_order_id and not fb_status:
            try:
                from porterchain_api.fleetbase_engine.integration_bridge import FleetbaseIntegrationBridge

                sync = FleetbaseIntegrationBridge().sync_status_from_fleetbase(settings, order)
                if sync:
                    fb_status = sync.get("status") or fb_status
                    fb_mapped = sync.get("target_state")
                    if not proofs and isinstance(sync.get("proofs"), list):
                        proofs = [p for p in sync["proofs"] if isinstance(p, dict)]
            except Exception:
                pass
        if fb_mapped is None and fb_status:
            try:
                from porterchain_api.fleetbase_engine.status_translator import StatusTranslator

                mapped = StatusTranslator.to_state(status=str(fb_status))
                fb_mapped = mapped.value if mapped else None
            except Exception:
                fb_mapped = None
        pc_upper = str(order.state).upper()
        fb_mapped_upper = str(fb_mapped).upper() if fb_mapped else None
        fb_status_l = str(fb_status).lower() if fb_status else ""
        aligned: bool | None
        if not fb_mapped_upper and not fb_status_l:
            aligned = None
        elif fb_mapped_upper == pc_upper:
            aligned = True
        elif pc_upper in {"POD_COMPLETED", "INVOICED", "CLOSED"} and (
            fb_mapped_upper in {"DELIVERED", "POD_COMPLETED"}
            or fb_status_l in {"completed", "delivered"}
        ):
            # Commercial post-delivery vs Fleetbase execution complete = expected, not drift.
            aligned = True
        else:
            aligned = False
        status_sync = {
            "pc_state": order.state,
            "fleetbase_order_id": order.fleetbase_order_id,
            "fleetbase_status": fb_status,
            "fleetbase_mapped_state": fb_mapped,
            "status_aligned": aligned,
            "truth": "Live from Fleetbase" if fb_status else "PC commercial only",
        }

        timeline = []
        for ev in events:
            timeline.append(
                {
                    "source": "order_event",
                    "event_type": ev.event_type,
                    "label": ops_timeline_label(
                        event_type=ev.event_type,
                        to_state=ev.to_state,
                        payload=ev.payload,
                    ),
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
                    "label": ops_timeline_label(
                        event_type=ev.event_type,
                        payload=ev.payload,
                    ),
                    "occurred_at": ev.occurred_at,
                    "actor_type": ev.actor_type,
                    "payload": ev.payload,
                }
            )
        timeline.sort(key=lambda x: str(x.get("occurred_at") or ""))

        from porterchain_api.merchant_engine.parcel_amend_service import (
            commercial_stops,
            packages_from_order,
            parcel_amendable,
            route_import_job_id,
        )

        cargo_stops = commercial_stops(order)
        packages = packages_from_order(order)
        if not packages and quote:
            packages.append(
                {
                    "weight_kg": quote.weight_kg,
                    "dimensions": quote.dimensions,
                    "declared_value_cents": quote.declared_value_cents,
                    "package_type": quote.package_type,
                    "vehicle_class": quote.vehicle_class,
                }
            )
        meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
        quote_snap = meta.get("quote") if isinstance(meta.get("quote"), dict) else {}
        quote_amount = quote.amount_cents if quote else quote_snap.get("amount_cents")
        from porterchain_api.merchant_engine.quote_snapshot import sanitize_pricing_breakdown

        pricing_breakdown = sanitize_pricing_breakdown(quote.pricing_breakdown if quote else None)
        if not pricing_breakdown and quote_snap:
            pricing_breakdown = sanitize_pricing_breakdown(
                {
                    **quote_snap,
                    "items": quote_snap.get("line_items") or quote_snap.get("items"),
                    "final_cents": quote_snap.get("amount_cents") or quote_snap.get("final_cents"),
                }
            )

        pod = normalize_pod(proofs)
        if not pod.get("complete"):
            pod_events = [
                ev for ev in events if "pod" in ev.event_type.lower() or ev.to_state == "POD_COMPLETED"
            ]
            if pod_events and isinstance(pod_events[-1].payload, dict):
                pod = {**pod, "event_payload": pod_events[-1].payload}

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
            from porterchain_api.driver_engine.wallet_ledger import wallet_balance_cents

            driver_360 = {
                "id": driver.id,
                "name": driver.full_name,
                "phone": driver.phone,
                "email": driver.email,
                "rating": driver.rating,
                "wallet_balance_cents": wallet_balance_cents(
                    db, driver.id, cached_cents=driver.wallet_balance_cents
                ),
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
        api_activity: list[dict[str, Any]] = []
        for item in timeline:
            et = str(item.get("event_type", ""))
            if any(et.startswith(p) for p in ("payment.", "notification.", "fleetbase.", "invoice.", "dispatch.", "order.")):
                automation.append(item)
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

        communications = self._order_communications(db, order_id)

        # Live driver status (online/GPS) is Fleetbase-owned; here we only
        # reflect the commercial assignment state of this order.
        driver_status = "assigned" if driver else "unassigned"
        vehicle_status = "assigned" if vehicle and order.assigned_driver_id else "available"

        receipt_url = public_document_url(invoice.stripe_receipt_url if invoice else None)
        pdf_url = public_document_url(invoice.pdf_url if invoice else None)
        documents = []
        if invoice and pdf_url:
            documents.append({"type": "invoice_pdf", "name": invoice.invoice_number, "url": pdf_url})
        if invoice and receipt_url:
            documents.append({"type": "receipt", "name": invoice.invoice_number, "url": receipt_url})

        merchants = self._merchant_map(db)
        row = self._row(db, order, merchants, self._driver_map(db))

        return {
            **row,
            "special_instructions": order.special_instructions,
            "fleetbase_order_id": order.fleetbase_order_id,
            "status_sync": status_sync,
            "customer_phone": customer.phone if customer else None,
            "booking_id": booking.id if booking else None,
            "booking_draft_id": booking_draft.id if booking_draft else None,
            "booking_draft_number": (
                f"PBD-{booking_draft.id[:8].upper()}" if booking_draft else None
            ),
            "quote_id": quote.id if quote else None,
            "vehicle_class": (quote.vehicle_class if quote else None) or meta.get("vehicle_class"),
            "package_type": quote.package_type if quote else None,
            "weight_kg": (quote.weight_kg if quote else None) or meta.get("weight_kg"),
            "dimensions": (quote.dimensions if quote else None) or meta.get("dimensions"),
            "declared_value_cents": quote.declared_value_cents if quote else None,
            "booking_mode": (quote.parcels or {}).get("booking_mode")
            if quote and isinstance(quote.parcels, dict)
            else None,
            "parcels": (quote.parcels or {}).get("items")
            if quote and isinstance(quote.parcels, dict) and isinstance((quote.parcels or {}).get("items"), list)
            else [],
            "distance_meters": (quote.distance_meters if quote else None)
            or quote_snap.get("distance_meters"),
            "quote_amount_cents": quote_amount,
            "pricing_breakdown": pricing_breakdown,
            "pickup_detail": order.pickup,
            "dropoff_detail": order.dropoff,
            "additional_stops": resolve_order_additional_stops(order, quote),
            "order_kind": meta.get("order_kind"),
            "stops": cargo_stops,
            "parcel_amendable": parcel_amendable(order),
            "route_import_job_id": route_import_job_id(order),
            "payments": [
                {
                    "payment_id": p.id,
                    "status": p.status,
                    "amount_cents": p.amount_cents,
                    "currency": p.currency,
                    "stripe_payment_intent_id": p.stripe_payment_intent_id,
                    "stripe_checkout_session_id": p.stripe_checkout_session_id,
                    "receipt_url": public_document_url(p.receipt_url),
                    "failure_reason": p.failure_reason,
                    "retry_count": p.retry_count,
                    "created_at": p.created_at,
                }
                for p in payments
            ],
            "invoice_number": invoice.invoice_number if invoice else None,
            "invoice_amount_cents": invoice.amount_cents if invoice else None,
            "invoice_receipt_url": receipt_url,
            "invoice_pdf_url": pdf_url,
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

    @staticmethod
    def _order_communications(db: Session, order_id: str) -> list[dict[str, Any]]:
        """Notification delivery history for this order (email / SMS / push / in-app)."""
        try:
            from porterchain_api.notification_engine.models import (
                NotificationDeliveryLog,
                NotificationRecord,
            )

            # Savepoint so a JSON filter miss never aborts the parent 360 transaction.
            with db.begin_nested():
                candidates = (
                    db.query(NotificationRecord)
                    .order_by(NotificationRecord.created_at.desc())
                    .limit(200)
                    .all()
                )
            matched = []
            for r in candidates:
                ctx = r.context if isinstance(r.context, dict) else {}
                tags = r.search_tags if isinstance(r.search_tags, dict) else {}
                if (
                    ctx.get("order_id") == order_id
                    or tags.get("order_id") == order_id
                    or order_id in (r.deep_link or "")
                ):
                    matched.append(r)
                if len(matched) >= 40:
                    break
            if not matched:
                return []
            ids = [r.id for r in matched]
            with db.begin_nested():
                logs = (
                    db.query(NotificationDeliveryLog)
                    .filter(NotificationDeliveryLog.notification_id.in_(ids))
                    .order_by(NotificationDeliveryLog.created_at.desc())
                    .all()
                )
            latest_by_nid: dict[str, NotificationDeliveryLog] = {}
            for log in logs:
                if log.notification_id and log.notification_id not in latest_by_nid:
                    latest_by_nid[log.notification_id] = log
            out: list[dict[str, Any]] = []
            for r in matched:
                log = latest_by_nid.get(r.id)
                out.append(
                    {
                        "id": r.id,
                        "source": "notification",
                        "event_type": r.event_type or r.template_key,
                        "label": r.title or r.template_key,
                        "channel": r.channel,
                        "template_key": r.template_key,
                        "recipient_type": r.recipient_type,
                        "recipient": r.recipient_address,
                        "status": (log.status if log else r.status),
                        "error": (log.error if log else r.failure_reason),
                        "occurred_at": r.created_at,
                        "body": (r.body or "")[:280],
                    }
                )
            return out
        except Exception:
            return []
