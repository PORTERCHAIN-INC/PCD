"""Nightly E2E: cycle invoices (lines carry the order) are found and cleaned up."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from porterchain_api.admin_engine.e2e_validation_catalog import E2E_MARKER
from porterchain_api.admin_engine.e2e_validation_service import E2EValidationService
from porterchain_api.billing_engine.models import InvoiceLine
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_models import Invoice, Order
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_models import Merchant


def _order(db, merchant_id: str, *, e2e: bool) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.INVOICED.value,
        merchant_id=merchant_id,
        amount_cents=10678,
        currency="cad",
        order_source=OrderSource.SHOPIFY.value,
        payment_terms="NET_30",
        pickup={"formatted": "A"},
        dropoff={"formatted": "B"},
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        internal_reference=E2E_MARKER if e2e else f"real-{uuid4().hex[:6]}",
    )
    db.add(order)
    db.flush()
    return order


def _cycle_invoice(db, merchant_id: str, orders: list[Order]) -> Invoice:
    inv = Invoice(
        invoice_number=f"E2E-{uuid4().hex[:10]}",
        order_id=None,
        merchant_id=merchant_id,
        amount_cents=10678 * len(orders),
        tax_cents=1228 * len(orders),
        fees_cents=0,
        currency="cad",
        billing_kind="cycle",
    )
    db.add(inv)
    db.flush()
    for o in orders:
        db.add(InvoiceLine(invoice_id=inv.id, order_id=o.id, description=f"Delivery {o.order_number}",
                           amount_cents=9450, tax_cents=1228, tax_province="ON"))
    db.flush()
    return inv


def test_cleanup_removes_e2e_cycle_invoice_and_keeps_real_one(db):
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"E2E cleanup {suffix}",
        email=f"e2e-cleanup-{suffix}@t.local",
        status=MerchantStatus.ACTIVE.value,
        payment_terms="NET_30",
        billing_cycle="MONTHLY",
    )
    db.add(merchant)
    db.flush()
    test_order = _order(db, merchant.id, e2e=True)
    real_order = _order(db, merchant.id, e2e=False)
    test_inv = _cycle_invoice(db, merchant.id, [test_order])
    real_inv = _cycle_invoice(db, merchant.id, [real_order])
    test_inv_id, real_inv_id, real_order_id = test_inv.id, real_inv.id, real_order.id
    db.commit()

    try:
        # Previously raised invoice_lines_order_id_fkey: the line still pointed at the order.
        removed = E2EValidationService()._cleanup_e2e_data(db)
        assert removed >= 1
        db.expire_all()
        assert db.query(Order).filter(Order.internal_reference == E2E_MARKER).count() == 0
        assert db.get(Invoice, test_inv_id) is None
        assert db.query(InvoiceLine).filter(InvoiceLine.invoice_id == test_inv_id).count() == 0
        # A cycle invoice with a real order is never touched.
        assert db.get(Invoice, real_inv_id) is not None
        assert db.query(InvoiceLine).filter(InvoiceLine.invoice_id == real_inv_id).count() == 1
        assert db.get(Order, real_order_id) is not None
    finally:
        db.rollback()
        db.query(InvoiceLine).filter(InvoiceLine.invoice_id.in_([test_inv_id, real_inv_id])).delete(
            synchronize_session=False
        )
        db.query(Invoice).filter(Invoice.id.in_([test_inv_id, real_inv_id])).delete(synchronize_session=False)
        db.query(Order).filter(Order.merchant_id == merchant.id).delete(synchronize_session=False)
        db.query(Merchant).filter(Merchant.id == merchant.id).delete(synchronize_session=False)
        db.commit()
