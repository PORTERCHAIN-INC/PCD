"""Interac billing: gap-free numbers, partial/over payments, credit carry-forward,
inbox ingest → review queue → one-click approval with audit."""

from __future__ import annotations

import email
import uuid
from datetime import UTC, datetime, timedelta
from email import policy
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.merchant_ar_service import MerchantArService, is_cycle_billed
from porterchain_api.admin_models import AdminAuditLog
from porterchain_api.billing_engine.interac.service import approve_transfer, ingest_message, reject_transfer
from porterchain_api.billing_engine.invoice_numbering import allocate_invoice_number
from porterchain_api.billing_engine.merchant_credit import merchant_credit_cents
from porterchain_api.billing_engine.merchant_service import invoice_status, outstanding_cents
from porterchain_api.booking_models import Invoice, Payment
from tests.services.test_merchant_ar_service import _admin, _merchant, _seed_delivered_order

pytestmark = pytest.mark.usefixtures("db")
FIX = Path(__file__).resolve().parent.parent / "fixtures" / "interac"
AUTHSERV = "mx.zohomail.com"


def _eml(name: str, **subs: str):
    raw = (FIX / name).read_text(encoding="utf-8")
    base = {
        "MSGID": uuid.uuid4().hex,
        "SENDER": "SOMEONE UNKNOWN",
        "AMOUNT": "10.00",
        "AMOUNT_FR": "10,00",
        "MEMO": "",
        "IREF": "CA" + uuid.uuid4().hex[:10],
    }
    base.update(subs)
    for k, v in base.items():
        raw = raw.replace("{" + k + "}", v)
    return email.message_from_bytes(raw.encode("utf-8"), policy=policy.compat32)


def _cycle_invoice(db: Session, n_orders: int = 1) -> Invoice:
    actx = _admin(db)
    _m, merchant = _merchant(db)
    for _ in range(n_orders):
        _seed_delivered_order(db, merchant)
    out = MerchantArService().generate(
        db,
        actx,
        merchant_id=merchant.id,
        period_start=datetime.now(UTC) - timedelta(days=1),
        period_end=datetime.now(UTC) + timedelta(days=1),
    )
    return db.get(Invoice, out["invoices"][0]["invoice_id"])


def _money(cents: int) -> str:
    return f"{cents / 100:,.2f}"


def test_invoice_numbers_are_sequential_and_gap_free(db: Session):
    prefix = "T" + uuid.uuid4().hex[:5].upper()
    a = allocate_invoice_number(db, prefix=prefix)
    b = allocate_invoice_number(db, prefix=prefix)
    db.rollback()  # a rolled-back invoice gives its number back
    c = allocate_invoice_number(db, prefix=prefix)
    d = allocate_invoice_number(db, prefix=prefix)
    db.commit()
    year = datetime.now(UTC).year
    assert a == f"{prefix}-{year}-000001"
    assert b == f"{prefix}-{year}-000002"
    assert c == a and d == b


def test_partial_then_overpayment_becomes_credit_applied_next_cycle(db: Session):
    actx = _admin(db)
    inv = _cycle_invoice(db, n_orders=2)
    total = int(inv.amount_cents)
    ar = MerchantArService()
    credit_before = merchant_credit_cents(db, inv.merchant_id)

    r1 = ar.record_payment(db, actx, inv.id, method="interac", amount_cents=1000, reference="CA-PART")
    assert r1["status"] == "partial" and r1["balance_cents"] == total - 1000
    db.refresh(inv)
    st = invoice_status(inv, None, None)
    assert st in ("partial", "overdue")
    assert outstanding_cents(inv, st) == total - 1000

    r2 = ar.record_payment(db, actx, inv.id, method="interac", amount_cents=total - 1000 + 700)
    assert r2["status"] == "paid" and r2["excess_cents"] == 700
    assert merchant_credit_cents(db, inv.merchant_id) == credit_before + 700

    nxt = _cycle_invoice(db, n_orders=1)
    db.refresh(nxt)
    assert int(nxt.amount_paid_cents) == min(int(nxt.amount_cents), credit_before + 700)


