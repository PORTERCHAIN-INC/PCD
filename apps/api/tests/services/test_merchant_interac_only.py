"""Ravi 2026-11-03: merchant invoices are paid by Interac e-Transfer only (no Stripe card).
Admin records the Interac payment (amount, date, reference) -> merchant_interac_payment ledger row."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.merchant_ar_service import MerchantArService, interac_instructions
from porterchain_api.admin_engine.platform_settings import etransfer_recipient_email
from porterchain_api.billing_engine import merchant_invoice_checkout as mic
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.notification_engine.templates import render_email
from tests.services.test_merchant_invoice_card import _invoice

pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture
def mkinv(db, admin_ctx, merchant_ctx):
    return lambda: _invoice(db, admin_ctx, merchant_ctx.merchant)[1]


def _kinds(db: Session, invoice_id: str) -> list[str]:
    return [e.kind for e in db.query(BillingLedgerEntry).filter(BillingLedgerEntry.invoice_id == invoice_id)]


def test_card_off_for_merchants_even_with_flag_and_test_key(db: Session, mkinv, admin_ctx):
    on = SimpleNamespace(stripe_secret="sk_test_x", merchant_card_payments_enabled=True)
    assert mic.card_payments_available(on) is False
    inv = mkinv()
    with pytest.raises(ValueError, match="card_payments_unavailable"):
        mic.create_invoice_checkout(db, on, SimpleNamespace(id=inv.merchant_id), inv.id, None)


def test_interac_instructions_carry_email_and_reference(db: Session, mkinv, admin_ctx):
    inv = mkinv()
    line = interac_instructions(db, inv)
    assert etransfer_recipient_email(db) in line
    assert (inv.payment_reference or inv.invoice_number) in line and inv.invoice_number in line


def test_merchant_invoice_emails_say_interac_not_pay_now():
    ctx = {"invoice_number": "INV-1", "merchant_name": "M", "amount_display": "$1.00 CAD",
           "pay_url": "http://portal/billing/invoices/x", "receipt_url": "http://r",
           "interac_line": "Pay by Interac e-Transfer to pay@example.com. Put PC-1 (invoice INV-1) in the message."}
    for tpl in ("merchant_invoice_ready", "merchant_invoice_reminder", "merchant_invoice_overdue"):
        _subject, text, html = render_email(tpl, ctx)
        assert "Interac e-Transfer to pay@example.com" in text, tpl
        assert "Interac e-Transfer to pay@example.com" in html, tpl
        assert "Pay now" not in text and "pay=card" not in text, tpl
        assert "Pay now" not in html, tpl


def test_admin_interac_payment_partial_then_over_writes_interac_ledger(db: Session, mkinv, admin_ctx):
    actx = admin_ctx
    inv = mkinv()
    total = int(inv.amount_cents)
    ar = MerchantArService()
    ref = inv.payment_reference or inv.invoice_number
    day = datetime(2026, 11, 2, 17, 0, tzinfo=UTC)
    r1 = ar.record_payment(db, actx, inv.id, method="interac", amount_cents=500, reference=ref, paid_at=day)
    assert r1["status"] == "partial" and r1["balance_cents"] == total - 500
    r2 = ar.record_payment(db, actx, inv.id, method="interac", amount_cents=total - 500 + 250, reference=ref)
    assert r2["status"] == "paid" and r2["excess_cents"] == 250
    kinds = _kinds(db, inv.id)
    assert kinds.count("merchant_interac_payment") == 2
    assert "merchant_card_payment" not in kinds


def test_cheque_still_offline_kind(db: Session, mkinv, admin_ctx):
    actx = admin_ctx
    inv = mkinv()
    MerchantArService().record_payment(db, actx, inv.id, method="cheque", reference="CHQ-1")
    assert "merchant_offline_payment" in _kinds(db, inv.id)
