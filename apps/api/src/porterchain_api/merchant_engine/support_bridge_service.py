"""Merchant support & claims — orchestrates admin modules (masterrule §3)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.support_engine.claims_service import AdminClaimsService, ClaimFilters
from porterchain_api.support_engine.support_service import AdminSupportService, SupportFilters
from porterchain_api.domain.claims import CLAIM_TYPES
from porterchain_api.domain.support import TICKET_CATEGORIES
from porterchain_api.booking_engine.repositories.order_repository import OrderRepository
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import MerchantAuditLog
from porterchain_api.booking_models import Order

_CLAIM_ERRORS = {
    "order_not_found": "That order was not found.",
    "order_ref_required": "Enter an order number or tracking number.",
}


def claim_error_message(code: str) -> str:
    key = (code or "").strip()
    return _CLAIM_ERRORS.get(key, _CLAIM_ERRORS["order_not_found"])


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
        ticket = self._support.get_ticket(db, ticket_id)
        if not ticket or ticket.merchant_id != ctx.merchant.id:
            raise LookupError("ticket_not_found")
        row = self._support._row(db, ticket)  # noqa: SLF001 — orchestration only
        data = ticket.ticket_data or {}
        return {
            **row,
            "ticket_id": ticket.id,
            "timeline": data.get("timeline") or [],
        }

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
        ticket = self._support.create_actor_ticket(
            db,
            subject=subject,
            description=description,
            priority=priority,
            category=category,
            order_id=order_id,
            merchant_id=ctx.merchant.id,
            actor_type="merchant",
            actor_id=ctx.user.id,
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
        db.commit()
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
        claim = self._claims.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        row = self._claims._row(db, claim)  # noqa: SLF001
        if row.get("merchant_id") != ctx.merchant.id:
            raise LookupError("claim_not_found")
        ev = claim.evidence or {}
        return {
            **row,
            "claim_id": claim.id,
            "description": claim.description,
            "timeline": ev.get("timeline") or [],
        }

    def open_claim(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        claim_type: str,
        description: str | None = None,
        order_id: str | None = None,
        order_number: str | None = None,
    ) -> dict[str, Any]:
        order = self._resolve_order(db, ctx, order_id=order_id, order_number=order_number)
        normalized = claim_type if claim_type in CLAIM_TYPES else "merchant_complaint"
        claim = self._claims.open_actor_claim(
            db,
            order_id=order.id,
            claim_type=normalized,
            description=description,
            status="new",
            actor_type="merchant",
            actor_id=ctx.user.id,
            commit=False,
        )
        db.add(
            MerchantAuditLog(
                merchant_id=ctx.merchant.id,
                actor_user_id=ctx.user.id,
                action="claim.opened",
                resource_type="claim",
                resource_id=claim.id,
                payload={"order_id": order.id, "claim_type": normalized},
            )
        )
        db.commit()
        db.refresh(claim)
        return self.get_claim(db, ctx, claim.id)

    def _require_order(self, db: Session, ctx: MerchantContext, order_id: str) -> Order:
        return self._resolve_order(db, ctx, order_id=order_id)

    def _resolve_order(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        order_id: str | None = None,
        order_number: str | None = None,
    ) -> Order:
        refs = [part.strip() for part in (order_id, order_number) if part and str(part).strip()]
        if not refs:
            raise ValueError("order_ref_required")
        repo = OrderRepository()
        for ref in refs:
            by_id = repo.get_for_merchant(db, ctx.merchant.id, ref)
            if by_id:
                return by_id
            by_lookup = repo.get_by_lookup_for_merchant(db, ctx.merchant.id, ref)
            if by_lookup:
                return by_lookup
        raise LookupError("order_not_found")
