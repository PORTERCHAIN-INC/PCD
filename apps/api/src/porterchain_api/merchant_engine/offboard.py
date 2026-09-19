"""Merchant-owned close/erasure guards — live order count and AR."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.order_engine.buckets import IN_FLIGHT, WAITING_DISPATCH

# Live dispatch + waiting for a truck. History (delivered / invoiced / cancelled) may remain.
BLOCKING_ORDER_STATES = IN_FLIGHT + WAITING_DISPATCH + ("DRIVER_REJECTED",)


def billing_context(merchant: Merchant) -> MerchantContext:
    """Synthetic seat so billing totals can run without a live portal user."""
    dummy = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id="lifecycle",
        email=merchant.email or "ops@porterchain.invalid",
        role=MerchantRole.OWNER.value,
        is_active=False,
    )
    return MerchantContext(merchant=merchant, user=dummy, role=MerchantRole.OWNER)


def operational_order_count(db: Session, merchant_id: str) -> int:
    """Live in-flight orders only — sandbox test rows must not block close."""
    return int(
        db.query(func.count(Order.id))
        .filter(
            Order.merchant_id == merchant_id,
            Order.is_sandbox.is_(False),
            Order.state.in_(BLOCKING_ORDER_STATES),
        )
        .scalar()
        or 0
    )


def outstanding_cents(db: Session, merchant: Merchant) -> int:
    from porterchain_api.merchant_engine.billing_service import MerchantBillingService

    return MerchantBillingService().outstanding_balance(db, billing_context(merchant))
