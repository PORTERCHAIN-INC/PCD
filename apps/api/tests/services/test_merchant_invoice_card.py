"""Merchant pays an invoice by card (Stripe Checkout): idempotent completion, ownership, declines."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from porterchain_api.admin_engine.merchant_ar_service import MerchantArService
from porterchain_api.billing_engine import merchant_invoice_checkout as mic
from porterchain_api.booking_models import Invoice, Payment
from porterchain_api.billing_engine.models import InvoiceLine

from tests.services.test_merchant_ar_service import _seed_delivered_order

pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture
def mk(db, admin_ctx, merchant_ctx):
    def make():
        return _invoice(db, admin_ctx, merchant_ctx.merchant)
    return make


def _invoice(db, actx, merchant):
    order = _seed_delivered_order(db, merchant)
    start, end = datetime.now(UTC) - timedelta(days=1), datetime.now(UTC) + timedelta(days=1)
    MerchantArService().generate(db, actx, merchant_id=merchant.id, period_start=start, period_end=end)
    line = db.query(InvoiceLine).filter(InvoiceLine.order_id == order.id).one()
    return merchant, db.get(Invoice, line.invoice_id)


def _session(inv, merchant, status="paid", pi="pi_test_123"):
    return {"id": "cs_test_1", "payment_status": status, "payment_intent": pi,
            "amount_total": int(inv.amount_cents),
            "metadata": {"purpose": mic.PURPOSE, "invoice_id": inv.id, "merchant_id": merchant.id}}


def test_card_payment_marks_paid_once(db, mk):
    merchant, inv = mk()
    out = mic.complete_invoice_checkout(db, _session(inv, merchant))
    assert out["status"] == "paid" and out["method"] == "card"
    db.refresh(inv)
    assert inv.paid_at is not None
    pay = db.query(Payment).filter(Payment.transaction_id == "stripe:pi_test_123").one()
    assert pay.payment_method == "card" and pay.status == "SUCCEEDED"
    # Webhook + return-page sync both arrive: second is a no-op.
    assert mic.complete_invoice_checkout(db, _session(inv, merchant))["status"] == "already_paid"
    assert db.query(Payment).filter(Payment.transaction_id == "stripe:pi_test_123").count() == 1


def test_declined_or_unpaid_session_records_nothing(db, mk):
    merchant, inv = mk()
    assert mic.complete_invoice_checkout(db, _session(inv, merchant, status="unpaid"))["status"] == "unpaid"
    assert mic.complete_invoice_checkout(db, {"metadata": {"quote_id": "q"}})["status"] == "ignored"
    db.refresh(inv)
    assert inv.paid_at is None


def test_admin_cannot_record_card_offline(db, mk, admin_ctx):
    _merchant_row, inv = mk()
    with pytest.raises(ValueError, match="invalid_payment_method"):
        MerchantArService().record_payment(db, admin_ctx, inv.id, method="card")


def test_sync_rejects_other_merchants_session(db, mk, monkeypatch):
    merchant, inv = mk()
    settings = SimpleNamespace(stripe_secret="sk_test_x")
    other = _session(inv, merchant)
    other["metadata"]["merchant_id"] = "someone-else"
    monkeypatch.setattr("porterchain_api.services.stripe_service.retrieve_checkout_session", lambda s, sid: other)
    with pytest.raises(LookupError):
        mic.sync_invoice_checkout(db, settings, merchant, inv.id, "cs_test_1")
    with pytest.raises(LookupError):
        mic.sync_invoice_checkout(db, settings, SimpleNamespace(id="nope"), inv.id, "cs_test_1")


def test_checkout_needs_stripe_and_balance(db, mk):
    merchant, inv = mk()
    with pytest.raises(ValueError, match="card_payments_unavailable"):
        mic.create_invoice_checkout(db, SimpleNamespace(stripe_secret=""), merchant, inv.id, None)


def test_card_checkout_off_by_default_g11(db, mk):
    """G11/R9: merchants pay by Interac unless merchant_card_payments_enabled is turned on."""
    from porterchain_api.config import Settings

    assert Settings.model_fields["merchant_card_payments_enabled"].default is False
    merchant, inv = mk()
    with pytest.raises(ValueError, match="card_payments_unavailable"):
        mic.create_invoice_checkout(db, SimpleNamespace(stripe_secret="sk_test_x", merchant_card_payments_enabled=False),
                                    merchant, inv.id, None)


def test_payment_received_sends_bilingual_receipt_email() -> None:
    from porterchain_api.notification_engine.templates import TEMPLATES
    from tests.test_late_penalty import _specs_for_event

    specs = _specs_for_event("merchant.payment_received", {"merchant_id": "m1", "merchant_email": "ap@acme.test",
                                                           "invoice_number": "INV-1"})
    chans = {s.get("channel") for s in specs if s["template_key"] == "merchant_invoice_paid"}
    assert {"in_app", "email"} <= chans
    t = TEMPLATES["merchant_invoice_paid"]
    assert "Paiement reçu" in t["subject"] and "{amount_display}" in t["body"] and "Bonjour" in t["body"]


def test_webhook_event_is_plain_dict_for_handlers() -> None:
    import hashlib
    import hmac
    import json
    import time

    from porterchain_services.stripe.sdk import construct_webhook_event

    secret = "whsec_unit_test_only"
    body = json.dumps({"id": "evt_1", "object": "event", "type": "checkout.session.completed",
                       "data": {"object": {"id": "cs_1", "object": "checkout.session",
                                           "metadata": {"purpose": "merchant_invoice"}}}}).encode()
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    event = construct_webhook_event(body, f"t={ts},v1={sig}", secret)
    assert isinstance(event, dict)
    assert event.get("type") == "checkout.session.completed"
    assert event["data"]["object"].get("metadata", {}).get("purpose") == "merchant_invoice"
