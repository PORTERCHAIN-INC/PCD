"""Merchant cycle AR — preview, generate, record payment."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.merchant_ar_service import MerchantArService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser
from porterchain_api.billing_engine.merchant_service import invoice_status
from porterchain_api.booking_models import Invoice, Order, Payment
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext, MerchantRole
from porterchain_api.merchant_models import Merchant, MerchantUser

pytestmark = pytest.mark.usefixtures("db")


def _admin(db: Session) -> AdminContext:
    admin = db.query(AdminUser).filter(AdminUser.is_active.is_(True)).first()
    if not admin:
        pytest.skip("no admin user")
    return AdminContext(user=admin, role=AdminRole(admin.role))


def _merchant(db: Session) -> tuple[MerchantContext, Merchant]:
    row = (
        db.query(MerchantUser, Merchant)
        .join(Merchant, Merchant.id == MerchantUser.merchant_id)
        .filter(MerchantUser.is_active.is_(True), Merchant.status == MerchantStatus.ACTIVE.value)
        .first()
    )
    if not row:
        pytest.skip("no active merchant")
    user, merchant = row
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER), merchant


def _seed_delivered_order(db: Session, merchant: Merchant) -> Order:
    from porterchain_api.booking_engine.numbers import (
        generate_order_number,
        generate_tracking_number,
    )

    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.POD_COMPLETED.value,
        merchant_id=merchant.id,
        customer_id=None,
        order_source="merchant",
        order_type="instant",
        payment_terms=merchant.payment_terms or "NET_30",
        amount_cents=2500,
        currency="cad",
        pickup={"formatted": "A", "lat": 43.6, "lng": -79.3},
        dropoff={"formatted": "B", "lat": 43.7, "lng": -79.4},
        scheduled_at=datetime.now(UTC),
        internal_reference="test-ar-order",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def test_merchant_ar_generate_and_pay(db: Session):
    """One cycle invoice per merchant per period; orders become lines."""
    from porterchain_api.billing_engine.models import InvoiceLine

    actx = _admin(db)
    _mctx, merchant = _merchant(db)
    order = _seed_delivered_order(db, merchant)
    order2 = _seed_delivered_order(db, merchant)
    ar = MerchantArService()
    start = datetime.now(UTC) - timedelta(days=1)
    end = datetime.now(UTC) + timedelta(days=1)

    preview = ar.preview(db, merchant_id=merchant.id, period_start=start, period_end=end)
    assert order.id in preview["order_ids"]

    gen = ar.generate(db, actx, merchant_id=merchant.id, period_start=start, period_end=end)
    assert gen["created_count"] == 1
    line = db.query(InvoiceLine).filter(InvoiceLine.order_id == order.id).one()
    line2 = db.query(InvoiceLine).filter(InvoiceLine.order_id == order2.id).one()
    assert line.invoice_id == line2.invoice_id
    inv = db.get(Invoice, line.invoice_id)
    assert inv.billing_kind == "cycle"
    assert inv.order_id is None
    assert inv.merchant_id == merchant.id
    assert inv.customer_id is None
    assert inv.due_at is not None
    assert inv.payment_reference and inv.payment_reference.startswith("PC-")
    assert db.query(Invoice).filter(Invoice.order_id == order.id).count() == 0

    gen2 = ar.generate(db, actx, merchant_id=merchant.id, period_start=start, period_end=end)
    assert gen2["created_count"] == 0

    total = int(inv.amount_cents)
    result = ar.record_payment(db, actx, inv.id, method="interac", reference="CA123")
    assert result["status"] == "paid"
    payment = db.query(Payment).filter(Payment.invoice_id == inv.id, Payment.status == "SUCCEEDED").one()
    assert payment.quote_id is None
    assert payment.payment_method == "interac"
    assert payment.amount_cents == total
    db.refresh(order)
    db.refresh(inv)
    assert order.state == OrderState.INVOICED.value
    assert invoice_status(inv, None, None, terms=merchant.payment_terms) == "paid"

    with pytest.raises(ValueError, match="already_paid"):
        ar.record_payment(db, actx, inv.id, method="wire")


def test_ach_is_no_longer_accepted(db: Session):
    actx = _admin(db)
    _mctx, merchant = _merchant(db)
    _seed_delivered_order(db, merchant)
    ar = MerchantArService()
    start = datetime.now(UTC) - timedelta(days=1)
    end = datetime.now(UTC) + timedelta(days=1)
    gen = ar.generate(db, actx, merchant_id=merchant.id, period_start=start, period_end=end)
    with pytest.raises(ValueError, match="invalid_payment_method"):
        ar.record_payment(db, actx, gen["invoices"][0]["invoice_id"], method="ach")
