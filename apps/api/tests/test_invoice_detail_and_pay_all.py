"""Invoice detail SOT + pay-all outstanding."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.merchant_engine.billing_service import MerchantBillingService


def test_invoice_detail_includes_channel_and_quote():
    db = MagicMock()
    merchant = SimpleNamespace(id="m1", pricing_model="fsa", payment_terms="NET_30", email="a@b.c")
    ctx = SimpleNamespace(merchant=merchant, user=SimpleNamespace(id="u1"))
    order = SimpleNamespace(
        id="o1",
        merchant_id="m1",
        order_number="PC-1",
        tracking_number="TRK1",
        order_source="SHOPIFY",
        amount_cents=6100,
        payment_terms="NET_30",
        compliance_metadata={
            "quote": {"final_cents": 6100, "items": [{"code": "base", "amount_cents": 5500}]},
            "shopify": {"rate_quote_id": "q1", "rate_quote_cents": 6100},
        },
    )
    inv = SimpleNamespace(
        id="inv1",
        invoice_number="INV-1",
        merchant_id="m1",
        order_id="o1",
        customer_id=None,
        amount_cents=6100,
        tax_cents=0,
        fees_cents=0,
        currency="cad",
        status="open",
        due_at=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        pdf_url=None,
        last_reminded_at=None,
    )
    db.query.return_value.outerjoin.return_value.filter.return_value.first.return_value = (inv, order)
    # InvoiceLine query → empty
    line_q = MagicMock()
    line_q.filter.return_value.order_by.return_value.all.return_value = []

    def query_side(*models):
        name = " ".join(getattr(m, "__name__", str(m)) for m in models)
        if "InvoiceLine" in name:
            return line_q
        m = MagicMock()
        m.outerjoin.return_value.filter.return_value.first.return_value = (inv, order)
        m.filter.return_value.first.return_value = (inv, order)
        m.filter.return_value.order_by.return_value.all.return_value = []
        return m

    db.query.side_effect = query_side
    svc = MerchantBillingService()
    with (
        patch.object(svc, "_payment_for_order", return_value=None),
        patch(
            "porterchain_api.merchant_engine.billing_service.invoice_status",
            return_value="sent",
        ),
        patch(
            "porterchain_api.merchant_engine.billing_service.outstanding_cents",
            return_value=6100,
        ),
        patch(
            "porterchain_api.merchant_engine.billing_service.effective_payment_terms",
            return_value="NET_30",
        ),
    ):
        detail = svc.invoice_detail(db, ctx, "inv1")

    assert detail["payable"] is True
    assert detail["pay_url"]
    assert detail["lines"][0]["channel"] == "shopify"
    assert detail["lines"][0]["pricing_model"] == "fsa"
    assert detail["lines"][0]["rate_quote_id"] == "q1"
    assert detail["lines"][0]["quote_breakdown"]["final_cents"] == 6100


def test_pay_outstanding_mock():
    db = MagicMock()
    settings = SimpleNamespace(
        allow_stripe_mock=True, stripe_secret="", merchant_portal_url="http://localhost:3001"
    )
    merchant = SimpleNamespace(id="m1", email="a@b.c", payment_terms="NET_30")
    ctx = SimpleNamespace(merchant=merchant, user=SimpleNamespace(id="u1"))
    svc = MerchantBillingService()
    with (
        patch.object(
            svc,
            "list_invoices_enriched",
            return_value=[
                {
                    "invoice_id": "inv1",
                    "outstanding_cents": 1000,
                    "status": "sent",
                    "currency": "cad",
                },
                {
                    "invoice_id": "inv2",
                    "outstanding_cents": 2500,
                    "status": "overdue",
                    "currency": "cad",
                },
            ],
        ),
        patch.object(svc, "_settle_invoice_batch") as settle,
    ):
        out = svc.start_pay_outstanding(db, settings, ctx)
    assert out["paid"] is True
    assert out["amount_cents"] == 3500
    assert out["invoice_ids"] == ["inv1", "inv2"]
    settle.assert_called_once()


def test_pay_outstanding_nothing_due():
    db = MagicMock()
    settings = SimpleNamespace(allow_stripe_mock=True, stripe_secret="")
    ctx = SimpleNamespace(merchant=SimpleNamespace(id="m1"), user=SimpleNamespace(id="u1"))
    svc = MerchantBillingService()
    with patch.object(svc, "list_invoices_enriched", return_value=[]):
        with pytest.raises(ValueError, match="nothing_outstanding"):
            svc.start_pay_outstanding(db, settings, ctx)
