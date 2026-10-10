"""AH — AP pack: glossary, remittance, invoice PDF, English errors."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.main import app
from porterchain_api.merchant_engine.billing_pack import (
    PAYEE_LEGAL_NAME,
    billing_error_message,
    remittance_pack,
)
from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.booking_models import Invoice, Order


def test_billing_copy() -> None:
    assert "invoice" in billing_error_message("invoice_not_found").lower()
    assert "pdf_not_available" not in billing_error_message("pdf_not_available")
    assert "Settings" in billing_error_message("billing_contact_missing")


def _ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"AP Co {suffix}",
        email=f"ap-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        credit_limit_cents=80_000,
        payment_terms="NET_14",
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"user-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def _order(db, merchant_id: str) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DELIVERED.value,
        merchant_id=merchant_id,
        amount_cents=4400,
        currency="cad",
        pickup={"formatted": "1 King"},
        dropoff={"formatted": "200 Bay"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def test_overview_pack_and_headroom(db) -> None:
    ctx = _ctx(db)
    db.commit()
    overview = MerchantBillingService().overview(db, ctx)
    assert overview["headroom_cents"] == overview["available_credit_cents"]
    assert overview["credits_applied_cents"] == overview["credit_notes_cents"]
    terms = {row["term"] for row in overview["glossary"]}
    assert "Headroom" in terms
    assert "Credits applied" in terms
    rem = overview["remittance"]
    assert rem["payee"] == PAYEE_LEGAL_NAME
    assert rem["net_terms_days"] == 14
    assert rem["advice_email"] == ctx.merchant.email


def test_remittance_lists_open_invoices() -> None:
    pack = remittance_pack(
        Merchant(company_name="X", email="ap@x.test"),
        outstanding_cents=1200,
        open_invoice_numbers=["INV-1", "INV-2"],
        net_terms_days=30,
        credits_applied_cents=200,
    )
    assert "INV-1" in pack["memo"]
    assert pack["credits_applied_cents"] == 200


def test_invoice_pdf_and_english_404(db, settings, monkeypatch) -> None:
    holder: dict = {}
    monkeypatch.setattr(
        "porterchain_api.routers.merchant.billing.require_module",
        lambda ctx, module: None,
    )
    app.dependency_overrides[get_merchant_context] = lambda: holder["ctx"]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        ctx = _ctx(db)
        order = _order(db, ctx.merchant.id)
        invoice = Invoice(
            invoice_number=f"INV-{uuid4().hex[:8].upper()}",
            order_id=order.id,
            merchant_id=ctx.merchant.id,
            amount_cents=4400,
            tax_cents=572,
            currency="cad",
        )
        db.add(invoice)
        db.commit()
        holder["ctx"] = ctx

        missing = client.get("/v1/merchant/billing/invoices/not-a-real-id/pdf")
        assert missing.status_code == 404
        assert "not found" in missing.json()["detail"].lower()

        pdf = client.get(f"/v1/merchant/billing/invoices/{invoice.id}/pdf")
        assert pdf.status_code == 200
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert pdf.content.startswith(b"%PDF")
        assert b"Shipping Label" not in pdf.content
    finally:
        app.dependency_overrides.clear()
