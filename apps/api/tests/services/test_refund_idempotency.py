"""Admin refunds claim a ledger row before Stripe and reuse that key."""

from __future__ import annotations

from datetime import UTC, datetime

from porterchain_api.admin_engine.finance_service import AdminFinanceService
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_models import Invoice, Order, Payment
from porterchain_api.domain.states import OrderState


def test_repeat_refund_calls_stripe_once(db, merchant_ctx, admin_ctx, settings, monkeypatch):
    now = datetime.now(UTC)
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DELIVERED.value,
        merchant_id=merchant_ctx.merchant.id,
        amount_cents=5000,
        currency="cad",
        pickup={"lat": 43.65, "lng": -79.38},
        dropoff={"lat": 43.7, "lng": -79.4},
        scheduled_at=now,
        stripe_payment_intent_id="pi_test",
    )
    db.add(order)
    db.flush()
    invoice = Invoice(
        invoice_number=f"INV-{order.order_number[-6:]}",
        order_id=order.id,
        merchant_id=merchant_ctx.merchant.id,
        amount_cents=5000,
        status="paid",
    )
    db.add(invoice)
    db.flush()
    payment = Payment(
        order_id=order.id,
        invoice_id=invoice.id,
        amount_cents=5000,
        status="SUCCEEDED",
        stripe_payment_intent_id="pi_test",
    )
    db.add(payment)
    db.commit()

    calls: list[str | None] = []

    def _fake(_settings, _order, amount_cents, *, idempotency_key=None):
        calls.append(idempotency_key)
        return "re_test_1"

    monkeypatch.setattr("porterchain_api.services.stripe_service.create_refund", _fake)
    finance = AdminFinanceService()
    partial = finance.refund_invoice(db, admin_ctx, settings, invoice.id, amount_cents=1000)
    again = finance.refund_invoice(db, admin_ctx, settings, invoice.id, amount_cents=1000)
    assert partial["status"] == "PARTIAL"
    assert again["refund_id"] == "re_test_1"
    assert len(calls) == 1
    db.refresh(payment)
    assert payment.status == "SUCCEEDED"
    full = finance.refund_invoice(db, admin_ctx, settings, invoice.id)
    assert full["status"] == "REFUNDED"
    assert len(calls) == 2
    db.refresh(payment)
    assert payment.status == "REFUNDED"
    rows = db.query(BillingLedgerEntry).filter(BillingLedgerEntry.invoice_id == invoice.id).all()
    assert len(rows) == 2
    assert {row.status for row in rows} == {"recorded"}
