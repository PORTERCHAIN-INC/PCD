"""Invoice adjustments (void / line credit / partial credit) as GST/HST credit notes.

See docs/compliance/INVOICE_ADJUSTMENTS_CANADA.md for the rules each test protects.
"""

from __future__ import annotations

import importlib.util
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminAuditLog, AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.billing_engine import invoice_adjustments as adj
from porterchain_api.billing_engine.interac.matcher import _open_invoice_rows
from porterchain_api.billing_engine.merchant_credit import merchant_credit_cents
from porterchain_api.billing_engine.merchant_service import invoice_status, outstanding_cents
from porterchain_api.billing_engine.models import BillingLedgerEntry, CreditNote, InvoiceLine
from porterchain_api.billing_engine.invoice_numbering import allocate_invoice_number, ensure_payment_reference
from porterchain_api.booking_models import Invoice
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.main import app
from porterchain_api.merchant_models import Merchant

pytestmark = pytest.mark.usefixtures("db")

SECRET = "INTERNAL-ONLY driver was late, ops ticket 4471"


@pytest.fixture(autouse=True)
def _threshold(monkeypatch):
    monkeypatch.setattr(adj, "approval_threshold_cents", lambda db: 1_000_000)


@pytest.fixture(autouse=True)
def _capture_email(monkeypatch):
    sent: list[dict] = []

    class _Log:
        status = "sent"

    from porterchain_api.notification_engine import delivery_service

    monkeypatch.setattr(delivery_service.DeliveryService, "deliver", lambda self, p: sent.append(p) or _Log())
    return sent


def _invoice(db, *, paid: int = 0, lines: bool = True) -> Invoice:
    """Cycle invoice: two $100.00 lines + 13% HST = $226.00, $26.00 tax, due in 30 days."""
    m = Merchant(
        status=MerchantStatus.ACTIVE.value,
        company_name=f"Credit Co {uuid.uuid4().hex[:6]}",
        legal_name="Credit Co Ltd.",
        email=f"ap_{uuid.uuid4().hex[:8]}@credit.test",
        payment_terms="NET_30",
        billing_cycle="WEEKLY",
    )
    db.add(m)
    db.flush()
    now = datetime.now(UTC)
    inv = Invoice(
        order_id=None,
        merchant_id=m.id,
        invoice_number=allocate_invoice_number(db),
        amount_cents=22_600,
        tax_cents=2_600,
        tax_province="ON",
        currency="cad",
        status="sent",
        billing_kind="cycle",
        amount_paid_cents=paid,
        due_at=now + timedelta(days=30),
        issued_at=now - timedelta(days=1),
    )
    db.add(inv)
    db.flush()
    ensure_payment_reference(db, inv)
    if lines:
        for i in (1, 2):
            db.add(InvoiceLine(invoice_id=inv.id, description=f"Delivery {i}", amount_cents=10_000, tax_cents=1_300, tax_province="ON"))
    db.commit()
    return inv


def _status(inv: Invoice) -> tuple[str, int]:
    st = invoice_status(inv, None, None)
    return st, outstanding_cents(inv, st)


def _lines(db, inv):
    return [r["line_id"] for r in adj.line_breakdown(db, inv)]


# ------------------------------------------------------------------ tax & status


def test_partial_credit_prorates_tax_half_up_and_sets_partially_credited(db) -> None:
    inv = _invoice(db)
    note = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=1_000, reason_code="goodwill", actor_id="a1")
    db.commit()
    # 1000 * 2600 / 22600 = 115.04 -> 115
    assert (note.amount_cents, note.tax_cents, note.subtotal_cents) == (1_000, 115, 885)
    assert note.status == "issued" and note.tax_province == "ON"
    assert note.original_invoice_number == inv.invoice_number and note.original_invoice_date is not None
    assert note.recipient_name == "Credit Co Ltd."
    assert _status(inv) == ("partially_credited", 21_600)


