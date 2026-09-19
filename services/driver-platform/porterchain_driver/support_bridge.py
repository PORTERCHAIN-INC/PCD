"""Driver support hub — orchestrates Support and Claims modules (masterrule §3)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

DRIVER_KB_CATEGORIES = frozenset({"drivers", "internal"})

DRIVER_INCIDENT_TYPES: list[dict[str, Any]] = [
    {
        "id": "accident_report",
        "label": "Accident Report",
        "creates_claim": True,
        "claim_type": "vehicle_damage",
        "priority": "critical",
    },
    {
        "id": "damaged_parcel",
        "label": "Damaged Parcel",
        "creates_claim": True,
        "claim_type": "damaged_parcel",
        "priority": "high",
    },
    {
        "id": "lost_parcel",
        "label": "Lost Parcel",
        "creates_claim": True,
        "claim_type": "lost_parcel",
        "priority": "high",
    },
    {
        "id": "unable_to_deliver",
        "label": "Unable To Deliver",
        "creates_claim": True,
        "claim_type": "delivery_failed",
        "priority": "high",
    },
    {
        "id": "customer_not_available",
        "label": "Customer Not Available",
        "creates_claim": False,
        "claim_type": None,
        "priority": "normal",
    },
    {
        "id": "vehicle_breakdown",
        "label": "Vehicle Breakdown",
        "creates_claim": True,
        "claim_type": "vehicle_damage",
        "priority": "critical",
    },
]

_INCIDENT_MAP = {t["id"]: t for t in DRIVER_INCIDENT_TYPES}


class DriverSupportBridgeService:
    def __init__(self) -> None:
        from porterchain_api.admin_engine.claims_service import AdminClaimsService
        from porterchain_api.admin_engine.support_service import AdminSupportService

        self._support = AdminSupportService()
        self._claims = AdminClaimsService()

    def snapshot(self, db: Session, driver: Any) -> dict[str, Any]:
        from porterchain_driver.incidents import IncidentService

        return {
            "tickets": self.list_tickets(db, driver.id),
            "claims": self.list_claims(db, driver.id),
            "incidents": IncidentService().list_incidents(db, driver.id),
            "incident_types": DRIVER_INCIDENT_TYPES,
            "emergency_contact": self.emergency_contact(driver),
            "knowledge_base": self.knowledge_base(db),
            "chat": {
                "enabled": False,
                "status": "coming_soon",
                "message": "Live chat will be available in a future release.",
                "channel_id": None,
            },
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def list_tickets(self, db: Session, driver_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        from porterchain_api.admin_engine.support_service import SupportFilters, ticket_number

        rows = self._support.list_enriched(db, SupportFilters(driver_id=driver_id, limit=limit))
        return [
            {
                "id": r.get("ticket_id") or r.get("id"),
                "ticket_number": r.get("ticket_number") or ticket_number(str(r.get("ticket_id") or r.get("id"))),
                "subject": r.get("subject"),
                "status": r.get("status"),
                "priority": r.get("priority"),
                "category": r.get("category"),
                "order_id": r.get("order_id"),
                "order_number": r.get("order_number"),
                "tracking_number": r.get("tracking_number"),
                "description": r.get("description"),
                "sla_status": r.get("sla_status"),
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
            }
            for r in rows
        ]

    def create_ticket(
        self,
        db: Session,
        driver: Any,
        *,
        subject: str,
        description: str | None = None,
        order_id: str | None = None,
        priority: str = "normal",
        category: str = "driver_support",
    ) -> dict[str, Any]:
        from porterchain_api.admin_engine.support_service import TICKET_CATEGORIES, _append_timeline, ticket_number
        from porterchain_api.admin_engine import events as E
        from porterchain_api.admin_models import SupportTicket
        from porterchain_api.booking_engine._core import emit_event
        from porterchain_api.booking_models import Order

        if category not in TICKET_CATEGORIES:
            category = "driver_support"
        if order_id:
            order = (
                db.query(Order)
                .filter(Order.id == order_id, Order.assigned_driver_id == driver.id)
                .first()
            )
            if not order:
                raise LookupError("order_not_found")

        ticket = SupportTicket(
            driver_id=driver.id,
            subject=subject,
            description=description,
            priority=priority,
            category=category,
            order_id=order_id,
            ticket_data={"timeline": [], "communications": [], "notes": [], "attachments": []},
        )
        db.add(ticket)
        db.flush()
        _append_timeline(
            ticket,
            label="Ticket created by driver",
            actor_type="driver",
            actor_id=driver.id,
            payload={"category": category},
        )
        emit_event(
            db,
            event_type=E.TICKET_CREATED,
            aggregate_type="support_ticket",
            aggregate_id=ticket.id,
            actor_type="driver",
            actor_id=driver.id,
            payload={
                "subject": subject,
                "ticket_number": ticket_number(ticket.id),
                "driver_id": driver.id,
            },
        )
        db.flush()
        return {
            "id": ticket.id,
            "ticket_number": ticket_number(ticket.id),
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "category": ticket.category,
            "order_id": ticket.order_id,
            "description": ticket.description,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        }

    def list_claims(self, db: Session, driver_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        from porterchain_api.admin_engine.claims_service import ClaimFilters

        rows = self._claims.list_enriched(db, ClaimFilters(driver_id=driver_id, limit=limit))
        return [
            {
                "id": r.get("id"),
                "claim_number": r.get("claim_number"),
                "claim_type": r.get("claim_type"),
                "status": r.get("status"),
                "order_id": r.get("order_id"),
                "order_number": r.get("order_number"),
                "tracking_number": r.get("tracking_number"),
                "amount_cents": r.get("amount_cents"),
                "description": r.get("description"),
                "created_at": r.get("created_at"),
                "resolved_at": r.get("resolved_at"),
            }
            for r in rows
        ]

    def open_claim(
        self,
        db: Session,
        driver: Any,
        *,
        order_id: str,
        claim_type: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.admin_engine.claims_service import CLAIM_TYPES, claim_number
        from porterchain_api.admin_engine import events as E
        from porterchain_api.admin_models import Claim
        from porterchain_api.booking_engine._core import emit_event
        from porterchain_api.booking_models import Order

        order = (
            db.query(Order)
            .filter(Order.id == order_id, Order.assigned_driver_id == driver.id)
            .first()
        )
        if not order:
            raise LookupError("order_not_found")

        normalized = claim_type if claim_type in CLAIM_TYPES else "driver_complaint"
        claim = Claim(
            order_id=order_id,
            claim_type=normalized,
            description=description,
            status="new",
            evidence={"_meta": {"reported_by_driver_id": driver.id}},
        )
        db.add(claim)
        db.flush()
        self._claims._append_timeline(  # noqa: SLF001
            db,
            claim,
            label="Claim filed by driver",
            actor_type="driver",
            actor_id=driver.id,
            payload={"claim_type": normalized},
        )
        emit_event(
            db,
            event_type=E.CLAIM_OPENED,
            aggregate_type="claim",
            aggregate_id=claim.id,
            actor_type="driver",
            actor_id=driver.id,
            payload={
                "order_id": order_id,
                "claim_type": normalized,
                "claim_number": claim_number(claim.id),
                "order_number": order.order_number,
            },
        )
        db.flush()
        rows = self.list_claims(db, driver.id, limit=1)
        return rows[0] if rows else {"id": claim.id, "claim_number": claim_number(claim.id)}

    def knowledge_base(self, db: Session) -> dict[str, Any]:
        kb = self._support.get_knowledge_base(db)
        categories = [c for c in kb.get("categories") or [] if c.get("id") in DRIVER_KB_CATEGORIES]
        cat_ids = {c["id"] for c in categories}
        articles = [
            a
            for a in kb.get("articles") or []
            if a.get("published", True) and a.get("category_id") in cat_ids
        ]
        faq = list(kb.get("faq") or [])[:30]
        return {"categories": categories, "articles": articles, "faq": faq}

    def emergency_contact(self, driver: Any) -> dict[str, Any]:
        docs = driver.documents or {}
        contact = docs.get("emergency_contact") if isinstance(docs.get("emergency_contact"), dict) else {}
        return {
            "name": contact.get("name"),
            "phone": contact.get("phone"),
            "relationship": contact.get("relationship"),
            "ops_hotline": "+1-800-PORTERCHAIN",
            "ops_email": "support@porterchain.com",
        }

    def update_emergency_contact(
        self,
        db: Session,
        driver: Any,
        *,
        name: str,
        phone: str,
        relationship: str | None = None,
    ) -> dict[str, Any]:
        docs = dict(driver.documents or {})
        docs["emergency_contact"] = {
            "name": name,
            "phone": phone,
            "relationship": relationship,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        driver.documents = docs
        db.flush()
        return self.emergency_contact(driver)

    def incident_type_meta(self, incident_type: str) -> dict[str, Any] | None:
        return _INCIDENT_MAP.get(incident_type)
