"""IDOR regression tests — cross-tenant access denied (DD-07)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.customer_service import CustomerService
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.repositories.order_repository import OrderRepository
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.orders_service import MerchantOrdersService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.models import Customer, Order


def _addr() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


def _make_merchant_ctx(db: Session, suffix: str) -> MerchantContext:
    merchant = Merchant(
        company_name=f"IDOR Test {suffix}",
        email=f"merchant-{suffix}@idor.test",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"user-{suffix}@idor.test",
        role=MerchantRole.OPS.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OPS)


def _make_customer(db: Session, suffix: str) -> Customer:
    customer = Customer(
        clerk_user_id=f"customer_clerk_{suffix}",
        email=f"customer-{suffix}@idor.test",
    )
    db.add(customer)
    db.flush()
    return customer


def _make_order(
    db: Session,
    *,
    merchant_id: str | None = None,
    customer_id: str | None = None,
) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.BOOKED.value,
        merchant_id=merchant_id,
        customer_id=customer_id,
        amount_cents=2500,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def test_merchant_cannot_read_other_merchant_order(db: Session, settings) -> None:
    ctx_a = _make_merchant_ctx(db, uuid4().hex[:8])
    ctx_b = _make_merchant_ctx(db, uuid4().hex[:8])
    order_b = _make_order(db, merchant_id=ctx_b.merchant.id)
    db.commit()

    svc = MerchantOrdersService()
    assert svc.get_order(db, ctx_a, order_b.id) is None
    with pytest.raises(LookupError, match="order_not_found"):
        svc.get_detail_360(db, settings, ctx_a, order_b.id)


def test_merchant_tracking_scoped_by_merchant_id(db: Session) -> None:
    ctx_a = _make_merchant_ctx(db, uuid4().hex[:8])
    ctx_b = _make_merchant_ctx(db, uuid4().hex[:8])
    order_b = _make_order(db, merchant_id=ctx_b.merchant.id)
    db.commit()

    svc = MerchantOrdersService()
    assert svc.get_by_tracking(db, ctx_a, order_b.tracking_number) is None
    assert svc.get_by_tracking(db, ctx_b, order_b.tracking_number) is not None


def test_customer_cannot_rebook_other_customer_order(db: Session) -> None:
    customer_a = _make_customer(db, uuid4().hex[:8])
    customer_b = _make_customer(db, uuid4().hex[:8])
    order_b = _make_order(db, customer_id=customer_b.id)
    db.commit()

    with pytest.raises(LookupError, match="order_not_found"):
        CustomerService().rebook_payload(db, customer_a.id, order_b.id)


def test_order_repository_cross_tenant_returns_none(db: Session) -> None:
    ctx_a = _make_merchant_ctx(db, uuid4().hex[:8])
    ctx_b = _make_merchant_ctx(db, uuid4().hex[:8])
    order_b = _make_order(db, merchant_id=ctx_b.merchant.id)
    db.commit()

    repo = OrderRepository()
    assert repo.get_for_merchant(db, ctx_a.merchant.id, order_b.id) is None
    assert repo.get_by_tracking_for_merchant(db, ctx_a.merchant.id, order_b.tracking_number) is None
    assert repo.get_for_merchant(db, ctx_b.merchant.id, order_b.id) is not None


def test_order_repository_require_raises_on_cross_tenant(db: Session) -> None:
    customer_a = _make_customer(db, uuid4().hex[:8])
    customer_b = _make_customer(db, uuid4().hex[:8])
    order_b = _make_order(db, customer_id=customer_b.id)
    db.commit()

    repo = OrderRepository()
    with pytest.raises(LookupError, match="order_not_found"):
        repo.require_for_customer(db, customer_a.id, order_b.id)
