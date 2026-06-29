"""Merchant lifecycle admin per BUSINESS_WORKFLOW.md §2."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant


class AdminMerchantService:
    def list_merchants(self, db: Session, *, status: str | None = None, limit: int = 50) -> list[Merchant]:
        q = db.query(Merchant)
        if status:
            q = q.filter(Merchant.status == status)
        return q.order_by(Merchant.created_at.desc()).limit(limit).all()

    def get_merchant(self, db: Session, merchant_id: str) -> Merchant | None:
        return db.query(Merchant).filter(Merchant.id == merchant_id).first()

    def approve_merchant(self, db: Session, ctx: AdminContext, merchant_id: str) -> Merchant:
        merchant = self._get_or_raise(db, merchant_id)
        merchant.status = MerchantStatus.ACTIVE.value
        merchant.activated_at = datetime.now(UTC)
        self._audit(db, ctx, "merchant.approved", "merchant", merchant_id, {})
        emit_event(
            db,
            event_type=E.MERCHANT_APPROVED,
            aggregate_type="merchant",
            aggregate_id=merchant_id,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(merchant)
        return merchant

    def suspend_merchant(self, db: Session, ctx: AdminContext, merchant_id: str) -> Merchant:
        merchant = self._get_or_raise(db, merchant_id)
        merchant.status = MerchantStatus.SUSPENDED.value
        self._audit(db, ctx, "merchant.suspended", "merchant", merchant_id, {})
        emit_event(
            db,
            event_type=E.MERCHANT_SUSPENDED,
            aggregate_type="merchant",
            aggregate_id=merchant_id,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(merchant)
        return merchant

    def update_merchant_terms(
        self,
        db: Session,
        ctx: AdminContext,
        merchant_id: str,
        *,
        payment_terms: str | None = None,
        pricing_config: dict | None = None,
        credit_limit_cents: int | None = None,
    ) -> Merchant:
        merchant = self._get_or_raise(db, merchant_id)
        if payment_terms:
            merchant.payment_terms = payment_terms
        if pricing_config is not None:
            merchant.pricing_config = pricing_config
        if credit_limit_cents is not None:
            merchant.credit_limit_cents = credit_limit_cents
        self._audit(db, ctx, "merchant.terms_updated", "merchant", merchant_id, {"payment_terms": payment_terms})
        db.commit()
        db.refresh(merchant)
        return merchant

    def _get_or_raise(self, db: Session, merchant_id: str) -> Merchant:
        merchant = self.get_merchant(db, merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")
        return merchant

    def _audit(
        self,
        db: Session,
        ctx: AdminContext,
        action: str,
        resource_type: str,
        resource_id: str,
        payload: dict,
    ) -> None:
        db.add(
            AdminAuditLog(
                actor_user_id=ctx.user.id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                payload=payload,
            )
        )
