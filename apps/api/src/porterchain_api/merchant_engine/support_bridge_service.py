"""Merchant support & claims — orchestrates admin modules (masterrule §3)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.claims_service import (
    CLAIM_TYPES,
    AdminClaimsService,
    ClaimFilters,
    claim_number,
)
from porterchain_api.admin_engine.support_service import (
    AdminSupportService,
    SupportFilters,
    TICKET_CATEGORIES,
    _append_timeline,
    ticket_number,
)
from porterchain_api.admin_models import Claim, SupportTicket
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import MerchantAuditLog
from porterchain_api.models import Order


MERCHANT_KB_CATEGORIES = frozenset({"merchants", "developers"})


class MerchantSupportBridgeService:
    def __init__(self) -> None:
        self._support = AdminSupportService()
        self._claims = AdminClaimsService()

    def list_tickets(self, db: Session, ctx: MerchantContext, *, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._support.list_enriched(
            db,
            SupportFilters(merchant_id=ctx.merchant.id, limit=limit),
        )
        return [
            {
                "ticket_id": r.get("ticket_id") or r.get("id"),
                "ticket_number": r.get("ticket_number"),
                "subject": r.get("subject"),
                "status": r.get("status"),
                "priority": r.get("priority"),
                "category": r.get("category"),
                "order_number": r.get("order_number"),
                "tracking_number": r.get("tracking_number"),
                "sla_status": r.get("sla_status"),
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
            }
            for r in rows
        ]

    def get_ticket(self, db: Session, ctx: MerchantContext, ticket_id: str) -> dict[str, Any]:
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket or ticket.merchant_id != ctx.merchant.id:
            raise LookupError("ticket_not_found")
        row = self._support._row(db, ticket)  # noqa: SLF001 — orchestration only
        data = ticket.ticket_data or {}
        return {**row, "timeline": data.get("timeline") or []}

    def create_ticket(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        subject: str,
        description: str | None = None,
        category: str = "merchant_support",
        priority: str = "normal",
        order_id: str | None = None,
    ) -> dict[str, Any]:
        if category not in TICKET_CATEGORIES:
            category = "merchant_support"
        if order_id:
            self._require_order(db, ctx, order_id)
        ticket = SupportTicket(
            subject=subject,
            description=description,
            priority=priority,
            category=category,
            order_id=order_id,
            merchant_id=ctx.merchant.id,
            ticket_data={"timeline": [], "communications": [], "notes": [], "attachments": []},
        )
        db.add(ticket)
        db.flush()
        _append_timeline(
            ticket,
            label="Ticket created by merchant",
            actor_type="merchant",
            actor_id=ctx.user.id,
            payload={"category": category},
        )
        db.add(
            MerchantAuditLog(
                merchant_id=ctx.merchant.id,
                actor_user_id=ctx.user.id,
                action="support.ticket_created",
                resource_type="support_ticket",
                resource_id=ticket.id,
                payload={"subject": subject},
            )
        )
        emit_event(
            db,
            event_type=E.TICKET_CREATED,
            aggregate_type="support_ticket",
            aggregate_id=ticket.id,
            actor_type="merchant",
            actor_id=ctx.user.id,
            payload={
                "subject": subject,
                "ticket_number": ticket_number(ticket.id),
                "merchant_id": ctx.merchant.id,
            },
        )
        db.commit()
        db.refresh(ticket)
        return self.get_ticket(db, ctx, ticket.id)

    def knowledge_base(self, db: Session) -> dict[str, Any]:
        kb = self._support.get_knowledge_base(db)
        categories = [
            c for c in kb.get("categories") or [] if c.get("id") in MERCHANT_KB_CATEGORIES
        ]
        cat_ids = {c["id"] for c in categories}
        articles = [
            a
            for a in kb.get("articles") or []
            if a.get("published", True) and a.get("category_id") in cat_ids
        ]
        faq = list(kb.get("faq") or [])[:20]
        return {"categories": categories, "articles": articles, "faq": faq}

    def list_claims(self, db: Session, ctx: MerchantContext, *, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._claims.list_enriched(db, ClaimFilters(merchant_id=ctx.merchant.id, limit=limit))
        return [
            {
                "claim_id": r.get("id"),
                "claim_number": r.get("claim_number"),
                "claim_type": r.get("claim_type"),
                "status": r.get("status"),
                "order_id": r.get("order_id"),
                "order_number": r.get("order_number"),
                "tracking_number": r.get("tracking_number"),
                "amount_cents": r.get("amount_cents"),
                "created_at": r.get("created_at"),
                "resolved_at": r.get("resolved_at"),
            }
            for r in rows
        ]

    def get_claim(self, db: Session, ctx: MerchantContext, claim_id: str) -> dict[str, Any]:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise LookupError("claim_not_found")
        row = self._claims._row(db, claim)  # noqa: SLF001
        if row.get("merchant_id") != ctx.merchant.id:
            raise LookupError("claim_not_found")
        return row

    def open_claim(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        order_id: str,
        claim_type: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        self._require_order(db, ctx, order_id)
        normalized = claim_type if claim_type in CLAIM_TYPES else "merchant_complaint"
        claim = Claim(
            order_id=order_id,
            claim_type=normalized,
            description=description,
            status="new",
        )
        db.add(claim)
        db.flush()
        self._claims._append_timeline(  # noqa: SLF001
            db,
            claim,
            label="Claim filed by merchant",
            actor_type="merchant",
            actor_id=ctx.user.id,
            payload={"claim_type": normalized},
        )
        db.add(
            MerchantAuditLog(
                merchant_id=ctx.merchant.id,
                actor_user_id=ctx.user.id,
                action="claim.opened",
                resource_type="claim",
                resource_id=claim.id,
                payload={"order_id": order_id, "claim_type": normalized},
            )
        )
        order = db.query(Order).filter(Order.id == order_id).first()
        emit_event(
            db,
            event_type=E.CLAIM_OPENED,
            aggregate_type="claim",
            aggregate_id=claim.id,
            actor_type="merchant",
            actor_id=ctx.user.id,
            payload={
                "order_id": order_id,
                "claim_type": normalized,
                "claim_number": claim_number(claim.id),
                "order_number": order.order_number if order else "",
            },
        )
        db.commit()
        db.refresh(claim)
        return self.get_claim(db, ctx, claim.id)

    def _require_order(self, db: Session, ctx: MerchantContext, order_id: str) -> Order:
        order = db.query(Order).filter(Order.id == order_id, Order.merchant_id == ctx.merchant.id).first()
        if not order:
            raise LookupError("order_not_found")
        return order
