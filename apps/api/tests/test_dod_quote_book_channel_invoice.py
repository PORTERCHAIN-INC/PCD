"""DoD: Quote≡Book≡channel≡invoice cents (unit-level, no live Shopify shop)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.commerce_metrics import (
    check_invoice_detail_consistency,
    reset_commerce_events_for_tests,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.reporting_metrics import channel_for_order_source, spend_by_channel
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.booking_models import Order


def _addr(**extra) -> dict:
    base = {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817, "postal_code": "M5V1E3"}
    base.update(extra)
    return base


def test_dod_quote_book_channel_invoice_cents(db):
    """Shopify channel order amount ≡ report channel spend ≡ invoice detail line + quote."""
    reset_commerce_events_for_tests()
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"DoD {suffix}",
        email=f"dod-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        pricing_model="fsa",
        payment_terms="NET_30",
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"u-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    ctx = MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)

    quote_cents = 6100
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DELIVERED.value,
        merchant_id=merchant.id,
        amount_cents=quote_cents,
        currency="cad",
        order_source=OrderSource.SHOPIFY.value,
        payment_terms="NET_30",
        pickup=_addr(),
        dropoff=_addr(postal_code="M5V 2T6"),
        compliance_metadata={
            "quote": {"final_cents": quote_cents, "amount_cents": quote_cents},
            "shopify": {"rate_quote_id": f"q-{suffix}", "rate_quote_cents": quote_cents},
        },
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db.add(order)
    db.commit()

    assert channel_for_order_source(order.order_source) == "shopify"
    channels = {r["channel"]: r for r in spend_by_channel(db, merchant.id)}
    assert channels["shopify"]["spend_cents"] == quote_cents
    assert channels["shopify"]["orders"] == 1

    inv = SimpleNamespace(
        id=f"inv-{suffix}",
        invoice_number=f"INV-{suffix}",
        merchant_id=merchant.id,
        order_id=order.id,
        customer_id=None,
        amount_cents=quote_cents,
        tax_cents=0,
        fees_cents=0,
        currency="cad",
        status="open",
        due_at=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        pdf_url=None,
        last_reminded_at=None,
    )
    db_mock = MagicMock()
    line_q = MagicMock()
    line_q.filter.return_value.order_by.return_value.all.return_value = []

    def query_side(*models):
        name = " ".join(getattr(m, "__name__", str(m)) for m in models)
        if "InvoiceLine" in name:
            return line_q
        m = MagicMock()
        m.outerjoin.return_value.filter.return_value.first.return_value = (inv, order)
        m.filter.return_value.first.return_value = order
        return m

    db_mock.query.side_effect = query_side
    svc = MerchantBillingService()
    with (
        patch.object(svc, "_payment_for_order", return_value=None),
        patch(
            "porterchain_api.merchant_engine.billing_service.invoice_status",
            return_value="sent",
        ),
        patch(
            "porterchain_api.merchant_engine.billing_service.outstanding_cents",
            return_value=quote_cents,
        ),
        patch(
            "porterchain_api.merchant_engine.billing_service.effective_payment_terms",
            return_value="NET_30",
        ),
    ):
        detail = svc.invoice_detail(db_mock, ctx, inv.id)

    assert detail["amount_cents"] == quote_cents
    assert detail["lines"]
    line = detail["lines"][0]
    assert line["channel"] == "shopify"
    assert line["pricing_model"] == "fsa"
    assert line["amount_cents"] == quote_cents
    assert line["rate_quote_cents"] == quote_cents
    assert detail["ar_consistency"]["ok"] is True
    assert check_invoice_detail_consistency(detail) == []


def test_ar_mismatch_metric_on_quote_line_drift():
    reset_commerce_events_for_tests()
    detail = {
        "amount_cents": 6100,
        "lines_total_cents": 6100,
        "lines": [
            {
                "amount_cents": 6100,
                "rate_quote_cents": 5000,
                "channel": "shopify",
            }
        ],
    }
    reasons = check_invoice_detail_consistency(detail)
    assert "quote_vs_line" in reasons
    from porterchain_api.merchant_engine.commerce_metrics import prometheus_commerce_lines

    text = "\n".join(prometheus_commerce_lines())
    assert 'kind="ar_mismatch"' in text
    assert 'result="quote_vs_line"' in text