def test_half_cent_rounds_up() -> None:
    from decimal import Decimal

    assert adj._round(Decimal("0.5")) == 1 and adj._round(Decimal("2.5")) == 3


def test_line_credit_then_void_reverses_exactly_the_tax_charged(db) -> None:
    inv = _invoice(db)
    l1, _l2 = _lines(db, inv)
    a = adj.request_credit(db, invoice_id=inv.id, kind="lines", line_ids=[l1], reason_code="our_fault", actor_id="a1")
    assert (a.amount_cents, a.tax_cents, a.reason_code) == (11_300, 1_300, "service_failure")
    with pytest.raises(ValueError, match="invoice_line_already_credited"):
        adj.request_credit(db, invoice_id=inv.id, kind="lines", line_ids=[l1], reason_code="goodwill", actor_id="a1")
    b = adj.request_credit(db, invoice_id=inv.id, kind="void", reason_code="test_delivery", actor_id="a1")
    db.commit()
    assert (b.amount_cents, b.tax_cents) == (11_300, 1_300)
    assert a.tax_cents + b.tax_cents == inv.tax_cents
    assert _status(inv) == ("void", 0) and inv.voided_at is not None
    with pytest.raises(ValueError, match="invoice_fully_credited"):
        adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=1, reason_code="goodwill", actor_id="a1")


def test_final_partial_takes_the_exact_tax_remainder(db) -> None:
    inv = _invoice(db, lines=False)
    a = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=333, reason_code="goodwill", actor_id="a1")
    b = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=22_600 - 333, reason_code="goodwill", actor_id="a1")
    db.commit()
    assert a.tax_cents + b.tax_cents == 2_600
    assert _status(inv) == ("credited", 0)


def test_credit_cannot_exceed_invoice(db) -> None:
    inv = _invoice(db)
    with pytest.raises(ValueError, match="credit_exceeds_invoice"):
        adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=22_601, reason_code="goodwill", actor_id="a1")


def test_reason_codes_are_required_and_other_needs_a_note(db) -> None:
    inv = _invoice(db)
    with pytest.raises(ValueError, match="credit_reason_invalid"):
        adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=100, reason_code="because", actor_id="a1")
    with pytest.raises(ValueError, match="credit_note_required_for_other"):
        adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=100, reason_code="other", actor_id="a1")


# ------------------------------------------------------------------ numbering


def test_credit_note_numbers_are_sequential_per_year(db) -> None:
    inv = _invoice(db)
    a = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=100, reason_code="goodwill", actor_id="a1")
    b = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=100, reason_code="goodwill", actor_id="a1")
    db.commit()
    year = datetime.now(UTC).year
    na, nb = (int(n.credit_note_number.rsplit("-", 1)[1]) for n in (a, b))
    assert a.credit_note_number.startswith(f"CN-{year}-") and nb == na + 1


def test_rolled_back_credit_note_gives_its_number_back(db) -> None:
    inv = _invoice(db)
    first = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=100, reason_code="goodwill", actor_id="a1")
    num = first.credit_note_number
    db.rollback()
    again = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=100, reason_code="goodwill", actor_id="a1")
    db.commit()
    assert again.credit_note_number == num


# ------------------------------------------------------------------ balances & money back


def test_credit_on_paid_interac_invoice_becomes_merchant_credit(db) -> None:
    inv = _invoice(db, paid=22_600)
    before = merchant_credit_cents(db, inv.merchant_id)
    note = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=5_000, reason_code="pricing_error", actor_id="a1")
    db.commit()
    assert note.settlement == "credit_balance" and note.settlement_cents == 5_000
    assert merchant_credit_cents(db, inv.merchant_id) == before + 5_000
    assert _status(inv) == ("paid", 0)


def test_partly_paid_invoice_only_returns_the_overpaid_part(db) -> None:
    inv = _invoice(db, paid=20_000)
    note = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=5_000, reason_code="goodwill", actor_id="a1")
    db.commit()
    # Net total 17600, paid 20000: 2400 goes to credit balance.
    assert note.settlement_cents == 2_400
    assert _status(inv)[1] == 0


