"""Shared helpers for claims enrichment and timeline."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Claim, Driver
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.domain.claims import claim_number
from porterchain_api.merchant_models import Merchant
from porterchain_api.booking_models import Customer, Order
from porterchain_api.support_engine.claims_constants import claim_meta, normalize_status


class ClaimsHelpersMixin:
    def _order_context(self, db: Session, order_id: str) -> dict[str, Any]:
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
        return {
            "order": order,
            "tracking_number": order.tracking_number,
            "order_number": order.order_number,
            "amount_cents": order.amount_cents,
            "merchant_id": order.merchant_id,
            "merchant_name": merchant.company_name if merchant else None,
            "customer_id": order.customer_id,
            "customer_email": customer.email if customer else None,
            "customer_phone": customer.phone if customer else None,
            "driver_id": order.assigned_driver_id,
            "driver_name": driver.full_name if driver else None,
        }

    def _claim_amount(self, claim: Claim, ctx: dict[str, Any]) -> int:
        comp = (claim.resolution or {}).get("compensation") or {}
        if comp.get("claim_amount_cents"):
            return int(comp["claim_amount_cents"])
        return int(ctx.get("amount_cents") or 0)

    def _risk_score(self, claim: Claim, ctx: dict[str, Any]) -> int:
        meta = claim_meta(claim)
        if meta.get("risk_score") is not None:
            return int(meta["risk_score"])
        score = 20
        ctype = claim.claim_type or ""
        if ctype in ("fraud_investigation", "chargeback", "payment_dispute"):
            score += 40
        if ctype in ("lost_parcel", "damaged_parcel"):
            score += 25
        amount = self._claim_amount(claim, ctx)
        if amount >= 50000:
            score += 20
        elif amount >= 20000:
            score += 10
        status = normalize_status(claim.status)
        if status.startswith("waiting_"):
            score += 15
        return min(100, score)

    def _append_timeline(
        self,
        db: Session,
        claim: Claim,
        *,
        label: str,
        actor_type: str = "system",
        actor_id: str | None = None,
        payload: dict | None = None,
    ) -> None:
        ev = dict(claim.evidence or {})
        timeline = list(ev.get("timeline") or [])
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
        ev["timeline"] = timeline
        claim.evidence = ev
        emit_event(
            db,
            event_type=f"claim.{label.lower().replace(' ', '_')}",
            aggregate_type="claim",
            aggregate_id=claim.id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"label": label, **(payload or {})},
        )

    def _row(self, db: Session, claim: Claim) -> dict[str, Any]:
        ctx = self._order_context(db, claim.order_id)
        meta = claim_meta(claim)
        investigator_id = claim.assigned_to
        investigator_name = None
        if investigator_id:
            inv = db.query(AdminUser).filter(AdminUser.id == investigator_id).first()
            investigator_name = inv.name or inv.email if inv else None
        insurance = (claim.resolution or {}).get("insurance") or {}
        return {
            "id": claim.id,
            "claim_number": claim_number(claim.id),
            "claim_type": claim.claim_type,
            "priority": meta.get("priority", "normal"),
            "status": claim.status,
            "display_status": normalize_status(claim.status),
            "merchant_id": ctx.get("merchant_id"),
            "merchant_name": ctx.get("merchant_name"),
            "customer_id": ctx.get("customer_id"),
            "customer_email": ctx.get("customer_email"),
            "driver_id": ctx.get("driver_id"),
            "driver_name": ctx.get("driver_name"),
            "order_id": claim.order_id,
            "tracking_number": ctx.get("tracking_number"),
            "order_number": ctx.get("order_number"),
            "amount_cents": self._claim_amount(claim, ctx),
            "has_insurance": bool(insurance.get("provider")),
            "assigned_investigator_id": investigator_id,
            "assigned_investigator": investigator_name,
            "risk_score": self._risk_score(claim, ctx),
            "description": claim.description,
            "created_at": claim.created_at,
            "updated_at": claim.resolved_at or claim.created_at,
            "resolved_at": claim.resolved_at,
        }