def test_reference_match_is_proposed_then_approved_with_audit(db: Session):
    actx = _admin(db)
    inv = _cycle_invoice(db)
    total = int(inv.amount_cents)
    msg = _eml("autodeposit_en.eml", AMOUNT=_money(total), MEMO=f"{inv.payment_reference} Oct deliveries")
    row = ingest_message(db, msg, authserv_id=AUTHSERV)
    db.commit()
    assert row.status == "proposed"
    assert row.invoice_id == inv.id and row.match_method == "reference" and row.match_note == "exact"
    # Re-reading the same email is a no-op.
    assert ingest_message(db, msg, authserv_id=AUTHSERV) is None

    out = approve_transfer(db, actx, row.id)
    assert out["status"] == "approved"
    db.refresh(inv)
    assert invoice_status(inv, None, None) == "paid"
    pay = db.get(Payment, out["payment_id"])
    assert pay.payment_method == "interac" and pay.amount_cents == total
    assert (
        db.query(AdminAuditLog)
        .filter(AdminAuditLog.resource_id == row.id, AdminAuditLog.action == "finance.interac.approve")
        .count()
        == 1
    )
    with pytest.raises(ValueError, match="not_approvable"):
        approve_transfer(db, actx, row.id)


def test_partial_and_over_go_to_review_not_proposed(db: Session):
    inv = _cycle_invoice(db)
    total = int(inv.amount_cents)
    short = ingest_message(
        db, _eml("autodeposit_en.eml", AMOUNT=_money(total - 500), MEMO=inv.payment_reference), authserv_id=AUTHSERV
    )
    over = ingest_message(
        db, _eml("autodeposit_en.eml", AMOUNT=_money(total + 500), MEMO=inv.payment_reference), authserv_id=AUTHSERV
    )
    db.commit()
    assert short.status == "needs_review" and short.match_note == "partial"
    assert over.status == "needs_review" and over.match_note == "over"


def test_sender_and_amount_match_without_reference(db: Session):
    inv = _cycle_invoice(db)
    _m, merchant = _merchant(db)
    assert inv.merchant_id == merchant.id
    st = invoice_status(inv, None, None)
    owing = outstanding_cents(inv, st)
    row = ingest_message(
        db,
        _eml("notification_en.eml", SENDER=(merchant.company_name or "").upper() + " INC.", AMOUNT=_money(owing), MEMO="thanks"),
        authserv_id=AUTHSERV,
    )
    db.commit()
    assert row.merchant_id == merchant.id
    # Exact amount for one open invoice → proposed; several equal open amounts → review.
    if row.status == "proposed":
        assert row.match_method == "sender_amount"
    else:
        assert row.match_note in ("ambiguous", "merchant_only")


def test_spoofed_email_is_suspicious_and_cannot_be_approved(db: Session):
    actx = _admin(db)
    inv = _cycle_invoice(db)
    row = ingest_message(
        db,
        _eml("spoofed.eml", AMOUNT=_money(int(inv.amount_cents)), MEMO=inv.payment_reference),
        authserv_id=AUTHSERV,
    )
    db.commit()
    assert row.status == "suspicious" and not row.auth_ok
    assert row.invoice_id is None
    with pytest.raises(ValueError):
        approve_transfer(db, actx, row.id, invoice_id=inv.id)
    out = reject_transfer(db, actx, row.id, note="phishing")
    assert out["status"] == "rejected"


def test_unmatched_goes_to_review_and_admin_picks_invoice(db: Session):
    actx = _admin(db)
    inv = _cycle_invoice(db)
    row = ingest_message(
        db, _eml("autodeposit_fr.eml", SENDER="PERSONNE INCONNUE", AMOUNT_FR="12,34"), authserv_id=AUTHSERV
    )
    db.commit()
    assert row.status == "needs_review" and row.invoice_id is None
    with pytest.raises(ValueError, match="invoice_required"):
        approve_transfer(db, actx, row.id)
    out = approve_transfer(db, actx, row.id, invoice_id=inv.id, note="matched by phone")
    assert out["match_method"] == "manual"
    db.refresh(inv)
    assert int(inv.amount_paid_cents) == 1234


def test_duplicate_interac_reference_is_flagged(db: Session):
    iref = "CA" + uuid.uuid4().hex[:10]
    first = ingest_message(db, _eml("notification_en.eml", IREF=iref), authserv_id=AUTHSERV)
    second = ingest_message(db, _eml("autodeposit_en.eml", IREF=iref), authserv_id=AUTHSERV)
    db.commit()
    assert first.status != "duplicate"
    assert second.status == "duplicate"


