"""Porterchain Inc. GST/HST 743402620 RT0001 (eff. 2026-09-28) prints on invoice PDFs and receipts (CRA)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from porterchain_api.admin_models import TaxRegistration
from porterchain_api.platform import tax_registration as reg

NUMBER = "743402620 RT0001"
NAME = "Porterchain Inc."


@pytest.fixture()
def registered(db):
    db.query(TaxRegistration).delete()
    db.commit()
    reg.clear_cache(db)
    reg.record_registration(db, gst_hst_number="743402620RT0001", legal_name=NAME,
                            effective_from=date(2026, 9, 28), actor_id=None)
    db.commit()
    yield db
    db.rollback()
    db.query(TaxRegistration).delete()
    db.commit()
    reg.clear_cache(db)


def test_registration_in_force_from_2026_09_28(registered) -> None:
    assert reg.collects_tax(registered, date(2026, 10, 1))
    assert not reg.collects_tax(registered, date(2026, 9, 27))
    assert reg.supplier_gst_hst_number(registered, date(2026, 10, 29)) == NUMBER


def test_invoice_pdf_prints_legal_name_and_number(registered) -> None:
    from porterchain_api.reporting.order_documents import invoice_compliance, render_branded_invoice_pdf

    inv = SimpleNamespace(issued_at=datetime(2026, 10, 29, 15, tzinfo=UTC), tax_cents=1294, tax_province="ON",
                          merchant_id=None, customer_id="c", billing_kind="order", amount_paid_cents=0,
                          billing_period_start=None, billing_period_end=None, payment_reference=None)
    comp = invoice_compliance(registered, inv)
    assert comp["supplier_tax_number"] == NUMBER and comp["supplier_legal_name"] == NAME
    pdf = render_branded_invoice_pdf(invoice_number="INV-T", amount_cents=11249, tax_cents=1294,
                                     receipt_number="RCPT-T", compliance=comp).decode("latin-1")
    assert NUMBER in pdf and NAME in pdf


def test_receipt_email_and_invoice_payload_carry_identity(registered) -> None:
    from porterchain_api.booking_engine.invoice_service import supplier_tax_identity
    from porterchain_api.notification_engine.templates import render_email

    ident = supplier_tax_identity(registered, SimpleNamespace(issued_at=datetime(2026, 10, 29, tzinfo=UTC)))
    assert ident == {"supplier_legal_name": NAME, "supplier_gst_hst_number": NUMBER}
    _, text, html = render_email("payment_receipt", {"order_number": "ORD-1", "amount_display": "$112.49 CAD",
                                                      "receipt_number": "RCPT-1", **ident})
    assert NUMBER in text and NAME in text
    assert NUMBER in (html or "") and NAME in (html or "")


def test_receipt_email_without_registration_has_no_number(db) -> None:
    from porterchain_api.notification_engine.templates import render_email

    _, text, html = render_email("payment_receipt", {"order_number": "ORD-1", "receipt_number": "RCPT-1"})
    assert "GST/HST" not in text and "GST/HST" not in (html or "")
