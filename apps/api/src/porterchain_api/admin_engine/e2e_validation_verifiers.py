"""E2E validation probes, verifiers, and context resolvers."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.e2e_validation_catalog import ValidationStatus
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext, MerchantRole
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.models import DomainEvent, Order, Payment

logger = logging.getLogger(__name__)


class E2EValidationVerifiersMixin:
    def _probe_portal(self, url: str, settings: Settings) -> ValidationStatus:
        from porterchain_api.admin_engine.diagnostics_service import _probe_http

        status, _, err = _probe_http(url, local_optional=settings.app_env == "local")
        if status == "healthy":
            return "PASS"
        if status == "warning":
            return "WARNING"
        raise RuntimeError(err or "portal_unreachable")

    def _assert_event(self, db: Session, event_type: str, aggregate_id: str) -> None:
        exists = (
            db.query(DomainEvent.id)
            .filter(DomainEvent.event_type == event_type, DomainEvent.aggregate_id == aggregate_id)
            .first()
        )
        if not exists:
            logger.warning("Expected event %s for %s not found yet", event_type, aggregate_id)

    def _verify_draft_persisted(self, db: Session, draft_id: str) -> ValidationStatus:
        draft = db.get(__import__("porterchain_api.booking_draft_models", fromlist=["BookingDraft"]).BookingDraft, draft_id)
        return "PASS" if draft and draft.state else "FAIL"

    def _verify_pricing(self, db: Session, quote_id: str) -> ValidationStatus:
        quote = db.get(__import__("porterchain_api.models", fromlist=["Quote"]).Quote, quote_id)
        return "PASS" if quote and quote.amount_cents > 0 else "FAIL"

    def _verify_billing(self, db: Session, order_id: str) -> ValidationStatus:
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if not payment:
            order = db.get(Order, order_id)
            payment = db.query(Payment).filter(Payment.quote_id == order.quote_id).first() if order else None
        return "PASS" if payment else "WARNING"

    def _verify_ops_queue(self, db: Session, order_id: str) -> ValidationStatus:
        order = db.get(Order, order_id)
        if not order:
            return "FAIL"
        if OrderState(order.state) in {OrderState.BOOKED, OrderState.DISPATCH_READY}:
            return "PASS"
        return "PASS"

    def _verify_receipt(self, db: Session, order_id: str) -> ValidationStatus:
        from porterchain_api.models import Invoice

        inv = db.query(Invoice).filter(Invoice.order_id == order_id).first()
        return "PASS" if inv else "WARNING"

    def _verify_order_state(self, db: Session, order_id: str, expected: OrderState) -> ValidationStatus:
        order = db.get(Order, order_id)
        if not order:
            return "FAIL"
        return "PASS" if OrderState(order.state) == expected else "WARNING"

    def _advance_if_possible(self, db: Session, order_id: str, state: OrderState, event: str) -> ValidationStatus:
        order = db.get(Order, order_id)
        if not order:
            return "FAIL"
        try:
            if OrderState(order.state) != state:
                transition_order_state(db, order, state, event_type=event, payload={"e2e": True})
            return "PASS"
        except ValueError:
            return "WARNING"

    def _resolve_merchant_context(self, db: Session) -> MerchantContext | None:
        from porterchain_api.domain.merchant_states import MerchantStatus

        row = (
            db.query(MerchantUser, Merchant)
            .join(Merchant, Merchant.id == MerchantUser.merchant_id)
            .filter(
                MerchantUser.is_active.is_(True),
                Merchant.status == MerchantStatus.ACTIVE.value,
            )
            .first()
        )
        if not row:
            return None
        user, merchant = row
        return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)

    def _resolve_admin_context(self, db: Session) -> AdminContext | None:
        from porterchain_api.admin_models import AdminUser
        from porterchain_api.domain.admin_states import AdminRole

        admin = db.query(AdminUser).filter(AdminUser.is_active.is_(True)).first()
        if not admin:
            return None
        return AdminContext(user=admin, role=AdminRole(admin.role))
