"""Cycle (Interac) invoice detail: pre-tax lines + HST reconcile with the gross invoice."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from porterchain_api.billing_engine.models import InvoiceLine
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_models import Invoice, Order
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.commerce_metrics import check_invoice_detail_consistency
from porterchain_api.merchant_models import Merchant


def test_cycle_invoice_detail_lines_total_is_gross(db):
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Cycle detail {suffix}",
        email=f"cycle-detail-{suffix}@t.local",
        status=MerchantStatus.ACTIVE.value,
        payment_terms="NET_7",
        billing_cycle="WEEKLY",
    )
    db.add(merchant)
    db.flush()
    orders = []
    for _ in range(2):
        o = Order(
            order_number=generate_order_number(),
            tracking_number=generate_tracking_number(),
            state=OrderState.INVOICED.value,
            merchant_id=merchant.id,
            amount_cents=10678,
            currency="cad",
            order_source=OrderSource.SHOPIFY.value,
            payment_terms="NET_7",
            pickup={"formatted": "A"},
            dropoff={"formatted": "B"},
            scheduled_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            compliance_metadata={"shopify": {"rate_quote_cents": 10678}, "quote": {"tax_cents": 1228}},
        )
        db.add(o)
        orders.append(o)
    db.flush()
    inv = Invoice(
        invoice_number=f"T-{uuid4().hex[:10]}",
        order_id=None,
        merchant_id=merchant.id,
        amount_cents=2 * 10678 + 3390,  # 2 deliveries + one $30 waiting fee (+ $3.90 HST)
        tax_cents=2 * 1228 + 390,
        fees_cents=0,
        currency="cad",
        billing_kind="cycle",
    )
    db.add(inv)
    db.flush()
    for o in orders:
        db.add(InvoiceLine(invoice_id=inv.id, order_id=o.id, description=f"Delivery {o.order_number}",
                           amount_cents=9450, tax_cents=1228, tax_province="ON"))
    db.add(InvoiceLine(invoice_id=inv.id, order_id=orders[0].id, description="Waiting time test",
                       amount_cents=3000, tax_cents=390, tax_province="ON"))
    db.flush()

    ctx = SimpleNamespace(merchant=merchant, user=None)
    detail = MerchantBillingService().invoice_detail(db, ctx, inv.id)

    assert detail["amount_cents"] == 2 * 10678 + 3390
    assert detail["lines_total_cents"] == detail["amount_cents"]
    assert check_invoice_detail_consistency(detail) == []
    assert detail["ar_consistency"] == {"ok": True, "reasons": []}


def test_per_order_line_mismatch_still_flagged():
    detail = {"amount_cents": 5000, "lines_total_cents": 4000,
              "lines": [{"amount_cents": 4000, "tax_cents": 0}]}
    assert "line_vs_invoice" in check_invoice_detail_consistency(detail)