def test_matcher_and_ledger_use_the_new_balance(db) -> None:
    inv = _invoice(db)
    adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=2_600, reason_code="goodwill", actor_id="a1")
    db.commit()
    rows = dict((i.id, out) for i, out in _open_invoice_rows(db, inv.merchant_id))
    assert rows[inv.id] == 20_000
    entry = db.query(BillingLedgerEntry).filter(BillingLedgerEntry.invoice_id == inv.id, BillingLedgerEntry.kind == "invoice_credit_note").one()
    assert entry.amount_cents == 2_600 and entry.metadata_json["tax_cents"] == 299
    adj.request_credit(db, invoice_id=inv.id, kind="void", reason_code="goodwill", actor_id="a1")
    db.commit()
    assert inv.id not in dict((i.id, o) for i, o in _open_invoice_rows(db, inv.merchant_id))


def test_reminder_refuses_a_voided_invoice(db) -> None:
    from porterchain_api.merchant_engine.invoice_reminder import remind_invoice

    inv = _invoice(db)
    adj.request_credit(db, invoice_id=inv.id, kind="void", reason_code="duplicate_billing", actor_id="a1")
    db.commit()
    with pytest.raises(ValueError, match="nothing_outstanding"):
        remind_invoice(db, inv, db.get(Merchant, inv.merchant_id), actor_type="admin", actor_id="a1")


# ------------------------------------------------------------------ approval


def test_above_threshold_needs_a_different_approver(db, monkeypatch) -> None:
    monkeypatch.setattr(adj, "approval_threshold_cents", lambda db: 1_000)
    inv = _invoice(db)
    note = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=5_000, reason_code="goodwill", actor_id="a1")
    db.commit()
    assert note.status == "pending_approval" and note.credit_note_number is None
    assert inv.credited_cents == 0 and _status(inv)[1] == 22_600
    assert adj.creditable_cents(db, inv) == 17_600
    with pytest.raises(PermissionError):
        adj.approve_credit(db, credit_note_id=note.id, actor_id="a1")
    adj.approve_credit(db, credit_note_id=note.id, actor_id="a2")
    db.commit()
    assert note.status == "issued" and note.approved_by == "a2" and note.credit_note_number
    assert inv.credited_cents == 5_000


def test_rejected_note_is_kept_unnumbered(db, monkeypatch) -> None:
    monkeypatch.setattr(adj, "approval_threshold_cents", lambda db: 0)
    inv = _invoice(db)
    note = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=100, reason_code="goodwill", actor_id="a1")
    adj.reject_credit(db, credit_note_id=note.id, actor_id="a2", note_text="not justified")
    db.commit()
    assert db.get(CreditNote, note.id).status == "rejected" and note.credit_note_number is None
    assert inv.credited_cents == 0


# ------------------------------------------------------------------ PDF & email


def test_pdf_carries_prescribed_information(db) -> None:
    from porterchain_api.reporting.credit_note_pdf import credit_note_pdf

    inv = _invoice(db)
    note = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=1_000, reason_code="goodwill", internal_note=SECRET, actor_id="a1")
    db.commit()
    pdf, name = credit_note_pdf(db, note)
    assert pdf.startswith(b"%PDF") and name == f"{note.credit_note_number}.pdf"
    # Uncompressed like invoices (order_documents), so the text is checkable.
    for text in (b"CREDIT NOTE", note.credit_note_number.encode(), inv.invoice_number.encode(), b"Credit Co Ltd.", b"Tax reversed"):
        assert text in pdf, text
    assert b"INTERNAL-ONLY" not in pdf


