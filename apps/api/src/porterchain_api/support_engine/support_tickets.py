"""Support ticket listing, detail, insights, and creation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminAuditLog, Driver, SupportTicket
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_models import Customer, DomainEvent
from porterchain_api.domain.support import TICKET_CATEGORIES, ticket_number
from porterchain_api.merchant_engine.lookups import get_merchant
from porterchain_api.platform.admin_audit import log_admin_audit
from porterchain_api.support_engine.support_helpers import (
    SupportActor,
    SupportFilters,
    append_timeline,
    normalize_status,
    ticket_data,
)
from porterchain_shared.events.catalog import DomainEventType


class SupportTicketsMixin:
    def list_tickets(self, db: Session, *, status: str | None = None, limit: int = 50) -> list[SupportTicket]:
        q = db.query(SupportTicket)
        if status:
            q = q.filter(SupportTicket.status == status)
        return q.order_by(SupportTicket.created_at.desc()).limit(limit).all()

    def open_count_for_merchant(self, db: Session, merchant_id: str) -> int:
        return (
            db.query(func.count(SupportTicket.id))
            .filter(
                SupportTicket.merchant_id == merchant_id,
                SupportTicket.status.in_(("open", "in_progress", "escalated")),
            )
            .scalar()
            or 0
        )

    def list_enriched(self, db: Session, filters: SupportFilters | None = None) -> list[dict[str, Any]]:
        f = filters or SupportFilters()
        q = db.query(SupportTicket)
        if f.status:
            q = q.filter(SupportTicket.status == f.status)
        if f.category:
            q = q.filter(SupportTicket.category == f.category)
        if f.priority:
            q = q.filter(SupportTicket.priority == f.priority)
        if f.agent_id:
            q = q.filter(SupportTicket.assigned_to == f.agent_id)
        if f.merchant_id:
            q = q.filter(SupportTicket.merchant_id == f.merchant_id)
        if f.driver_id:
            q = q.filter(SupportTicket.driver_id == f.driver_id)
        if f.customer_id:
            q = q.filter(SupportTicket.customer_id == f.customer_id)
        if f.date_from:
            q = q.filter(SupportTicket.created_at >= f.date_from)
        if f.date_to:
            q = q.filter(SupportTicket.created_at <= f.date_to)
        if f.module == "internal":
            q = q.filter(SupportTicket.category == "internal_request")
        elif f.module == "finance":
            q = q.filter(
                SupportTicket.category.in_(
                    ("billing_issue", "invoice_issue", "payment_issue", "refund_request")
                )
            )
        elif f.module == "technical":
            q = q.filter(SupportTicket.category.in_(("technical_issue", "api_support")))
        elif f.module == "operations":
            q = q.filter(
                SupportTicket.category.in_(
                    (
                        "tracking_issue",
                        "pickup_issue",
                        "delivery_issue",
                        "late_delivery",
                        "lost_parcel",
                        "damaged_parcel",
                        "wrong_delivery",
                        "fleet_issue",
                    )
                )
            )
        elif f.module == "claims":
            q = q.filter(SupportTicket.category == "claim")
        if f.search:
            term = f"%{f.search.strip()}%"
            q = q.filter(
                or_(
                    SupportTicket.subject.ilike(term),
                    SupportTicket.description.ilike(term),
                    SupportTicket.id.ilike(term),
                )
            )
        tickets = q.order_by(SupportTicket.updated_at.desc()).limit(f.limit).all()
        rows = [self._row(db, t) for t in tickets]
        if f.sla:
            rows = [r for r in rows if r["sla_status"] == f.sla]
        return rows

    def get_ticket(self, db: Session, ticket_id: str) -> SupportTicket | None:
        return db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    def get_detail(self, db: Session, ticket_id: str) -> dict[str, Any] | None:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            return None
        row = self._row(db, ticket)
        ctx = self._order_context(db, ticket.order_id)
        data = ticket_data(ticket)
        customer = (
            db.query(Customer).filter(Customer.id == ticket.customer_id).first()
            if ticket.customer_id
            else None
        )
        merchant = get_merchant(db, ticket.merchant_id)
        driver = (
            db.query(Driver).filter(Driver.id == ticket.driver_id).first()
            if ticket.driver_id
            else None
        )
        domain_events = (
            db.query(DomainEvent)
            .filter(DomainEvent.aggregate_type == "support_ticket", DomainEvent.aggregate_id == ticket.id)
            .order_by(DomainEvent.occurred_at.asc())
            .all()
        )
        audit_logs = (
            db.query(AdminAuditLog)
            .filter(
                AdminAuditLog.resource_type == "support_ticket",
                AdminAuditLog.resource_id == ticket.id,
            )
            .order_by(AdminAuditLog.created_at.asc())
            .all()
        )
        return {
            **row,
            "timeline": data.get("timeline") or [],
            "communications": data.get("communications") or [],
            "internal_notes": data.get("notes") or [],
            "attachments": data.get("attachments") or [],
            "customer": {
                "id": customer.id,
                "email": customer.email,
                "phone": customer.phone,
            }
            if customer
            else (
                {
                    "email": ctx.get("customer_email"),
                    "phone": ctx.get("customer_phone"),
                }
                if ctx.get("customer_email")
                else None
            ),
            "merchant": {
                "id": merchant.id,
                "name": merchant.company_name,
                "email": merchant.email,
                "phone": merchant.phone,
            }
            if merchant
            else ({"name": ctx.get("merchant_name")} if ctx.get("merchant_name") else None),
            "driver": {
                "id": driver.id,
                "name": driver.full_name,
                "phone": driver.phone,
                "email": driver.email,
            }
            if driver
            else ({"name": ctx.get("driver_name")} if ctx.get("driver_name") else None),
            "order": {
                "order_id": ctx.get("order_id"),
                "order_number": ctx.get("order_number"),
                "tracking_number": ctx.get("tracking_number"),
                "state": ctx.get("order_state"),
                "amount_cents": ctx.get("amount_cents"),
            }
            if ctx.get("order_id")
            else None,
            "booking": {
                "booking_id": ctx.get("booking_id"),
                "booking_number": ctx.get("booking_number"),
            }
            if ctx.get("booking_id")
            else None,
            "tracking": {"tracking_number": ctx.get("tracking_number")} if ctx.get("tracking_number") else None,
            "invoice": ctx.get("invoice"),
            "payment": ctx.get("payment"),
            "claims": ctx.get("claims") or [],
            "documents": data.get("attachments") or [],
            "domain_events": [
                {
                    "event_type": e.event_type,
                    "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                    "actor_type": e.actor_type,
                    "payload": e.payload,
                }
                for e in domain_events
            ],
            "audit_log": [
                {
                    "action": a.action,
                    "actor_user_id": a.actor_user_id,
                    "payload": a.payload,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in audit_logs
            ],
            "sla": {
                "status": row["sla_status"],
                "config": self._sla_config(db),
                "paused": bool(data.get("sla_paused")),
                "first_response_at": data.get("first_response_at"),
                "resolved_at": data.get("resolved_at"),
            },
            "duplicates": self.find_duplicates(db, ticket),
            "smart": self.smart_insights(db, ticket),
        }

    def find_duplicates(self, db: Session, ticket: SupportTicket) -> list[dict[str, Any]]:
        if not ticket.order_id and not ticket.customer_id:
            return []
        q = db.query(SupportTicket).filter(SupportTicket.id != ticket.id)
        if ticket.order_id:
            q = q.filter(SupportTicket.order_id == ticket.order_id)
        elif ticket.customer_id:
            q = q.filter(SupportTicket.customer_id == ticket.customer_id)
        others = q.order_by(SupportTicket.created_at.desc()).limit(5).all()
        return [
            {
                "id": o.id,
                "ticket_number": ticket_number(o.id),
                "subject": o.subject,
                "status": normalize_status(o.status),
            }
            for o in others
        ]

    def smart_insights(self, db: Session, ticket: SupportTicket) -> dict[str, Any]:
        subject = (ticket.subject or "").lower()
        desc = (ticket.description or "").lower()
        text = f"{subject} {desc}"
        suggested_category = ticket.category or "general_inquiry"
        suggested_priority = ticket.priority or "normal"
        if any(w in text for w in ("urgent", "asap", "emergency")):
            suggested_priority = "urgent"
        if any(w in text for w in ("lost", "missing")):
            suggested_category = "lost_parcel"
        elif any(w in text for w in ("damage", "broken")):
            suggested_category = "damaged_parcel"
        elif any(w in text for w in ("refund", "charge")):
            suggested_category = "refund_request"
        elif any(w in text for w in ("invoice", "billing")):
            suggested_category = "billing_issue"
        elif any(w in text for w in ("track", "where")):
            suggested_category = "tracking_issue"
        sentiment = "neutral"
        if any(w in text for w in ("angry", "terrible", "awful", "furious")):
            sentiment = "negative"
        elif any(w in text for w in ("thank", "great", "excellent")):
            sentiment = "positive"
        kb = self.get_knowledge_base(db)
        related = [
            a for a in kb.get("articles", [])
            if any(w in str(a.get("title", "")).lower() for w in text.split()[:5] if len(w) > 4)
        ][:3]
        duplicates = self.find_duplicates(db, ticket)
        summary = f"{ticket.subject}. Priority {ticket.priority}, status {normalize_status(ticket.status)}."
        if ticket.order_id:
            ctx = self._order_context(db, ticket.order_id)
            if ctx.get("tracking_number"):
                summary += f" Linked to tracking {ctx['tracking_number']}."
        return {
            "ai_summary": summary,
            "suggested_category": suggested_category,
            "suggested_priority": suggested_priority,
            "sentiment": sentiment,
            "related_kb_articles": related,
            "duplicate_count": len(duplicates),
        }

    def create_ticket(
        self,
        db: Session,
        ctx: SupportActor,
        *,
        subject: str,
        description: str | None = None,
        priority: str = "normal",
        category: str = "general_inquiry",
        order_id: str | None = None,
        customer_id: str | None = None,
        merchant_id: str | None = None,
        driver_id: str | None = None,
    ) -> SupportTicket:
        if category not in TICKET_CATEGORIES:
            category = "other"
        if order_id and not (customer_id or merchant_id or driver_id):
            ctx_data = self._order_context(db, order_id)
            customer_id = customer_id or ctx_data.get("customer_id")
            merchant_id = merchant_id or ctx_data.get("merchant_id")
            driver_id = driver_id or ctx_data.get("driver_id")
        ticket = SupportTicket(
            subject=subject,
            description=description,
            priority=priority,
            category=category,
            order_id=order_id,
            customer_id=customer_id,
            merchant_id=merchant_id,
            driver_id=driver_id,
            assigned_to=ctx.user.id,
            ticket_data={"timeline": [], "communications": [], "notes": [], "attachments": []},
        )
        db.add(ticket)
        db.flush()
        append_timeline(ticket, label="Ticket created", actor_type="admin", actor_id=ctx.user.id)
        log_admin_audit(
            db,
            ctx,
            action="support.ticket.create",
            resource_type="support_ticket",
            resource_id=ticket.id,
            payload={"subject": subject, "category": category},
        )
        contact_email: str | None = None
        if customer_id:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            contact_email = customer.email if customer else None
        emit_event(
            db,
            event_type=DomainEventType.SUPPORT_TICKET_CREATED,
            aggregate_type="support_ticket",
            aggregate_id=ticket.id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={
                "subject": subject,
                "ticket_number": ticket_number(ticket.id),
                "email": contact_email,
                "order_id": order_id,
            },
        )
        db.commit()
        db.refresh(ticket)
        return ticket

    def list_for_customer(self, db: Session, customer_id: str, *, limit: int = 20) -> list[SupportTicket]:
        return (
            db.query(SupportTicket)
            .filter(SupportTicket.customer_id == customer_id)
            .order_by(SupportTicket.created_at.desc())
            .limit(limit)
            .all()
        )

    def create_actor_ticket(
        self,
        db: Session,
        *,
        subject: str,
        description: str | None = None,
        priority: str = "normal",
        category: str = "general_inquiry",
        order_id: str | None = None,
        customer_id: str | None = None,
        merchant_id: str | None = None,
        driver_id: str | None = None,
        actor_type: str,
        actor_id: str,
        idempotency_key: str | None = None,
    ) -> SupportTicket:
        from porterchain_shared.events.catalog import DomainEventType

        if category not in TICKET_CATEGORIES:
            category = "other"
        key = (idempotency_key or "").strip()
        if key and customer_id:
            prior = (
                db.query(SupportTicket)
                .filter(SupportTicket.customer_id == customer_id)
                .order_by(SupportTicket.created_at.desc())
                .limit(50)
                .all()
            )
            for row in prior:
                data = row.ticket_data if isinstance(row.ticket_data, dict) else {}
                if data.get("idempotency_key") == key:
                    return row
        extra: dict[str, Any] = {"timeline": [], "communications": [], "notes": [], "attachments": []}
        if key:
            extra["idempotency_key"] = key
        ticket = SupportTicket(
            subject=subject,
            description=description,
            priority=priority,
            category=category,
            order_id=order_id,
            customer_id=customer_id,
            merchant_id=merchant_id,
            driver_id=driver_id,
            ticket_data=extra,
        )
        db.add(ticket)
        db.flush()
        append_timeline(
            ticket,
            label=f"Ticket created by {actor_type}",
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"category": category},
        )
        contact_email: str | None = None
        if customer_id:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            contact_email = customer.email if customer else None
        emit_event(
            db,
            event_type=DomainEventType.SUPPORT_TICKET_CREATED,
            aggregate_type="support_ticket",
            aggregate_id=ticket.id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "subject": subject,
                "ticket_number": ticket_number(ticket.id),
                "email": contact_email,
                "order_id": order_id,
                "merchant_id": merchant_id,
            },
        )
        db.commit()
        db.refresh(ticket)
        return ticket
