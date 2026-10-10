"""Fixtures for merchant_p0 pack (avoid depending on tests/services/conftest)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser


@pytest.fixture
def merchant_ctx(db: Session) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"P0 Merchant {suffix}",
        email=f"p0-merchant-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        payment_terms="NET_30",
        profile={},
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_p0_{suffix}",
        email=f"p0-user-{suffix}@test.local",
        role=MerchantRole.OPS.value,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OPS)


@pytest.fixture
def dispatch_order(db: Session, merchant_ctx: MerchantContext) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DISPATCH_READY.value,
        merchant_id=merchant_ctx.merchant.id,
        amount_cents=3200,
        currency="cad",
        pickup={"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817},
        dropoff={"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order