def test_email_has_customer_reason_only_and_logs_masked(db, _capture_email, caplog) -> None:
    from porterchain_api.platform.credit_note_email import mask_email, send_credit_note_email

    inv = _invoice(db)
    m = db.get(Merchant, inv.merchant_id)
    note = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=1_000, reason_code="service_failure", internal_note=SECRET, actor_id="a1")
    db.commit()
    caplog.set_level("INFO")
    out = send_credit_note_email(db, note)
    payload = _capture_email[-1]
    assert payload["template"] == "invoice_credit_note_issued" and payload["recipient"] == m.email
    assert payload["context"]["customer_reason"] == adj.REASON_CODES["service_failure"]
    assert "INTERNAL" not in str(payload) and out["recipient"] == mask_email(m.email)
    assert m.email not in caplog.text
    assert mask_email("alice@example.com") == "a***@example.com"


def test_template_renders() -> None:
    from porterchain_api.notification_engine.templates import render_email

    subject, body, html = render_email(
        "invoice_credit_note_issued",
        {
            k: "x"
            for k in (
                "recipient_name invoice_date customer_reason subtotal_display tax_display tax_label "
                "balance_display settlement_line document_url support_email supplier_legal_name"
            ).split()
        }
        | {"credit_note_number": "CN-2026-000001", "invoice_number": "INV-2026-000001", "amount_display": "$10.00"},
    )
    assert "CN-2026-000001" in subject and "Credit note" in (html or body)


# ------------------------------------------------------------------ API


