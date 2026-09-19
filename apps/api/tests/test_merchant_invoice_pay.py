"""Merchant invoice Pay now — server-locked amount + mock settle."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.merchant_engine.billing_service import MerchantBillingService


def test_start_invoice_pay_mock_settles():
    db = MagicMock()
    settings = SimpleNamespace(allow_stripe_mock=True, stripe_secret="", merchant_portal_url="http://localhost:3001")
    merchant = SimpleNamespace(id="m1", email="m@test.invalid", payment_terms="NET_30")
    ctx = SimpleNamespace(merchant=merchant, user=SimpleNamespace(id="u1"))
    inv = SimpleNamespace(
        id="inv1",
        invoice_number="INV-1",
        merchant_id="m1",
        order_id="o1",
        customer_id=None,
        amount_cents=5000,
        fees_cents=0,
        tax_cents=0,
        currency="cad",
        status="open",
        due_at=None,
        created_at=None,
    )
    order = SimpleNamespace(id="o1", merchant_id="m1", customer_id=None, payment_terms="NET_30")
    db.query.return_value.outerjoin.return_value.filter.return_value.first.return_value = (inv, order)

    svc = MerchantBillingService()
    with (
        patch.object(svc, "_payment_for_order", return_value=None),
        patch(
            "porterchain_api.merchant_engine.billing_service.invoice_status",
            return_value="sent",
        ),
        patch(
            "porterchain_api.merchant_engine.billing_service.outstanding_cents",
            return_value=5000,
        ),
        patch(
            "porterchain_api.merchant_engine.billing_service.effective_payment_terms",
            return_value="NET_30",
        ),
    ):
        out = svc.start_invoice_pay(db, settings, ctx, "inv1")

    assert out["paid"] is True
    assert out["mock"] is True
    assert out["amount_cents"] == 5000
    assert out["pay_url"] is None
    db.commit.assert_called()


def test_start_invoice_pay_wrong_merchant():
    db = MagicMock()
    settings = SimpleNamespace(allow_stripe_mock=True, stripe_secret="")
    ctx = SimpleNamespace(merchant=SimpleNamespace(id="m1"), user=SimpleNamespace(id="u1"))
    inv = SimpleNamespace(id="inv1", merchant_id="other", order_id=None)
    db.query.return_value.outerjoin.return_value.filter.return_value.first.return_value = (inv, None)
    with pytest.raises(LookupError, match="invoice_not_found"):
        MerchantBillingService().start_invoice_pay(db, settings, ctx, "inv1")
