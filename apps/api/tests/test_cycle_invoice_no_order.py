"""A cycle invoice has order_id=NULL. Every reader must cope: collections, aging, AR,
dashboard, invoice list/detail, PDF, reminder email and the merchant portal."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.billing_engine.invoice_numbering import allocate_invoice_number, ensure_payment_reference
from porterchain_api.booking_models import Invoice
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.main import app
from porterchain_api.merchant_models import Merchant


def _cycle_invoice(db, *, overdue_days: int = 40) -> tuple[Merchant, Invoice]:
    m = Merchant(
        status=MerchantStatus.ACTIVE.value,
        company_name=f"Cycle Co {uuid.uuid4().hex[:6]}",
        email=f"ap_{uuid.uuid4().hex[:8]}@cycle.test",
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
        amount_cents=30_000,
        tax_cents=3_900,
        currency="cad",
        status="sent",
        billing_kind="cycle",
        billing_period_start=now - timedelta(days=overdue_days + 37),
        billing_period_end=now - timedelta(days=overdue_days + 30),
        due_at=now - timedelta(days=overdue_days),
    )
    db.add(inv)
    db.flush()
    ensure_payment_reference(db, inv)
    db.commit()
    return m, inv


@pytest.fixture()
def admin_client(db, monkeypatch):
    import sys

    # Module authz has its own tests; the synthetic admin has no SpiceDB tuples.
    for name, mod in list(sys.modules.items()):
        if name.startswith("porterchain_api.routers.admin") and hasattr(mod, "require_module"):
            monkeypatch.setattr(mod, "require_module", lambda ctx, module: None)
    admin = AdminContext(
        user=AdminUser(clerk_user_id="cyc-admin", email="ops@porterchain.com", role="super_admin"),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_admin_finance_endpoints_survive_an_orderless_invoice(admin_client, db) -> None:
    _m, inv = _cycle_invoice(db)
    for path in (
        "/v1/admin/finance/collections",
        "/v1/admin/finance/dashboard",
        "/v1/admin/finance/invoices",
        "/v1/admin/finance/reports",
        f"/v1/admin/finance/invoices/{inv.id}",
        "/v1/admin/finance/export",
        "/v1/admin/finance/payments",
        "/v1/admin/finance/ledger",
        "/v1/admin/finance/summary",
        "/v1/admin/finance/duplicates",
    ):
        r = admin_client.get(path)
        assert r.status_code == 200, (path, r.status_code, r.text[:300])
    rows = admin_client.get("/v1/admin/finance/collections").json()
    row = next(r for r in rows if r["invoice_id"] == inv.id)
    assert row["order_id"] is None
    assert row["aging_bucket"]
    pdf = admin_client.get(f"/v1/admin/finance/invoices/{inv.id}/pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_ar_reminder_and_merchant_views_handle_no_order(db, monkeypatch) -> None:
    from porterchain_api.admin_engine.finance_service import AdminFinanceService
    from porterchain_api.admin_engine.merchant360_board import timeline_payload
    from porterchain_api.admin_engine.merchant_lifecycle import ops_invoices
    from porterchain_api.billing_engine.ar import merchant_ar
    from porterchain_api.booking_engine.invoice_service import InvoiceService
    from porterchain_api.merchant_engine import invoice_reminder

    m, inv = _cycle_invoice(db)
    assert merchant_ar(db, m) is not None
    assert AdminFinanceService().find_duplicate_invoices(db, inv) == []

    payload = InvoiceService()._invoice_event_payload(db, None, inv)
    assert payload["order_id"] is None and payload["merchant_id"] == m.id
    assert payload["payment_reference"] == inv.payment_reference

    # No real sends: stub the notification router.
    monkeypatch.setattr(
        "porterchain_api.notification_engine.event_router.handle_domain_event", lambda *_a, **_k: None
    )
    out = invoice_reminder.remind_invoice(db, inv, m, actor_type="admin", actor_id=None)
    assert out

    crm = ops_invoices(db, m)
    assert any(r.id == inv.id for r in crm)
    events = timeline_payload(db, m.id, None)
    assert any(inv.invoice_number in e["title"] for e in events)
