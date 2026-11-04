"""Late-payment penalty: 20% once per overdue business invoice + same-day suspension."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from porterchain_api.billing_engine import late_penalty as LP
from porterchain_api.billing_engine.invoice_extras import invoice_detail_extras
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_models import Invoice
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.notification_engine.event_router import _specs_for_event
from tests.test_collections_bl import _merchant

NOW = datetime.now(UTC)


def _invoice(db, merchant_id: str, *, due: datetime, amount: int = 10_000, paid: int = 0) -> Invoice:
    inv = Invoice(
        invoice_number=f"INV-T-{uuid4().hex[:10]}",
        merchant_id=merchant_id,
        status="sent",
        amount_cents=amount,
        tax_cents=0,
        fees_cents=0,
        due_at=due,
        amount_paid_cents=paid,
        billing_kind="cycle",
    )
    db.add(inv)
    db.flush()
    return inv


def _ours(db, inv_ids):
    return db.query(BillingLedgerEntry).filter(
        BillingLedgerEntry.kind == "late_penalty", BillingLedgerEntry.invoice_id.in_(inv_ids)
    ).all()


def test_overdue_invoice_gets_20pct_once_and_business_suspended(db) -> None:
    m = _merchant(db)
    inv = _invoice(db, m.id, due=NOW - timedelta(hours=2))
    LP.apply_due_penalties(db, now=NOW, pct=20)
    db.refresh(inv)
    db.refresh(m)
    assert inv.fees_cents == 2_000
    assert m.status == MerchantStatus.SUSPENDED.value
    assert len(_ours(db, [inv.id])) == 1
    # Idempotent: a second (and third) run adds nothing.
    LP.apply_due_penalties(db, now=NOW + timedelta(hours=1), pct=20)
    LP.apply_due_penalties(db, now=NOW + timedelta(days=3), pct=20)
    db.refresh(inv)
    assert inv.fees_cents == 2_000
    assert len(_ours(db, [inv.id])) == 1


def test_not_yet_due_or_paid_is_untouched(db) -> None:
    m = _merchant(db)
    future = _invoice(db, m.id, due=NOW + timedelta(days=1))
    paid = _invoice(db, m.id, due=NOW - timedelta(days=1), paid=10_000)
    LP.apply_due_penalties(db, now=NOW, pct=20)
    assert not _ours(db, [future.id, paid.id])
    db.refresh(m)
    assert m.status == MerchantStatus.ACTIVE.value


def test_penalty_line_shown_and_outstanding_includes_it(db) -> None:
    from porterchain_api.billing_engine.merchant_service import outstanding_cents

    m = _merchant(db)
    inv = _invoice(db, m.id, due=NOW - timedelta(days=1))
    LP.apply_due_penalties(db, now=NOW, pct=20)
    db.refresh(inv)
    f = LP.penalty_fields(db, inv)
    assert f == {"penalty_cents": 2_000, "penalty_label": "Late payment penalty (20%)"}
    lines = invoice_detail_extras(db, inv)["lines"]
    assert any(ln["description"] == "Late payment penalty (20%)" and ln["amount_cents"] == 2_000 for ln in lines)
    assert outstanding_cents(inv, "overdue") == 12_000


def test_paid_in_full_with_penalty_makes_unsuspend_candidate(db) -> None:
    m = _merchant(db)
    inv = _invoice(db, m.id, due=NOW - timedelta(days=1))
    LP.apply_due_penalties(db, now=NOW, pct=20)
    ids = {c["merchant_id"] for c in LP.unsuspend_candidates(db)}
    assert m.id not in ids
    db.refresh(inv)
    inv.amount_paid_cents = 10_000  # base only: still owes the penalty
    db.commit()
    assert m.id not in {c["merchant_id"] for c in LP.unsuspend_candidates(db)}
    inv.amount_paid_cents = 12_000
    db.commit()
    assert m.id in {c["merchant_id"] for c in LP.unsuspend_candidates(db)}


def test_suspension_event_reuses_suspension_email() -> None:
    specs = _specs_for_event(
        "merchant.suspended",
        {"merchant_id": "m1", "company_name": "Acme", "merchant_email": "ap@acme.test",
         "reason": "unpaid_invoice"},
    )
    keys = {(s.get("channel"), s["template_key"]) for s in specs}
    assert any(k[1] == "merchant_account_suspended" for k in keys)


def test_auto_unsuspend_only_when_paid_in_full_and_idempotent(db) -> None:

    m = _merchant(db)
    inv = _invoice(db, m.id, due=NOW - timedelta(days=1))
    LP.apply_due_penalties(db, now=NOW, pct=20)
    db.refresh(m)
    assert str(m.status).upper() == MerchantStatus.SUSPENDED.value
    db.refresh(inv)
    inv.amount_paid_cents = 10_000  # base only: penalty still owed -> stays suspended
    db.commit()
    assert LP.auto_unsuspend(db, m.id) == []
    inv.amount_paid_cents = 12_000
    db.commit()
    assert LP.auto_unsuspend(db, m.id) == [m.id]
    db.refresh(m)
    assert str(m.status).upper() == MerchantStatus.ACTIVE.value
    assert LP.auto_unsuspend(db, m.id) == []  # idempotent


def test_reinstated_event_sends_in_app_and_bilingual_email() -> None:
    from porterchain_api.notification_engine.templates import TEMPLATES

    specs = _specs_for_event(
        "merchant.unsuspended",
        {"merchant_id": "m1", "company_name": "Acme", "merchant_email": "ap@acme.test",
         "reason": "paid_in_full"},
    )
    chans = {s.get("channel") for s in specs if s["template_key"] == "merchant_account_reinstated"}
    assert {"in_app", "email"} <= chans
    t = TEMPLATES["merchant_account_reinstated"]
    assert "réactivé" in t["subject"] and "active again" in t["body"] and "Bonjour" in t["body"]