@pytest.fixture()
def admin_client(db, monkeypatch):
    import sys

    for name, mod in list(sys.modules.items()):
        if name.startswith("porterchain_api.routers.admin") and hasattr(mod, "require_module"):
            monkeypatch.setattr(mod, "require_module", lambda ctx, module: None)
    admin = AdminContext(
        user=AdminUser(id=str(uuid.uuid4()), clerk_user_id="cn-admin", email="ops@porterchain.com", role="super_admin"),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def stepped_up(monkeypatch):
    from porterchain_api.routers.admin import finance_credit_notes

    monkeypatch.setattr(finance_credit_notes, "enforce_staff_step_up", lambda *a, **k: None)


def test_api_requires_step_up(admin_client, db) -> None:
    inv = _invoice(db)
    r = admin_client.post(f"/v1/admin/finance/invoices/{inv.id}/credit-notes", json={"kind": "void", "reason_code": "goodwill"})
    assert r.status_code == 403
    assert db.query(CreditNote).filter(CreditNote.invoice_id == inv.id).count() == 0


def test_api_requires_finance_module(db, monkeypatch) -> None:
    from fastapi import HTTPException

    from porterchain_api.routers.admin import finance_credit_notes

    def deny(ctx, module):
        raise HTTPException(status_code=403, detail="module_forbidden")

    monkeypatch.setattr(finance_credit_notes, "require_module", deny)
    admin = AdminContext(
        user=AdminUser(id=str(uuid.uuid4()), clerk_user_id="cn-viewer", email="v@porterchain.com", role="support"),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    try:
        inv = _invoice(db)
        r = TestClient(app).post(f"/v1/admin/finance/invoices/{inv.id}/credit-notes", json={"kind": "void", "reason_code": "goodwill"})
        assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_api_issue_list_pdf_and_audit(admin_client, stepped_up, db) -> None:
    inv = _invoice(db)
    line = _lines(db, inv)[0]
    r = admin_client.post(
        f"/v1/admin/finance/invoices/{inv.id}/credit-notes",
        json={"kind": "lines", "line_ids": [line], "reason_code": "service_failure", "internal_note": SECRET},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "issued" and body["tax_cents"] == 1_300 and body["email"]["sent"]
    assert body["invoice"]["credited_cents"] == 11_300
    summary = admin_client.get(f"/v1/admin/finance/invoices/{inv.id}/adjustments").json()
    assert summary["creditable_cents"] == 11_300 and summary["lines"][0]["credited"] is True
    pdf = admin_client.get(f"/v1/admin/finance/credit-notes/{body['credit_note_id']}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    detail = admin_client.get(f"/v1/admin/finance/invoices/{inv.id}").json()
    assert detail["status"] == "partially_credited" and detail["credited_cents"] == 11_300
    assert any("line_id" in ln for ln in detail["lines"])
    audit = db.query(AdminAuditLog).filter(AdminAuditLog.resource_id == inv.id, AdminAuditLog.action == "finance.credit_note.issued").one()
    assert audit is not None


def test_api_errors(admin_client, stepped_up, db) -> None:
    inv = _invoice(db)
    url = f"/v1/admin/finance/invoices/{inv.id}/credit-notes"
    assert admin_client.post(url, json={"kind": "partial", "amount_cents": 99_999, "reason_code": "goodwill"}).status_code == 400
    assert admin_client.post(url, json={"kind": "refund", "reason_code": "goodwill"}).status_code == 422
    assert admin_client.post("/v1/admin/finance/invoices/nope/credit-notes", json={"kind": "void", "reason_code": "goodwill"}).status_code == 404


def test_old_ledger_only_endpoint_is_gone(admin_client) -> None:
    r = admin_client.post("/v1/admin/finance/credit-notes", json={"order_id": "x", "amount_cents": 1, "reason": "x"})
    assert r.status_code in (404, 405)


def test_merchant_views_hide_internal_note(db) -> None:
    from porterchain_api.merchant_engine.billing_service import MerchantBillingService
    from porterchain_api.merchant_engine.billing_views import list_credit_notes
    from porterchain_api.domain.merchant_states import MerchantRole
    from porterchain_api.merchant_engine.rbac import MerchantContext

    inv = _invoice(db)
    note = adj.request_credit(db, invoice_id=inv.id, kind="partial", amount_cents=1_000, reason_code="goodwill", internal_note=SECRET, actor_id="a1")
    db.commit()
    ctx = MerchantContext(merchant=db.get(Merchant, inv.merchant_id), user=None, role=MerchantRole.OWNER)
    svc = MerchantBillingService()
    rows = list_credit_notes(svc, db, ctx)
    assert rows[0]["credit_note_number"] == note.credit_note_number and rows[0]["tax_cents"] == 115
    assert "INTERNAL" not in str(rows)
    assert "INTERNAL" not in str(adj.notes_for_invoice(db, inv.id, internal=False))
    pdf, _ = svc.credit_note_pdf(db, ctx, note.id)
    assert pdf.startswith(b"%PDF")


# ------------------------------------------------------------------ migration


def test_migration_upgrade_and_downgrade(db_url) -> None:
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "cn5creditnotes0005_invoice_credit_notes.py"
    spec = importlib.util.spec_from_file_location("cn5", path)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    schema = f"cn5_{uuid.uuid4().hex[:8]}"
    engine = sa.create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(sa.text(f"CREATE SCHEMA {schema}"))
        conn.execute(sa.text(f"SET search_path TO {schema}"))
        conn.execute(sa.text("CREATE TABLE invoices (id VARCHAR(36) PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE credit_notes (id VARCHAR(36) PRIMARY KEY, amount_cents INTEGER)"))
        conn.execute(sa.text("INSERT INTO invoices VALUES ('i1')"))
        conn.execute(sa.text("INSERT INTO credit_notes VALUES ('c1', 5)"))
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mig.upgrade()
        cols = {c["name"] for c in sa.inspect(conn).get_columns("credit_notes", schema=schema)}
        assert {"credit_note_number", "tax_cents", "original_invoice_number", "internal_note"} <= cols
        assert conn.execute(sa.text("SELECT credited_cents FROM invoices")).scalar() == 0
        with Operations.context(ctx):
            mig.downgrade()
        cols = {c["name"] for c in sa.inspect(conn).get_columns("credit_notes", schema=schema)}
        assert cols == {"id", "amount_cents"}
        assert "credited_cents" not in {c["name"] for c in sa.inspect(conn).get_columns("invoices", schema=schema)}
        assert conn.execute(sa.text("SELECT amount_cents FROM credit_notes")).scalar() == 5
        conn.execute(sa.text(f"DROP SCHEMA {schema} CASCADE"))
