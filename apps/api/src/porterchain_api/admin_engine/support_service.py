"""Enterprise support center — Application Service (masterrule §3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.finance_service import AdminFinanceService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, AdminUser, Claim, SupportTicket, SystemConfig
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E
from porterchain_api.admin_models import Driver
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Booking, Customer, DomainEvent, Invoice, Order, Payment


TICKET_CATEGORIES = frozenset({
    "general_inquiry",
    "booking_issue",
    "quote_issue",
    "tracking_issue",
    "pickup_issue",
    "delivery_issue",
    "late_delivery",
    "lost_parcel",
    "damaged_parcel",
    "wrong_delivery",
    "billing_issue",
    "invoice_issue",
    "payment_issue",
    "refund_request",
    "merchant_support",
    "driver_support",
    "fleet_issue",
    "technical_issue",
    "api_support",
    "account_issue",
    "complaint",
    "suggestion",
    "claim",
    "internal_request",
    "compliance",
    "other",
})

TICKET_STATUSES = frozenset({
    "new",
    "open",
    "assigned",
    "waiting_customer",
    "waiting_merchant",
    "waiting_driver",
    "waiting_internal",
    "escalated",
    "resolved",
    "closed",
    "archived",
    # legacy
    "in_progress",
})

LEGACY_STATUS_MAP = {
    "in_progress": "assigned",
    "open": "open",
}

OPEN_STATUSES = frozenset({
    "new",
    "open",
    "assigned",
    "waiting_customer",
    "waiting_merchant",
    "waiting_driver",
    "waiting_internal",
    "escalated",
    "in_progress",
})

DEFAULT_SLA = {
    "first_response_hours": 4,
    "resolution_hours": 24,
    "escalation_hours": 48,
    "business_hours_only": True,
    "holidays": [],
}


def ticket_number(ticket_id: str) -> str:
    return f"PCT-{ticket_id[:8].upper()}"


def _normalize_status(status: str) -> str:
    return LEGACY_STATUS_MAP.get(status, status)


def _data(ticket: SupportTicket) -> dict[str, Any]:
    return dict(ticket.ticket_data or {})


def _set_data(ticket: SupportTicket, **updates: Any) -> None:
    data = _data(ticket)
    data.update(updates)
    ticket.ticket_data = data


def _append_timeline(
    ticket: SupportTicket,
    *,
    label: str,
    actor_type: str = "system",
    actor_id: str | None = None,
    payload: dict | None = None,
) -> None:
    data = _data(ticket)
    timeline = list(data.get("timeline") or [])
    timeline.append(
        {
            "id": str(uuid.uuid4()),
            "label": label,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            "payload": payload or {},
        }
    )
    data["timeline"] = timeline
    ticket.ticket_data = data


@dataclass
class SupportFilters:
    status: str | None = None
    category: str | None = None
    priority: str | None = None
    agent_id: str | None = None
    merchant_id: str | None = None
    driver_id: str | None = None
    customer_id: str | None = None
    sla: str | None = None
    module: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    search: str | None = None
    limit: int = 500


class AdminSupportService:
    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _sla_config(self, db: Session) -> dict[str, Any]:
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_sla").first()
        if row and row.value:
            return {**DEFAULT_SLA, **row.value}
        return dict(DEFAULT_SLA)

    def set_sla_config(self, db: Session, ctx: AdminContext, value: dict[str, Any]) -> dict[str, Any]:
        merged = {**self._sla_config(db), **value}
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_sla").first()
        if not row:
            row = SystemConfig(key="support_sla", value=merged)
            db.add(row)
        else:
            row.value = merged
        log_admin_audit(db, ctx, action="support.sla.update", resource_type="system_config", resource_id="support_sla")
        db.commit()
        return merged

    def _order_context(self, db: Session, order_id: str | None) -> dict[str, Any]:
        if not order_id:
            return {}
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {}
        merchant = (
            db.query(Merchant).filter(Merchant.id == order.merchant_id).first()
            if order.merchant_id
            else None
        )
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )
        driver = (
            db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
            if order.assigned_driver_id
            else None
        )
        booking = db.query(Booking).filter(Booking.order_id == order.id).first()
        invoice = db.query(Invoice).filter(Invoice.order_id == order.id).order_by(Invoice.created_at.desc()).first()
        payment = db.query(Payment).filter(Payment.order_id == order.id).order_by(Payment.created_at.desc()).first()
        claims = db.query(Claim).filter(Claim.order_id == order.id).all()
        invoice_status = (
            AdminFinanceService()._invoice_status(invoice, order, payment) if invoice else None
        )
        return {
            "order": order,
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "order_state": order.state,
            "amount_cents": order.amount_cents,
            "merchant_id": order.merchant_id,
            "merchant_name": merchant.company_name if merchant else None,
            "customer_id": order.customer_id,
            "customer_email": customer.email if customer else None,
            "customer_phone": customer.phone if customer else None,
            "driver_id": order.assigned_driver_id,
            "driver_name": driver.full_name if driver else None,
            "booking_id": booking.id if booking else None,
            "booking_number": booking.booking_number if booking else None,
            "invoice": {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "amount_cents": invoice.amount_cents,
                "status": invoice_status,
                "pdf_url": invoice.pdf_url,
            }
            if invoice
            else None,
            "payment": {
                "payment_id": payment.id,
                "status": payment.status,
                "amount_cents": payment.amount_cents,
                "stripe_payment_intent_id": payment.stripe_payment_intent_id,
                "receipt_url": payment.receipt_url,
            }
            if payment
            else None,
            "claims": [
                {"id": c.id, "claim_type": c.claim_type, "status": c.status}
                for c in claims
            ],
        }

    def _sla_status(self, db: Session, ticket: SupportTicket) -> str:
        data = _data(ticket)
        if data.get("sla_paused"):
            return "paused"
        cfg = self._sla_config(db)
        created = ticket.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        age_h = (self._now() - created).total_seconds() / 3600
        first_at = data.get("first_response_at")
        resolution_at = data.get("resolved_at")
        if resolution_at:
            return "met"
        if age_h > cfg["resolution_hours"]:
            return "breached"
        if age_h > cfg["resolution_hours"] * 0.75:
            return "at_risk"
        if not first_at and age_h > cfg["first_response_hours"]:
            return "breached"
        if not first_at and age_h > cfg["first_response_hours"] * 0.75:
            return "at_risk"
        return "ok"

    def _agent_name(self, db: Session, user_id: str | None) -> str | None:
        if not user_id:
            return None
        user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        return user.name or user.email if user else None

    def _row(self, db: Session, ticket: SupportTicket) -> dict[str, Any]:
        ctx = self._order_context(db, ticket.order_id)
        customer = (
            db.query(Customer).filter(Customer.id == ticket.customer_id).first()
            if ticket.customer_id
            else None
        )
        merchant = (
            db.query(Merchant).filter(Merchant.id == ticket.merchant_id).first()
            if ticket.merchant_id
            else None
        )
        driver = (
            db.query(Driver).filter(Driver.id == ticket.driver_id).first()
            if ticket.driver_id
            else None
        )
        display_status = _normalize_status(ticket.status)
        return {
            "id": ticket.id,
            "ticket_number": ticket_number(ticket.id),
            "subject": ticket.subject,
            "category": ticket.category or "general_inquiry",
            "priority": ticket.priority,
            "status": ticket.status,
            "display_status": display_status,
            "customer_id": ticket.customer_id or ctx.get("customer_id"),
            "customer_email": customer.email if customer else ctx.get("customer_email"),
            "merchant_id": ticket.merchant_id or ctx.get("merchant_id"),
            "merchant_name": merchant.company_name if merchant else ctx.get("merchant_name"),
            "driver_id": ticket.driver_id or ctx.get("driver_id"),
            "driver_name": driver.full_name if driver else ctx.get("driver_name"),
            "order_id": ticket.order_id,
            "order_number": ctx.get("order_number"),
            "tracking_number": ctx.get("tracking_number"),
            "booking_id": ctx.get("booking_id"),
            "booking_number": ctx.get("booking_number"),
            "assigned_agent_id": ticket.assigned_to,
            "assigned_agent": self._agent_name(db, ticket.assigned_to),
            "sla_status": self._sla_status(db, ticket),
            "description": ticket.description,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
        }

    def list_tickets(self, db: Session, *, status: str | None = None, limit: int = 50) -> list[SupportTicket]:
        q = db.query(SupportTicket)
        if status:
            q = q.filter(SupportTicket.status == status)
        return q.order_by(SupportTicket.created_at.desc()).limit(limit).all()

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

    def dashboard(self, db: Session) -> dict[str, Any]:
        tickets = db.query(SupportTicket).all()
        open_tickets = [t for t in tickets if _normalize_status(t.status) in OPEN_STATUSES]
        urgent = [t for t in open_tickets if t.priority in ("urgent", "critical")]
        breached = [t for t in tickets if self._sla_status(db, t) == "breached"]
        waiting_customer = [t for t in open_tickets if _normalize_status(t.status) == "waiting_customer"]
        waiting_merchant = [t for t in open_tickets if _normalize_status(t.status) == "waiting_merchant"]
        waiting_driver = [t for t in open_tickets if _normalize_status(t.status) == "waiting_driver"]
        waiting_internal = [t for t in open_tickets if _normalize_status(t.status) == "waiting_internal"]
        claims_linked = sum(1 for t in tickets if t.category == "claim" or t.order_id)
        orders_impacted = len({t.order_id for t in tickets if t.order_id})

        first_response_times: list[float] = []
        resolution_times: list[float] = []
        csat_scores: list[float] = []
        for t in tickets:
            data = _data(t)
            if data.get("first_response_at") and t.created_at:
                created = t.created_at.replace(tzinfo=UTC) if t.created_at.tzinfo is None else t.created_at
                first = datetime.fromisoformat(str(data["first_response_at"]).replace("Z", "+00:00"))
                first_response_times.append((first - created).total_seconds() / 3600)
            if data.get("resolved_at") and t.created_at:
                created = t.created_at.replace(tzinfo=UTC) if t.created_at.tzinfo is None else t.created_at
                resolved = datetime.fromisoformat(str(data["resolved_at"]).replace("Z", "+00:00"))
                resolution_times.append((resolved - created).total_seconds() / 3600)
            if data.get("csat_score") is not None:
                csat_scores.append(float(data["csat_score"]))

        agents = (
            db.query(AdminUser)
            .filter(AdminUser.role.in_(("support", "support_lead", "admin", "super_admin")))
            .all()
        )
        workload = []
        for agent in agents:
            assigned = [t for t in open_tickets if t.assigned_to == agent.id]
            workload.append(
                {
                    "agent_id": agent.id,
                    "agent_name": agent.name or agent.email,
                    "open_tickets": len(assigned),
                    "urgent_tickets": sum(1 for t in assigned if t.priority in ("urgent", "critical")),
                }
            )
        workload.sort(key=lambda x: -x["open_tickets"])

        recent = sorted(tickets, key=lambda t: t.updated_at, reverse=True)[:8]
        return {
            "open_tickets": len(open_tickets),
            "urgent_tickets": len(urgent),
            "sla_breaches": len(breached),
            "pending_customer": len(waiting_customer),
            "pending_merchant": len(waiting_merchant),
            "pending_driver": len(waiting_driver),
            "pending_internal": len(waiting_internal),
            "claims_linked": claims_linked,
            "orders_impacted": orders_impacted,
            "avg_first_response_hours": round(sum(first_response_times) / len(first_response_times), 1)
            if first_response_times
            else 0,
            "avg_resolution_hours": round(sum(resolution_times) / len(resolution_times), 1)
            if resolution_times
            else 0,
            "customer_satisfaction": round(sum(csat_scores) / len(csat_scores), 1) if csat_scores else 0,
            "recent_activity": [
                {
                    "ticket_id": t.id,
                    "ticket_number": ticket_number(t.id),
                    "subject": t.subject,
                    "status": _normalize_status(t.status),
                    "updated_at": t.updated_at,
                }
                for t in recent
            ],
            "team_workload": workload[:10],
        }

    def reports(self, db: Session) -> dict[str, Any]:
        tickets = db.query(SupportTicket).all()
        by_type: dict[str, int] = {}
        by_merchant: dict[str, int] = {}
        by_driver: dict[str, int] = {}
        by_agent: dict[str, int] = {}
        monthly: dict[str, int] = {}
        sla_ok = 0
        sla_breach = 0
        for t in tickets:
            by_type[t.category or "other"] = by_type.get(t.category or "other", 0) + 1
            ctx = self._order_context(db, t.order_id)
            if ctx.get("merchant_name"):
                by_merchant[ctx["merchant_name"]] = by_merchant.get(ctx["merchant_name"], 0) + 1
            if ctx.get("driver_name"):
                by_driver[ctx["driver_name"]] = by_driver.get(ctx["driver_name"], 0) + 1
            agent = self._agent_name(db, t.assigned_to) or "Unassigned"
            by_agent[agent] = by_agent.get(agent, 0) + 1
            month = t.created_at.strftime("%Y-%m") if t.created_at else "unknown"
            monthly[month] = monthly.get(month, 0) + 1
            sla = self._sla_status(db, t)
            if sla == "breached":
                sla_breach += 1
            elif sla in ("ok", "met"):
                sla_ok += 1
        dash = self.dashboard(db)
        return {
            "by_type": by_type,
            "by_merchant": dict(sorted(by_merchant.items(), key=lambda x: x[1], reverse=True)[:15]),
            "by_driver": dict(sorted(by_driver.items(), key=lambda x: x[1], reverse=True)[:15]),
            "by_agent": dict(sorted(by_agent.items(), key=lambda x: x[1], reverse=True)[:15]),
            "monthly_trends": dict(sorted(monthly.items())),
            "avg_first_response_hours": dash["avg_first_response_hours"],
            "avg_resolution_hours": dash["avg_resolution_hours"],
            "sla_compliance_percent": round(100 * sla_ok / max(1, sla_ok + sla_breach), 1),
            "customer_satisfaction": dash["customer_satisfaction"],
            "top_issues": [{"cause": k, "count": v} for k, v in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:10]],
        }

    def get_ticket(self, db: Session, ticket_id: str) -> SupportTicket | None:
        return db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    def get_detail(self, db: Session, ticket_id: str) -> dict[str, Any] | None:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            return None
        row = self._row(db, ticket)
        ctx = self._order_context(db, ticket.order_id)
        data = _data(ticket)
        customer = (
            db.query(Customer).filter(Customer.id == ticket.customer_id).first()
            if ticket.customer_id
            else None
        )
        merchant = (
            db.query(Merchant).filter(Merchant.id == ticket.merchant_id).first()
            if ticket.merchant_id
            else None
        )
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
                "status": _normalize_status(o.status),
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
        summary = f"{ticket.subject}. Priority {ticket.priority}, status {_normalize_status(ticket.status)}."
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
        ctx: AdminContext,
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
        _append_timeline(ticket, label="Ticket created", actor_type="admin", actor_id=ctx.user.id)
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
            event_type=E.TICKET_CREATED,
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

    def update_status(self, db: Session, ctx: AdminContext, ticket_id: str, status: str) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        if status not in TICKET_STATUSES:
            raise ValueError("invalid_status")
        old = ticket.status
        ticket.status = status
        data = _data(ticket)
        if status in ("resolved", "closed") and not data.get("resolved_at"):
            _set_data(ticket, resolved_at=datetime.now(UTC).isoformat())
        _append_timeline(
            ticket,
            label=f"Status changed to {status.replace('_', ' ')}",
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"from": old, "to": status},
        )
        log_admin_audit(
            db,
            ctx,
            action="support.ticket.status",
            resource_type="support_ticket",
            resource_id=ticket.id,
            payload={"from": old, "to": status},
        )
        if status in ("resolved", "closed"):
            emit_event(
                db,
                event_type="support.ticket_resolved",
                aggregate_type="support_ticket",
                aggregate_id=ticket.id,
                actor_type="admin",
                actor_id=ctx.user.id,
            )
        db.commit()
        db.refresh(ticket)
        return ticket

    def assign_agent(self, db: Session, ctx: AdminContext, ticket_id: str, agent_id: str) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        ticket.assigned_to = agent_id
        if _normalize_status(ticket.status) in ("new", "open"):
            ticket.status = "assigned"
        _append_timeline(
            ticket,
            label="Agent assigned",
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"agent_id": agent_id},
        )
        log_admin_audit(
            db,
            ctx,
            action="support.ticket.assign",
            resource_type="support_ticket",
            resource_id=ticket.id,
            payload={"agent_id": agent_id},
        )
        db.commit()
        db.refresh(ticket)
        return ticket

    def auto_assign(self, db: Session, ctx: AdminContext, ticket_id: str) -> SupportTicket:
        agents = (
            db.query(AdminUser)
            .filter(AdminUser.is_active.is_(True), AdminUser.role.in_(("support", "support_lead")))
            .all()
        )
        if not agents:
            raise LookupError("no_agents")
        open_counts = {
            a.id: db.query(func.count(SupportTicket.id))
            .filter(
                SupportTicket.assigned_to == a.id,
                SupportTicket.status.in_(tuple(OPEN_STATUSES)),
            )
            .scalar()
            or 0
            for a in agents
        }
        agent_id = min(open_counts, key=open_counts.get)
        return self.assign_agent(db, ctx, ticket_id, agent_id)

    def add_note(
        self,
        db: Session,
        ctx: AdminContext,
        ticket_id: str,
        *,
        body: str,
        internal: bool = True,
        channel: str = "note",
    ) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        data = _data(ticket)
        entry = {
            "id": str(uuid.uuid4()),
            "body": body,
            "channel": channel,
            "internal": internal,
            "author_id": ctx.user.id,
            "at": datetime.now(UTC).isoformat(),
        }
        if internal:
            notes = list(data.get("notes") or [])
            notes.append(entry)
            _set_data(ticket, notes=notes)
            _append_timeline(ticket, label="Internal note added", actor_type="admin", actor_id=ctx.user.id)
        else:
            comms = list(data.get("communications") or [])
            comms.append(entry)
            _set_data(ticket, communications=comms)
            if not data.get("first_response_at"):
                _set_data(ticket, first_response_at=datetime.now(UTC).isoformat())
            _append_timeline(
                ticket,
                label=f"Reply sent via {channel}",
                actor_type="admin",
                actor_id=ctx.user.id,
            )
        log_admin_audit(
            db,
            ctx,
            action="support.ticket.note",
            resource_type="support_ticket",
            resource_id=ticket.id,
            payload={"internal": internal, "channel": channel},
        )
        db.commit()
        db.refresh(ticket)
        return ticket

    def pause_sla(self, db: Session, ctx: AdminContext, ticket_id: str) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        _set_data(ticket, sla_paused=True)
        _append_timeline(ticket, label="SLA paused", actor_type="admin", actor_id=ctx.user.id)
        db.commit()
        db.refresh(ticket)
        return ticket

    def resume_sla(self, db: Session, ctx: AdminContext, ticket_id: str) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        _set_data(ticket, sla_paused=False)
        _append_timeline(ticket, label="SLA resumed", actor_type="admin", actor_id=ctx.user.id)
        db.commit()
        db.refresh(ticket)
        return ticket

    def bulk_action(
        self,
        db: Session,
        ctx: AdminContext,
        ticket_ids: list[str],
        action: str,
        *,
        agent_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        for tid in ticket_ids:
            try:
                if action == "assign" and agent_id:
                    self.assign_agent(db, ctx, tid, agent_id)
                    results.append({"ticket_id": tid, "status": "assigned"})
                elif action == "auto_assign":
                    self.auto_assign(db, ctx, tid)
                    results.append({"ticket_id": tid, "status": "auto_assigned"})
                elif action == "status" and status:
                    self.update_status(db, ctx, tid, status)
                    results.append({"ticket_id": tid, "status": status})
                elif action == "close":
                    self.update_status(db, ctx, tid, "closed")
                    results.append({"ticket_id": tid, "status": "closed"})
                elif action == "escalate":
                    self.update_status(db, ctx, tid, "escalated")
                    results.append({"ticket_id": tid, "status": "escalated"})
                else:
                    results.append({"ticket_id": tid, "status": "unsupported"})
            except Exception as exc:
                results.append({"ticket_id": tid, "status": f"error:{exc}"})
        return results

    def update_ticket(self, db: Session, ticket_id: str, **fields) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        for k, v in fields.items():
            if v is not None and hasattr(ticket, k):
                setattr(ticket, k, v)
        db.commit()
        db.refresh(ticket)
        return ticket

    def get_knowledge_base(self, db: Session) -> dict[str, Any]:
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_kb").first()
        if row and row.value:
            return row.value
        default = {
            "categories": [
                {"id": "customers", "name": "Customer Guides"},
                {"id": "merchants", "name": "Merchant Guides"},
                {"id": "drivers", "name": "Driver Guides"},
                {"id": "developers", "name": "Developer Guides"},
                {"id": "internal", "name": "Internal Documentation"},
            ],
            "articles": [
                {
                    "id": "faq-tracking",
                    "category_id": "customers",
                    "title": "How to track your delivery",
                    "body": "Use your tracking number on the Porterchain tracking page.",
                    "version": 1,
                    "published": True,
                },
                {
                    "id": "faq-refund",
                    "category_id": "customers",
                    "title": "Refund policy",
                    "body": "Refunds are processed within 5-10 business days after approval.",
                    "version": 1,
                    "published": True,
                },
            ],
            "faq": [
                {"question": "Where is my parcel?", "answer": "Check tracking or contact support with your tracking number."},
            ],
        }
        return default

    def save_kb_article(self, db: Session, ctx: AdminContext, article: dict[str, Any]) -> dict[str, Any]:
        kb = self.get_knowledge_base(db)
        articles = list(kb.get("articles") or [])
        aid = article.get("id") or str(uuid.uuid4())
        article["id"] = aid
        article["version"] = int(article.get("version") or 1)
        existing = next((i for i, a in enumerate(articles) if a.get("id") == aid), None)
        if existing is not None:
            articles[existing] = {**articles[existing], **article, "version": articles[existing].get("version", 1) + 1}
        else:
            articles.append(article)
        kb["articles"] = articles
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_kb").first()
        if not row:
            row = SystemConfig(key="support_kb", value=kb)
            db.add(row)
        else:
            row.value = kb
        log_admin_audit(db, ctx, action="support.kb.update", resource_type="system_config", resource_id=aid)
        db.commit()
        return article

    def get_macros(self, db: Session) -> list[dict[str, Any]]:
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_macros").first()
        if row and row.value:
            if isinstance(row.value, dict):
                return list(row.value.get("macros") or [])
            if isinstance(row.value, list):
                return list(row.value)
        return [
            {
                "id": "greeting",
                "title": "Greeting",
                "body": "Hello, thank you for contacting Porterchain Support. How can I help you today?",
                "channel": "email",
            },
            {
                "id": "tracking",
                "title": "Tracking update",
                "body": "I have checked your shipment and will provide an update shortly.",
                "channel": "email",
            },
        ]

    def save_macro(self, db: Session, ctx: AdminContext, macro: dict[str, Any]) -> dict[str, Any]:
        macros = self.get_macros(db)
        mid = macro.get("id") or str(uuid.uuid4())
        macro["id"] = mid
        existing = next((i for i, m in enumerate(macros) if m.get("id") == mid), None)
        if existing is not None:
            macros[existing] = {**macros[existing], **macro}
        else:
            macros.append(macro)
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_macros").first()
        payload = {"macros": macros}
        if not row:
            row = SystemConfig(key="support_macros", value=payload)
            db.add(row)
        else:
            row.value = payload
        log_admin_audit(db, ctx, action="support.macro.update", resource_type="system_config", resource_id=mid)
        db.commit()
        return macro

    def get_automation_rules(self, db: Session) -> dict[str, Any]:
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_automation").first()
        if row and row.value:
            return row.value
        return {
            "auto_assign": True,
            "auto_escalate_breached_sla": True,
            "auto_close_resolved_days": 7,
            "auto_reminder_hours": 24,
            "auto_tagging": True,
            "auto_categorization": True,
            "auto_merge_duplicates": False,
        }

    def set_automation_rules(self, db: Session, ctx: AdminContext, rules: dict[str, Any]) -> dict[str, Any]:
        merged = {**self.get_automation_rules(db), **rules}
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_automation").first()
        if not row:
            row = SystemConfig(key="support_automation", value=merged)
            db.add(row)
        else:
            row.value = merged
        log_admin_audit(db, ctx, action="support.automation.update", resource_type="system_config", resource_id="support_automation")
        db.commit()
        return merged
