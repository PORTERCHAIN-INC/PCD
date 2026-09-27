"""AK — Shopify on 360; ops invoice words on the timeline."""

from __future__ import annotations

from types import SimpleNamespace

from porterchain_api.domain.catalog_labels import order_source_label
from porterchain_api.order_engine.platform_helpers import ops_timeline_label, shopify_snapshot


def test_shopify_snapshot_from_metadata() -> None:
    order = SimpleNamespace(
        order_source="SHOPIFY",
        purchase_order_number="999",
        internal_reference="#1001",
        compliance_metadata={
            "shopify": {
                "shop_domain": "acme.myshopify.com",
                "order_id": 123,
                "order_name": "#1001",
            }
        },
    )
    snap = shopify_snapshot(order)
    assert snap == {
        "shop_domain": "acme.myshopify.com",
        "order_id": "123",
        "order_name": "#1001",
        "fulfillment_id": None,
        "last_tracking_push_at": None,
        "last_tracking_state": None,
        "last_fulfillment_error": None,
        "held_for_ops": False,
        "auto_dispatch": None,
        "last_repush_at": None,
        "last_event_status": None,
        "last_event_at": None,
        "order_admin_url": "https://acme.myshopify.com/admin/orders/123",
    }
    assert order_source_label("SHOPIFY") == "Shopify"


def test_shopify_snapshot_absent_for_portal_book() -> None:
    order = SimpleNamespace(
        order_source="MERCHANT",
        purchase_order_number="PO-1",
        internal_reference="WH-2",
        compliance_metadata={},
    )
    assert shopify_snapshot(order) is None
    assert order_source_label("MERCHANT") == "Merchant portal"


def test_ops_timeline_invoice_is_english_dollars() -> None:
    label = ops_timeline_label(
        event_type="order.invoiced",
        to_state="INVOICED",
        payload={"invoice_number": "INV-88", "amount_display": "$25.00 CAD", "amount_cents": 2500},
    )
    assert "INV-88" in label
    assert "$25.00" in label
    assert "2500" not in label
    assert "INVOICED" not in label
    assert "order.invoiced" not in label


def test_merchant360_timeline_uses_ops_invoices_not_crm(db) -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from porterchain_api.admin_engine.merchant360_service import Merchant360Service
    from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
    from porterchain_api.crm_models import CrmCompany, CrmInvoice
    from porterchain_api.domain.merchant_states import MerchantStatus
    from porterchain_api.domain.states import OrderState
    from porterchain_api.merchant_models import Merchant
    from porterchain_api.booking_models import Invoice, Order

    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"AK Co {suffix}",
        email=f"ak-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(merchant)
    db.flush()
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.INVOICED.value,
        merchant_id=merchant.id,
        amount_cents=2500,
        currency="cad",
        pickup={"formatted": "1 King"},
        dropoff={"formatted": "2 Bay"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    db.add(
        Invoice(
            invoice_number=f"INV-OPS-{suffix}",
            order_id=order.id,
            merchant_id=merchant.id,
            amount_cents=2500,
            currency="cad",
        )
    )
    company = CrmCompany(legal_name=f"AK CRM {suffix}", merchant_id=merchant.id)
    db.add(company)
    db.flush()
    db.add(
        CrmInvoice(
            invoice_number=f"INV-CRM-{suffix}",
            company_id=company.id,
            status="sent",
            amount_cents=99999,
            total_cents=99999,
        )
    )
    db.commit()

    events = Merchant360Service().timeline(db, merchant.id, company.id)
    titles = " ".join(e["title"] for e in events if e["kind"] == "invoice")
    assert f"INV-OPS-{suffix}" in titles
    assert "$25.00" in titles
    assert f"INV-CRM-{suffix}" not in titles
    assert "99999" not in titles
