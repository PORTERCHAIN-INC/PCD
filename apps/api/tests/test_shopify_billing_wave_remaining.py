"""Shopify install hijack hardening + cycle invoice lines + commerce metrics."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest

from porterchain_api.admin_engine.merchant_ar_service import MerchantArService
from porterchain_api.billing_engine.models import InvoiceLine
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_engine.commerce_metrics import (
    note_commerce_event,
    prometheus_commerce_lines,
    reset_commerce_events_for_tests,
)
from porterchain_api.merchant_engine.shopify_service import _merchant_for_install
from porterchain_api.merchant_models import Merchant, ShopifyShop


def test_merchant_for_install_blocks_email_hijack_onto_bound_merchant(db):
    suffix = uuid4().hex[:8]
    owner = Merchant(
        company_name=f"Owner {suffix}",
        email=f"owner-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(owner)
    db.flush()
    db.add(
        ShopifyShop(
            merchant_id=owner.id,
            shop_domain=f"owner-{suffix}.myshopify.com",
            encrypted_access_token="enc",
            installed_at=datetime.now(UTC),
        )
    )
    db.commit()

    with pytest.raises(ValueError, match="shopify_email_already_bound"):
        _merchant_for_install(
            db,
            None,
            f"attacker-{suffix}.myshopify.com",
            {"email": owner.email, "name": "Attacker"},
        )


def test_merchant_for_install_state_merchant_blocks_other_live_shop(db):
    suffix = uuid4().hex[:8]
    a = Merchant(company_name=f"A {suffix}", email=f"a-{suffix}@t.local", status=MerchantStatus.ACTIVE.value)
    b = Merchant(company_name=f"B {suffix}", email=f"b-{suffix}@t.local", status=MerchantStatus.ACTIVE.value)
    db.add_all([a, b])
    db.flush()
    db.add(
        ShopifyShop(
            merchant_id=a.id,
            shop_domain=f"taken-{suffix}.myshopify.com",
            encrypted_access_token="enc",
            installed_at=datetime.now(UTC),
        )
    )
    db.commit()

    with pytest.raises(ValueError, match="shop_already_connected"):
        _merchant_for_install(db, b.id, f"taken-{suffix}.myshopify.com", {"email": b.email})


def test_cycle_generate_creates_invoice_line_with_channel(db):
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Cycle {suffix}",
        email=f"cycle-{suffix}@t.local",
        status=MerchantStatus.ACTIVE.value,
        payment_terms="NET_30",
        billing_cycle="MONTHLY",
        pricing_model="fsa",
    )
    db.add(merchant)
    db.flush()
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DELIVERED.value,
        merchant_id=merchant.id,
        amount_cents=4500,
        currency="cad",
        order_source=OrderSource.SHOPIFY.value,
        payment_terms="NET_30",
        pickup={"formatted": "A"},
        dropoff={"formatted": "B"},
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    user = SimpleNamespace(id=f"admin-{suffix}")
    ctx = SimpleNamespace(user=user)

    with (
        patch.object(
            MerchantArService,
            "_resolve_period",
            return_value=(datetime(2026, 1, 1), datetime(2026, 2, 1)),
        ),
        patch.object(MerchantArService, "_eligible_orders", return_value=[order]),
        patch(
            "porterchain_api.admin_engine.merchant_ar_service.transition_order_state",
            return_value=None,
        ),
        patch("porterchain_api.admin_engine.merchant_ar_service.emit_event"),
        patch("porterchain_api.admin_engine.merchant_ar_service.log_admin_audit"),
        patch(
            "porterchain_api.admin_engine.platform_settings.tax_cents_for_amount",
            return_value=0,
        ),
        patch(
            "porterchain_api.admin_engine.platform_settings.invoice_number_prefix",
            return_value="INV",
        ),
    ):
        result = MerchantArService().generate(db, ctx, merchant_id=merchant.id)

    created = result.get("invoices") or []
    assert created, result
    invoice_id = created[0]["invoice_id"]
    lines = db.query(InvoiceLine).filter(InvoiceLine.invoice_id == invoice_id).all()
    assert lines
    assert any("shopify/fsa" in (ln.description or "") for ln in lines), [ln.description for ln in lines]


def test_commerce_metrics_prometheus():
    reset_commerce_events_for_tests()
    note_commerce_event("shopify_quote", "ok")
    note_commerce_event("invoice_pay", "settled")
    text = "\n".join(prometheus_commerce_lines())
    assert "porterchain_commerce_events_total" in text
    assert 'kind="shopify_quote"' in text
    assert 'kind="invoice_pay"' in text
