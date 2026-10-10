"""Billing round 2: province tax, Stripe refunds/disputes/payouts, margin, HST report,
accounting CSV, Cash board + reminder drafts, driver payout runs, retention, statement."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

import porterchain_api.crm_models  # noqa: F401  (drivers.crm_lead_id FK target)
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.merchant_ar_service import MerchantArService
from porterchain_api.billing_engine.models import (
    BillingLedgerEntry,
    DriverPayoutRun,
    FinanceReminderDraft,
    InteracTransfer,
    InvoiceLine,
    StripePayout,
)
from porterchain_api.billing_engine.tax import split_amount
from porterchain_api.booking_models import Invoice, Order, Payment
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant
from tests.services.test_merchant_ar_service import _admin, _seed_delivered_order

pytestmark = pytest.mark.usefixtures("db")


def _fresh_merchant(db: Session) -> Merchant:
    m = Merchant(
        status=MerchantStatus.ACTIVE.value,
        company_name=f"R2 Co {uuid.uuid4().hex[:6]}",
        email=f"ap_{uuid.uuid4().hex[:8]}@r2.test",
        payment_terms="NET_30",
        billing_cycle="WEEKLY",
    )
    db.add(m)
    db.commit()
    return m


def _order(db: Session, m: Merchant, *, cents: int, postal: str = "M5V 2T6", quote_tax: int | None = None) -> Order:
    o = _seed_delivered_order(db, m)
    o.amount_cents = cents
    o.dropoff = {"formatted": f"1 Main St, {postal}", "postal_code": postal}
    if quote_tax is not None:
        o.compliance_metadata = {"quote": {"tax_cents": quote_tax}}
    db.commit()
    return o


def _cycle(db: Session, m: Merchant) -> Invoice:
    now = datetime.now(UTC)
    out = MerchantArService().generate(
        db, _admin(db), merchant_id=m.id, period_start=now - timedelta(days=7), period_end=now + timedelta(hours=1)
    )
    return db.get(Invoice, out["invoices"][0]["invoice_id"])


# --- 9. tax ---------------------------------------------------------------------------


def test_split_exclusive_inclusive_and_province():
    on = split_amount(10000, province="ON", mode="exclusive", collect_qst=False)
    assert (on.pretax_cents, on.tax_cents, on.gross_cents) == (10000, 1300, 11300)
    # Quote already added 13%: take it out, then add the right tax back.
    quoted = split_amount(11300, province="ON", mode="exclusive", collect_qst=False, quoted_tax=1300)
    assert (quoted.pretax_cents, quoted.tax_cents, quoted.gross_cents) == (10000, 1300, 11300)
    ab = split_amount(10000, province="AB", mode="exclusive", collect_qst=False)
    assert ab.tax_cents == 500 and ab.label == "GST 5%"
    qc = split_amount(10000, province="QC", mode="exclusive", collect_qst=True)
    assert qc.tax_cents == 1498
    inc = split_amount(11300, province="ON", mode="inclusive", collect_qst=False)
    assert (inc.pretax_cents, inc.tax_cents, inc.gross_cents) == (10000, 1300, 11300)


def test_cycle_invoice_is_tax_exclusive_by_destination(db: Session):
    m = _fresh_merchant(db)
    _order(db, m, cents=10000, postal="M5V 2T6")
    _order(db, m, cents=10000, postal="T2P 1J9")  # Calgary: GST only
    inv = _cycle(db, m)
    lines = db.query(InvoiceLine).filter(InvoiceLine.invoice_id == inv.id).all()
    assert sorted((ln.tax_province, ln.amount_cents, ln.tax_cents) for ln in lines) == [
        ("AB", 10000, 500),
        ("ON", 10000, 1300),
    ]
    assert inv.tax_cents == 1800 and inv.amount_cents == 21800
    assert inv.tax_province is None  # mixed provinces
    # Merchant tax summary reads the same numbers: subtotal + tax = total.
    from porterchain_api.billing_engine.merchant_service import build_tax_summary

    s = build_tax_summary([inv])
    assert (s["subtotal_cents"], s["tax_cents"], s["total_cents"]) == (20000, 1800, 21800)


def test_hst_report_and_accounting_csv(db: Session):
    from porterchain_api.reporting.tax_report import accounting_csv, hst_report, hst_report_csv

    m = _fresh_merchant(db)
    _order(db, m, cents=20000, postal="B3H 1A1")  # Halifax: 14% HST
    inv = _cycle(db, m)
    start, end = datetime.now(UTC) - timedelta(hours=1), datetime.now(UTC) + timedelta(hours=1)
    rep = hst_report(db, start, end)
    ns = next(p for p in rep["provinces"] if p["province"] == "NS")
    assert ns["rate_pct"] == 14.0 and ns["tax_cents"] >= 2800
    assert rep["gst34"]["line_103_tax_collected_cents"] >= 2800
    assert "GST34 line 101" in hst_report_csv(rep)
    qbo = accounting_csv(db, start, end, fmt="quickbooks")
    xero = accounting_csv(db, start, end, fmt="xero")
    assert qbo.splitlines()[0].startswith("InvoiceNo,Customer,InvoiceDate")
    assert xero.splitlines()[0].startswith("*ContactName,*InvoiceNumber")
    assert inv.invoice_number in qbo and "HST NS" in qbo
    assert inv.invoice_number in xero and "HST 14% (NS)" in xero


# --- 7. Stripe ------------------------------------------------------------------------


def _stripe_payment(db: Session, cents: int = 5000) -> Payment:
    m = _fresh_merchant(db)
    o = _order(db, m, cents=cents)
    pi = f"pi_{uuid.uuid4().hex[:14]}"
    o.stripe_payment_intent_id = pi
    p = Payment(order_id=o.id, status="SUCCEEDED", amount_cents=cents, currency="cad", stripe_payment_intent_id=pi)
    db.add(p)
    db.commit()
    return p


def _event(kind: str, obj: dict) -> dict:
    return {"id": f"evt_{uuid.uuid4().hex[:16]}", "type": kind, "data": {"object": obj}}


def test_dashboard_refund_webhook_is_recorded_once(db: Session):
    from porterchain_api.booking_engine.stripe_webhook_service import StripeWebhookService
    from porterchain_api.config import get_settings

    p = _stripe_payment(db)
    charge = {
        "id": "ch_1",
        "payment_intent": p.stripe_payment_intent_id,
        "amount": 5000,
        "amount_refunded": 5000,
        "refunds": {"data": [{"id": f"re_{uuid.uuid4().hex[:10]}", "amount": 5000, "status": "succeeded"}]},
    }
    svc = StripeWebhookService()
    assert svc.handle(db, get_settings(), _event("charge.refunded", charge))["status"] == "ok"
    svc.handle(db, get_settings(), _event("charge.refunded", charge))  # new event id, same refund
    db.refresh(p)
    rows = db.query(BillingLedgerEntry).filter(BillingLedgerEntry.payment_id == p.id, BillingLedgerEntry.kind == "refund").all()
    assert len(rows) == 1 and rows[0].amount_cents == 5000
    assert p.status == "REFUNDED"


def test_pcd_started_refund_is_not_double_counted(db: Session):
    from porterchain_api.billing_engine.stripe_money import apply_charge_refunds

    p = _stripe_payment(db)
    rid = f"re_{uuid.uuid4().hex[:10]}"
    db.add(BillingLedgerEntry(kind="refund", payment_id=p.id, amount_cents=2000, status="recorded",
                              metadata_json={"stripe_refund_id": rid}))
    db.commit()
    out = apply_charge_refunds(db, {"payment_intent": p.stripe_payment_intent_id, "amount": 5000,
                                    "amount_refunded": 2000, "refunds": {"data": [{"id": rid, "amount": 2000}]}})
    assert out["refunds_added"] == 0
    db.refresh(p)
    assert p.status == "SUCCEEDED"  # partial refund keeps the payment


def test_dispute_lifecycle(db: Session):
    from porterchain_api.billing_engine.stripe_money import apply_dispute

    p = _stripe_payment(db)
    d = {"id": f"dp_{uuid.uuid4().hex[:10]}", "payment_intent": p.stripe_payment_intent_id, "amount": 5000,
         "reason": "fraudulent", "status": "needs_response", "evidence_details": {"due_by": 1893456000}}
    apply_dispute(db, d)
    db.refresh(p)
    assert p.status == "DISPUTED"
    apply_dispute(db, {**d, "status": "lost"})
    db.refresh(p)
    assert p.status == "DISPUTE_LOST"
    rows = db.query(BillingLedgerEntry).filter(BillingLedgerEntry.idempotency_key == f"stripe_dispute:{d['id']}").all()
    assert len(rows) == 1 and rows[0].status == "lost"


def test_payout_reconciles_to_zero_and_books_fees(db: Session):
    from porterchain_api.billing_engine.stripe_money import handle_payout_event

    p = _stripe_payment(db, cents=10000)
    txns = [
        {"id": f"txn_{uuid.uuid4().hex[:12]}", "type": "charge", "amount": 10000, "fee": 320, "source": {"payment_intent": p.stripe_payment_intent_id}},
        {"id": "txn_r", "type": "refund", "amount": -2000, "fee": 0},
        {"id": "txn_p", "type": "payout", "amount": -7680, "fee": 0},
    ]
    payout = {"id": f"po_{uuid.uuid4().hex[:10]}", "status": "paid", "amount": 7680, "currency": "cad",
              "arrival_date": 1760000000}
    out = handle_payout_event(db, payout, fetch=lambda _pid: txns)
    db.commit()
    assert out["difference_cents"] == 0
    row = db.query(StripePayout).filter(StripePayout.stripe_payout_id == payout["id"]).one()
    assert (row.gross_cents, row.fee_cents, row.refund_cents, row.matched_count) == (10000, 320, 2000, 1)
    fee = db.query(BillingLedgerEntry).filter(BillingLedgerEntry.kind == "stripe_fee", BillingLedgerEntry.payment_id == p.id).one()
    assert fee.amount_cents == 320


# --- 8. margin ------------------------------------------------------------------------


def test_margin_uses_actual_driver_pay_and_flags_the_floor(db: Session):
    from porterchain_api.admin_models import Driver
    from porterchain_api.driver_engine.wallet_ledger import record_transaction
    from porterchain_api.reporting.margin import margin_report

    m = _fresh_merchant(db)
    driver = Driver(full_name="Margin Pat", email=f"m{uuid.uuid4().hex[:6]}@d.test", phone="4165550000")
    db.add(driver)
    db.flush()
    good = _order(db, m, cents=5000)
    bad = _order(db, m, cents=1000)
    for o in (good, bad):
        o.assigned_driver_id = driver.id
    record_transaction(db, driver_id=driver.id, tx_type="delivery", amount_cents=1500, balance_after_cents=1500,
                       reference_id=good.id)
    record_transaction(db, driver_id=driver.id, tx_type="delivery", amount_cents=1500, balance_after_cents=3000,
                       reference_id=bad.id)
    db.commit()
    rep = margin_report(db, days=2, merchant_id=m.id)
    stops = {s["order_id"]: s for s in rep["stops"]}
    assert stops[good.id]["cost_source"] == "actual" and stops[good.id]["driver_cost_cents"] == 1500
    assert stops[bad.id]["below_floor"] is True
    assert stops[good.id]["below_floor"] is False
    assert rep["routes"][0]["stops"] == 2 and rep["routes"][0]["cost_source"] == "actual"


# --- 6. Cash + reminder drafts ---------------------------------------------------------


def test_cash_board_and_reminder_drafts_never_send_until_approved(db: Session, monkeypatch):
    from porterchain_api.finance_ops.cash import cash_board
    from porterchain_api.finance_ops.reminders import decide, list_drafts, queue_drafts

    sent: list = []
    monkeypatch.setattr(
        "porterchain_api.notification_engine.event_router.handle_domain_event", lambda *a, **k: sent.append(a)
    )
    m = _fresh_merchant(db)
    _order(db, m, cents=8000)
    inv = _cycle(db, m)
    inv.due_at = datetime.now(UTC) - timedelta(days=40)
    db.commit()
    board = cash_board(db)
    row = next(r for r in board["merchants"] if r["merchant_id"] == m.id)
    assert row["oldest_days"] >= 40 and row["buckets"]["31–60 days"] == row["outstanding_cents"]
    assert board["credit_holds"]["available"] in (True, False)

    queue_drafts(db)
    drafts = [d for d in list_drafts(db) if d["merchant_id"] == m.id]
    assert len(drafts) == 1 and inv.invoice_number in drafts[0]["body"]
    assert sent == []  # queuing never sends
    queue_drafts(db)  # idempotent: still one draft
    assert len([d for d in list_drafts(db) if d["merchant_id"] == m.id]) == 1

    out = decide(db, _admin(db), [drafts[0]["id"]], approve=True)
    assert out["emails_sent"] == 1
    assert db.get(FinanceReminderDraft, drafts[0]["id"]).status == "sent"
    db.refresh(inv)
    assert inv.last_reminded_at is not None
    queue_drafts(db)  # reminded just now: no new draft
    assert not [d for d in list_drafts(db) if d["merchant_id"] == m.id]


# --- Driver Pay ------------------------------------------------------------------------


def test_payout_run_draft_approve_paid_and_bank_csv(db: Session):
    from porterchain_api.admin_models import Driver, DriverPayout
    from porterchain_api.driver_engine.wallet_ledger import record_transaction, wallet_balance_cents
    from porterchain_api.finance_ops.payout_runs import approve_run, bank_csv, create_run, mark_run_paid

    db.query(DriverPayoutRun).filter(DriverPayoutRun.status == "draft").update({"status": "discarded"})
    driver = Driver(full_name="Run Pat", email=f"r{uuid.uuid4().hex[:6]}@d.test", phone="4165550001")
    db.add(driver)
    db.flush()
    record_transaction(db, driver_id=driver.id, tx_type="delivery", amount_cents=10800, balance_after_cents=10800)
    db.commit()
    admin = _admin(db)
    now = datetime.now(UTC)
    run = create_run(db, admin, now - timedelta(hours=1), now + timedelta(hours=1))
    line = next(r for r in run.lines if r["driver_id"] == driver.id)
    assert line["amount_cents"] == 10800 and run.status == "draft"
    with pytest.raises(ValueError):
        bank_csv(db, run.id)  # approve first
    run = approve_run(db, admin, run.id)
    line = next(r for r in run.lines if r["driver_id"] == driver.id)
    assert line["payout_id"] and wallet_balance_cents(db, driver.id) == 0
    body, _name = bank_csv(db, run.id)
    assert "Run Pat" in body and "108.00" in body
    run = mark_run_paid(db, admin, run.id)
    assert run.status == "paid" and db.get(DriverPayout, line["payout_id"]).status == "paid"


# --- retention + statement -------------------------------------------------------------


def test_interac_retention_keeps_open_and_recent(db: Session):
    from porterchain_api.finance_ops.retention import purge_expired_interac

    old = datetime.now(UTC) - timedelta(days=365 * 8)
    rows = [
        InteracTransfer(message_id=f"<{uuid.uuid4()}@x>", amount_cents=100, status="approved", received_at=old),
        InteracTransfer(message_id=f"<{uuid.uuid4()}@x>", amount_cents=100, status="needs_review", received_at=old),
        InteracTransfer(message_id=f"<{uuid.uuid4()}@x>", amount_cents=100, status="approved",
                        received_at=datetime.now(UTC)),
    ]
    db.add_all(rows)
    db.commit()
    ids = [r.id for r in rows]
    out = purge_expired_interac(db)
    assert out["deleted"] >= 1 and out["years"] == 7
    left = {r.id for r in db.query(InteracTransfer).filter(InteracTransfer.id.in_(ids)).all()}
    assert left == {ids[1], ids[2]}


def test_statement_pdf(db: Session):
    from porterchain_api.reporting.statement import statement_data, statement_pdf

    m = _fresh_merchant(db)
    _order(db, m, cents=4000)
    inv = _cycle(db, m)
    data = statement_data(db, m)
    assert data["balance_cents"] == inv.amount_cents
    assert data["open"][0]["reference"] == inv.payment_reference
    assert statement_pdf(data, tax_number="123456789 RT0001")[:4] == b"%PDF"


def test_remittance_schema_keeps_interac_fields():
    """Regression: the response model used to drop etransfer_email/open_references."""
    from porterchain_api.merchant_engine.billing_pack import remittance_pack
    from porterchain_api.schemas_merchant import BillingRemittance

    m = Merchant(company_name="X", email="ap@x.test")
    packed = remittance_pack(
        m, outstanding_cents=100, open_invoice_numbers=["INV-1"], net_terms_days=30, credits_applied_cents=0,
        open_references=["PC-ABCDE"], etransfer_email="billing@porterchain.com",
    )
    out = BillingRemittance(**packed).model_dump()
    assert out["etransfer_email"] == "billing@porterchain.com"
    assert out["open_references"] == ["PC-ABCDE"] and out["method"] == "interac"
