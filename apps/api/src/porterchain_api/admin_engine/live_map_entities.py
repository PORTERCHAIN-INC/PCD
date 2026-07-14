"""Search and entity detail views for the live operations map."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower_service import HIGH_PRIORITY_CENTS, IN_FLIGHT
from porterchain_api.admin_engine.live_map_helpers import (
    _coords,
    _driver_ref,
    _merchant_ref,
    _order_vehicle_class,
)
from porterchain_api.admin_models import Driver, Vehicle
from porterchain_api.merchant_models import Merchant, SavedAddress
from porterchain_api.models import Customer, DomainEvent, Order


class LiveMapEntitiesMixin:
    def search(self, db: Session, query: str, *, limit: int = 30) -> list[dict]:
        q = query.strip()
        if len(q) < 2:
            return []
        like = f"%{q}%"
        results: list[dict] = []

        for d in db.query(Driver).filter(or_(Driver.full_name.ilike(like), Driver.phone.ilike(like), Driver.email.ilike(like))).limit(limit).all():
            results.append({"type": "driver", "id": d.id, "label": d.full_name, "subtitle": d.phone, "location": None})

        for v in db.query(Vehicle).filter(Vehicle.plate_number.ilike(like)).limit(limit).all():
            results.append({"type": "vehicle", "id": v.id, "label": v.plate_number, "subtitle": v.vehicle_class, "location": None})

        for m in db.query(Merchant).filter(or_(Merchant.company_name.ilike(like), Merchant.email.ilike(like), Merchant.phone.ilike(like))).limit(limit).all():
            results.append({"type": "merchant", "id": m.id, "label": m.company_name, "subtitle": m.email, "location": None})

        for c in db.query(Customer).filter(or_(Customer.email.ilike(like), Customer.phone.ilike(like))).limit(limit).all():
            results.append({"type": "customer", "id": c.id, "label": c.email, "subtitle": c.phone, "location": None})

        for o in db.query(Order).filter(
            or_(Order.tracking_number.ilike(like), Order.order_number.ilike(like))
        ).limit(limit).all():
            coords = _coords(o.pickup) or _coords(o.dropoff)
            results.append(
                {
                    "type": "order",
                    "id": o.id,
                    "label": o.tracking_number,
                    "subtitle": o.state,
                    "location": {"lat": coords[0], "lng": coords[1]} if coords else None,
                }
            )

        return results[:limit]

    def entity_detail(self, db: Session, entity_type: str, entity_id: str) -> dict[str, Any]:
        if entity_type == "driver":
            return self._driver_detail(db, entity_id)
        if entity_type == "vehicle":
            return self._vehicle_detail(db, entity_id)
        if entity_type == "merchant":
            return self._merchant_detail(db, entity_id)
        if entity_type == "customer":
            return self._customer_detail(db, entity_id)
        if entity_type == "order":
            return self._order_detail(db, entity_id)
        if entity_type == "ticket":
            return self._ticket_detail(db, entity_id)
        if entity_type == "claim":
            return self._claim_detail(db, entity_id)
        raise LookupError("entity_not_found")

    def _ticket_detail(self, db: Session, ticket_id: str) -> dict:
        from porterchain_api.admin_models import SupportTicket
        from porterchain_api.domain.support import ticket_number

        t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not t:
            raise LookupError("entity_not_found")
        return {
            "entity_type": "ticket",
            "entity_id": t.id,
            "title": ticket_number(t.id),
            "subtitle": t.subject,
            "status": t.status,
            "location": None,
            "contact": {},
            "current_job": {"order_id": t.order_id} if t.order_id else None,
            "timeline": [
                {
                    "label": "Ticket created",
                    "at": t.created_at.isoformat() if t.created_at else None,
                },
                {
                    "label": f"Priority · {t.priority}",
                    "at": t.updated_at.isoformat() if t.updated_at else None,
                },
            ],
            "eta": None,
            "notes": [{"body": t.description}] if t.description else [],
            "actions": [
                {"key": "open_ticket", "label": "Open Support", "href": f"/support/{t.id}"},
                *(
                    [{"key": "open_order", "label": "Open Order", "href": f"/orders/{t.order_id}"}]
                    if t.order_id
                    else []
                ),
            ],
            "meta": {
                "category": t.category,
                "priority": t.priority,
                "merchant_id": t.merchant_id,
                "customer_id": t.customer_id,
                "driver_id": t.driver_id,
            },
        }

    def _claim_detail(self, db: Session, claim_id: str) -> dict:
        from porterchain_api.admin_models import Claim
        from porterchain_api.domain.claims import claim_number

        c = db.query(Claim).filter(Claim.id == claim_id).first()
        if not c:
            raise LookupError("entity_not_found")
        order = db.query(Order).filter(Order.id == c.order_id).first()
        return {
            "entity_type": "claim",
            "entity_id": c.id,
            "title": claim_number(c.id),
            "subtitle": c.claim_type.replace("_", " ").title(),
            "status": c.status,
            "location": None,
            "contact": {},
            "current_job": {
                "order_id": c.order_id,
                "tracking_number": order.tracking_number if order else None,
            },
            "timeline": [
                {
                    "label": "Claim opened",
                    "at": c.created_at.isoformat() if c.created_at else None,
                }
            ],
            "eta": None,
            "notes": [{"body": c.description}] if c.description else [],
            "actions": [
                {"key": "open_claim", "label": "Open Claim", "href": f"/claims/{c.id}"},
                {"key": "open_order", "label": "Open Order", "href": f"/orders/{c.order_id}"},
            ],
            "meta": {"claim_type": c.claim_type, "assigned_to": c.assigned_to},
        }

    def _driver_detail(self, db: Session, driver_id: str) -> dict:
        d = db.query(Driver).filter(Driver.id == driver_id).first()
        if not d:
            raise LookupError("entity_not_found")
        pings = self._latest_pings(db)
        ping = pings.get(d.id)
        active = (
            db.query(Order)
            .filter(Order.assigned_driver_id == d.id, Order.state.in_(IN_FLIGHT))
            .first()
        )
        vehicle = db.query(Vehicle).filter(Vehicle.driver_id == d.id, Vehicle.is_active.is_(True)).first()
        timeline = [
            {
                "label": "Driver registered",
                "at": d.created_at.isoformat() if d.created_at else None,
            }
        ]
        if active:
            timeline.append({"label": f"Active order {active.tracking_number}", "at": active.updated_at.isoformat() if active.updated_at else None})
        return {
            "entity_type": "driver",
            "entity_id": d.id,
            "title": d.full_name,
            "subtitle": _driver_ref(d.id),
            "status": d.availability,
            "location": {"lat": ping.lat, "lng": ping.lng} if ping else None,
            "contact": {"phone": d.phone, "email": d.email},
            "current_job": {
                "order_id": active.id,
                "tracking_number": active.tracking_number,
                "state": active.state,
            }
            if active
            else None,
            "timeline": timeline,
            "eta": active.scheduled_at.isoformat() if active and active.scheduled_at else None,
            "notes": [],
            "actions": [
                {"key": "open_driver", "label": "Open Driver", "href": f"/drivers/{d.id}"},
                {"key": "call", "label": "Call Driver", "href": f"tel:{d.phone}" if d.phone else "#"},
            ],
            "meta": {
                "rating": d.rating,
                "vehicle": vehicle.vehicle_class if vehicle else None,
                "online": d.is_online,
            },
        }

    def _vehicle_detail(self, db: Session, vehicle_id: str) -> dict:
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise LookupError("entity_not_found")
        driver = db.query(Driver).filter(Driver.id == v.driver_id).first() if v.driver_id else None
        return {
            "entity_type": "vehicle",
            "entity_id": v.id,
            "title": v.plate_number,
            "subtitle": v.make_model or v.vehicle_class,
            "status": "active" if v.is_active else "inactive",
            "location": None,
            "contact": {},
            "current_job": None,
            "timeline": [],
            "eta": None,
            "notes": [],
            "actions": [
                {"key": "open_vehicle", "label": "Open Vehicle", "href": f"/drivers/{v.driver_id}" if v.driver_id else "#"},
            ],
            "meta": {"vehicle_class": v.vehicle_class, "driver_name": driver.full_name if driver else None},
        }

    def _merchant_detail(self, db: Session, merchant_id: str) -> dict:
        m = db.query(Merchant).filter(Merchant.id == merchant_id).first()
        if not m:
            raise LookupError("entity_not_found")
        addr = db.query(SavedAddress).filter(SavedAddress.merchant_id == m.id).first()
        loc = {"lat": addr.lat, "lng": addr.lng} if addr and addr.lat and addr.lng else None
        return {
            "entity_type": "merchant",
            "entity_id": m.id,
            "title": m.company_name,
            "subtitle": _merchant_ref(m.id),
            "status": m.status,
            "location": loc,
            "contact": {"phone": m.phone, "email": m.email},
            "current_job": None,
            "timeline": [],
            "eta": None,
            "notes": [],
            "actions": [
                {"key": "open_merchant", "label": "Open Merchant", "href": f"/merchants/{m.id}"},
                {"key": "email", "label": "Email Merchant", "href": f"mailto:{m.email}"},
            ],
            "meta": {},
        }

    def _customer_detail(self, db: Session, customer_id: str) -> dict:
        c = db.query(Customer).filter(Customer.id == customer_id).first()
        if not c:
            raise LookupError("entity_not_found")
        return {
            "entity_type": "customer",
            "entity_id": c.id,
            "title": c.email,
            "subtitle": c.phone,
            "status": "active",
            "location": None,
            "contact": {"phone": c.phone, "email": c.email},
            "current_job": None,
            "timeline": [],
            "eta": None,
            "notes": [],
            "actions": [],
            "meta": {},
        }

    def _order_detail(self, db: Session, order_id: str) -> dict:
        o = db.query(Order).filter(Order.id == order_id).first()
        if not o:
            raise LookupError("entity_not_found")
        merchant = db.query(Merchant).filter(Merchant.id == o.merchant_id).first() if o.merchant_id else None
        driver = db.query(Driver).filter(Driver.id == o.assigned_driver_id).first() if o.assigned_driver_id else None
        events = (
            db.query(DomainEvent)
            .filter(DomainEvent.aggregate_type == "order", DomainEvent.aggregate_id == o.id)
            .order_by(DomainEvent.occurred_at.asc())
            .limit(30)
            .all()
        )
        coords = _coords(o.dropoff) or _coords(o.pickup)
        return {
            "entity_type": "order",
            "entity_id": o.id,
            "title": o.tracking_number,
            "subtitle": o.order_number,
            "status": o.state,
            "location": {"lat": coords[0], "lng": coords[1]} if coords else None,
            "contact": {},
            "current_job": {
                "driver": driver.full_name if driver else None,
                "merchant": merchant.company_name if merchant else None,
                "pickup": (o.pickup or {}).get("formatted"),
                "dropoff": (o.dropoff or {}).get("formatted"),
            },
            "timeline": [
                {"label": e.event_type, "at": e.occurred_at.isoformat() if e.occurred_at else None}
                for e in events
            ],
            "eta": o.scheduled_at.isoformat() if o.scheduled_at else None,
            "notes": [],
            "actions": [
                {"key": "open_order", "label": "Open Order", "href": f"/orders?search={o.tracking_number}"},
                {"key": "timeline", "label": "Open Timeline", "href": f"/orders?search={o.tracking_number}"},
            ],
            "meta": {
                "amount_cents": o.amount_cents,
                "vehicle_class": _order_vehicle_class(o),
                "priority": "high" if o.amount_cents >= HIGH_PRIORITY_CENTS else "normal",
            },
        }