def test_imap_reader_is_read_only_and_flag_gated(db: Session):
    from types import SimpleNamespace

    from porterchain_api.billing_engine.interac.imap_reader import fetch_and_ingest

    off = SimpleNamespace(interac_imap_enabled=False, interac_imap_host="h", interac_imap_user="u", interac_imap_password="p")
    assert fetch_and_ingest(db, off)["enabled"] is False

    raw = _eml("autodeposit_en.eml").as_bytes()
    calls: list[tuple] = []

    class FakeImap:
        def login(self, *a):
            calls.append(("login",))

        def select(self, folder, readonly=False):
            calls.append(("select", folder, readonly))
            return "OK", [b"1"]

        def search(self, *a):
            return "OK", [b"1"]

        def fetch(self, num, spec):
            calls.append(("fetch", spec))
            return "OK", [(b"1 (BODY[] {n})", raw)]

        def store(self, *a):  # pragma: no cover - must never be called
            raise AssertionError("mailbox must not be modified")

        def logout(self):
            calls.append(("logout",))

    on = SimpleNamespace(
        interac_imap_enabled=True,
        interac_imap_host="imappro.zoho.com",
        interac_imap_port=993,
        interac_imap_user="billing@porterchain.com",
        interac_imap_password="app-password",
        interac_imap_folder="INBOX",
        interac_imap_lookback_days=7,
        interac_authserv_id=AUTHSERV,
    )
    out = fetch_and_ingest(db, on, client_factory=FakeImap)
    assert out == {"enabled": True, "fetched": 1, "queued": 1}
    assert ("select", "INBOX", True) in calls
    assert ("fetch", "(BODY.PEEK[])") in calls


def test_cycle_billed_orders_skip_per_order_invoice(db: Session):
    _m, merchant = _merchant(db)
    order = _seed_delivered_order(db, merchant)
    expected = (merchant.billing_cycle or "").upper() in ("WEEKLY", "BIWEEKLY", "MONTHLY") and (
        order.payment_terms or ""
    ).upper() not in ("", "IMMEDIATE", "PREPAID")
    assert is_cycle_billed(db, order) is expected


def test_invoice_pdf_has_gst_number_and_etransfer_instructions(db: Session):
    from porterchain_api.reporting.order_documents import pdf_bytes_for_invoice_id

    inv = _cycle_invoice(db)
    pdf, name = pdf_bytes_for_invoice_id(db, inv.id)
    text = pdf.decode("latin-1")
    assert "GST/HST Reg. No.:" in text
    assert inv.payment_reference in text
    assert "Interac e-Transfer" in text
    assert name.endswith(".pdf")


def test_merchant_portal_lists_cycle_invoice_with_interac_remittance(db: Session):
    from porterchain_api.merchant_engine.billing_service import MerchantBillingService
    from tests.services.test_merchant_ar_service import _merchant as _mm

    inv = _cycle_invoice(db)
    mctx, _merchant_row = _mm(db)
    svc = MerchantBillingService()
    rows = svc.list_invoices_enriched(db, mctx)
    mine = [r for r in rows if r["invoice_id"] == inv.id]
    assert mine and mine[0]["payment_reference"] == inv.payment_reference
    assert mine[0]["billing_kind"] == "cycle"
    detail = svc.invoice_detail(db, mctx, inv.id)
    assert detail["remittance_memo"] == inv.payment_reference
    assert len(detail["lines"]) >= 1


def test_lost_counter_resumes_after_highest_issued_number(db: Session):
    from porterchain_api.billing_engine.models import InvoiceNumberSequence

    prefix = "R" + uuid.uuid4().hex[:5].upper()
    year = datetime.now(UTC).year
    first = allocate_invoice_number(db, prefix=prefix)
    db.add(Invoice(invoice_number=first, amount_cents=100, currency="cad"))
    db.flush()
    db.query(InvoiceNumberSequence).filter(InvoiceNumberSequence.scope == f"{prefix}:{year}").delete()
    db.flush()
    assert allocate_invoice_number(db, prefix=prefix) == f"{prefix}-{year}-000002"
    db.rollback()


def test_cycle_invoice_never_borrows_an_unrelated_payment(db: Session):
    """order_id is NULL on cycle invoices; `Payment.order_id == None` must not match."""
    from porterchain_api.admin_engine.finance_service import AdminFinanceService
    from porterchain_api.billing_engine.merchant_credit import merchant_credit_cents

    _m, merchant = _merchant(db)
    # Ensure an unrelated NULL-order payment exists.
    db.add(Payment(order_id=None, status="SUCCEEDED", amount_cents=1, currency="cad", payment_method="interac"))
    db.commit()
    inv = _cycle_invoice(db)
    svc = AdminFinanceService()
    assert svc._payment_for_order(db, inv.order_id) is None
    detail = svc.get_invoice_detail(db, inv.id)
    if merchant_credit_cents(db, merchant.id) == 0 and int(inv.amount_paid_cents or 0) == 0:
        assert detail["status"] != "paid"
    assert detail["outstanding_cents"] == max(0, int(inv.amount_cents) - int(inv.amount_paid_cents or 0))
