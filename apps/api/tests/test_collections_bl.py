"""BL — collections shows due date, aging, the merchant to open, and who to call."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.finance_service import AdminFinanceService
from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.billing_engine.ar import AGING_OLDEST, aging_bucket
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.main import app
from porterchain_api.merchant_engine.invoice_reminder import (
    primary_ap_contact,
    primary_billing_email,
)
from porterchain_api.merchant_models import Merchant
from porterchain_api.booking_models import Invoice, Order, Payment

INVOICE_CENTS = 30_000


def _merchant(db, *, billing_contacts: list[dict] | None = None, phone: str | None = None) -> Merchant:
    merchant = Merchant(
        status=MerchantStatus.ACTIVE.value,
        company_name=f"Collections Co {uuid.uuid4().hex[:6]}",
        email=f"ap_{uuid.uuid4().hex[:10]}@collect.test",
        phone=phone,
        payment_terms="NET_30",
    )
    if billing_contacts is not None:
        merchant.profile = {"settings": {"billing_contacts": billing_contacts}}
    db.add(merchant)
    db.flush()
    return merchant


def _open_invoice(db, merchant: Merchant, *, due_in_days: int, cents: int = INVOICE_CENTS) -> Invoice:
    """An unpaid invoice whose due date sits `due_in_days` from now (negative = late)."""
    order = Order(
        merchant_id=merchant.id,
        state=OrderState.INVOICED.value,
        amount_cents=cents,
        currency="cad",
        payment_terms="NET_30",
        order_number=f"COL-{uuid.uuid4().hex[:8].upper()}",
        tracking_number=f"TRK{uuid.uuid4().hex[:10].upper()}",
        pickup={"formatted": "100 King St W, Toronto"},
        dropoff={"formatted": "200 Bay St, Toronto"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    invoice = Invoice(
        invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
        order_id=order.id,
        merchant_id=merchant.id,
        amount_cents=cents,
        tax_cents=0,
        fees_cents=0,
        currency="cad",
        due_at=datetime.now(UTC) + timedelta(days=due_in_days),
    )
    db.add(invoice)
    db.flush()
    return invoice


def _rows_for(db, merchant: Merchant) -> list[dict]:
    """Only this merchant's rows — the local dev book holds other merchants' debt."""
    return [r for r in AdminFinanceService().collections(db) if r["merchant_id"] == merchant.id]


# --- Aging ladder ---


def test_aging_ladder_reads_like_an_ar_report() -> None:
    assert aging_bucket(0) == "Current"
    assert aging_bucket(1) == "1–30 days"
    assert aging_bucket(30) == "1–30 days"
    assert aging_bucket(31) == "31–60 days"
    assert aging_bucket(60) == "31–60 days"
    assert aging_bucket(61) == "61–90 days"
    assert aging_bucket(90) == "61–90 days"
    assert aging_bucket(91) == AGING_OLDEST
    assert aging_bucket(400) == AGING_OLDEST


def test_a_bucket_is_never_a_raw_number() -> None:
    """Finance reads buckets, not integers."""
    for days in (0, 5, 45, 75, 200):
        assert not aging_bucket(days).isdigit()


# --- Collections rows ---


def test_a_collections_row_carries_due_date_and_aging(db) -> None:
    merchant = _merchant(db, billing_contacts=[])
    _open_invoice(db, merchant, due_in_days=-45)

    rows = _rows_for(db, merchant)
    assert len(rows) == 1
    row = rows[0]
    assert row["due_date"] is not None
    assert row["days_overdue"] >= 44
    assert row["aging_bucket"] == "31–60 days"
    assert row["outstanding_cents"] == INVOICE_CENTS


def test_an_invoice_not_yet_due_is_listed_as_current(db) -> None:
    """It is collectable work, but it is not late and must not be coloured as such."""
    merchant = _merchant(db, billing_contacts=[])
    _open_invoice(db, merchant, due_in_days=10)

    row = _rows_for(db, merchant)[0]
    assert row["days_overdue"] == 0
    assert row["aging_bucket"] == "Current"


def test_the_row_links_to_the_merchant(db) -> None:
    """Collections has to get from an invoice to the company file in one click."""
    merchant = _merchant(db, billing_contacts=[])
    _open_invoice(db, merchant, due_in_days=-5)

    row = _rows_for(db, merchant)[0]
    assert row["merchant_id"] == merchant.id
    assert row["merchant_name"] == merchant.company_name


def test_oldest_debt_comes_first(db) -> None:
    """A human works the list top down, so the list must be in chase order."""
    merchant = _merchant(db, billing_contacts=[])
    _open_invoice(db, merchant, due_in_days=10)
    _open_invoice(db, merchant, due_in_days=-100)
    _open_invoice(db, merchant, due_in_days=-40)

    overdue = [r["days_overdue"] for r in _rows_for(db, merchant)]
    assert overdue == sorted(overdue, reverse=True)
    assert overdue[0] >= 99
    assert overdue[-1] == 0


def test_a_paid_invoice_leaves_the_list(db) -> None:
    merchant = _merchant(db, billing_contacts=[])
    invoice = _open_invoice(db, merchant, due_in_days=-20)
    assert len(_rows_for(db, merchant)) == 1

    db.add(
        Payment(
            order_id=invoice.order_id,
            status="SUCCEEDED",
            amount_cents=INVOICE_CENTS,
            currency="cad",
        )
    )
    db.flush()
    assert _rows_for(db, merchant) == []


# --- Who to call ---


def test_the_row_names_the_primary_ap_contact(db) -> None:
    merchant = _merchant(
        db,
        billing_contacts=[
            {"id": "1", "name": "Second Desk", "email": "second@ap.test", "phone": "416-555-0002"},
            {
                "id": "2",
                "name": "Dana Patel",
                "email": "dana@ap.test",
                "phone": "416-555-0001",
                "role": "billing",
                "is_primary": True,
            },
        ],
    )
    _open_invoice(db, merchant, due_in_days=-15)

    contact = _rows_for(db, merchant)[0]["ap_contact"]
    assert contact["name"] == "Dana Patel"
    assert contact["phone"] == "416-555-0001"
    assert contact["email"] == "dana@ap.test"
    assert contact["is_primary"] is True
    assert contact["source"] == "billing_contact"


def test_an_ap_contact_with_a_phone_but_no_email_is_still_reachable(db) -> None:
    """Chasing a payment needs a number; a mailbox is optional."""
    merchant = _merchant(
        db,
        billing_contacts=[
            {"id": "1", "name": "Front Desk", "phone": "416-555-0100", "is_primary": True}
        ],
    )
    contact = primary_ap_contact(merchant)
    assert contact.name == "Front Desk"
    assert contact.phone == "416-555-0100"
    assert contact.email is None
    assert contact.is_named

    # The reminder path still needs a mailbox, so it falls back to the company.
    assert primary_billing_email(merchant) == merchant.email


def test_no_ap_contact_falls_back_to_the_company_and_says_so(db) -> None:
    merchant = _merchant(db, billing_contacts=[], phone="416-555-0199")
    _open_invoice(db, merchant, due_in_days=-3)

    contact = _rows_for(db, merchant)[0]["ap_contact"]
    assert contact["source"] == "company"
    assert contact["phone"] == "416-555-0199"
    assert contact["email"] == merchant.email
    assert contact["is_primary"] is False


def test_a_company_with_nothing_on_file_is_not_a_crash(db) -> None:
    merchant = _merchant(db, billing_contacts=[])
    merchant.phone = None
    db.flush()

    contact = primary_ap_contact(merchant)
    assert contact.phone is None
    assert contact.source == "company"
    assert primary_ap_contact(None).as_dict()["name"] is None


def test_every_invoice_for_one_merchant_names_the_same_contact(db) -> None:
    """Two open invoices must not disagree about who to phone."""
    merchant = _merchant(
        db,
        billing_contacts=[
            {"id": "1", "name": "Dana Patel", "phone": "416-555-0001", "is_primary": True}
        ],
    )
    _open_invoice(db, merchant, due_in_days=-10)
    _open_invoice(db, merchant, due_in_days=-70)

    rows = _rows_for(db, merchant)
    assert len(rows) == 2
    assert {r["ap_contact"]["name"] for r in rows} == {"Dana Patel"}
    assert {r["aging_bucket"] for r in rows} == {"1–30 days", "61–90 days"}


def test_blank_contact_fields_do_not_become_empty_strings(db) -> None:
    """A blank phone must read as missing, not as a dialable empty number."""
    merchant = _merchant(
        db,
        billing_contacts=[{"id": "1", "name": "Dana", "phone": "   ", "email": "", "is_primary": True}],
    )
    contact = primary_ap_contact(merchant)
    assert contact.phone is None
    assert contact.email is None


# --- The route ---


@pytest.fixture
def admin_client(db, monkeypatch):
    # Module authz has its own tests; the synthetic admin has no SpiceDB tuples.
    monkeypatch.setattr(
        "porterchain_api.routers.admin.finance.require_module", lambda ctx, module: None
    )
    admin = AdminContext(
        user=AdminUser(clerk_user_id="col-admin", email="ops@porterchain.com", role="super_admin"),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_the_endpoint_ships_aging_and_the_contact(admin_client, db) -> None:
    """The response model must not flatten the collections fields away."""
    merchant = _merchant(
        db,
        billing_contacts=[
            {
                "id": "1",
                "name": "Dana Patel",
                "email": "dana@ap.test",
                "phone": "416-555-0001",
                "is_primary": True,
            }
        ],
    )
    _open_invoice(db, merchant, due_in_days=-95)

    res = admin_client.get("/v1/admin/finance/collections")
    assert res.status_code == 200, res.text
    row = next(r for r in res.json() if r["merchant_id"] == merchant.id)
    assert row["due_date"] is not None
    assert row["days_overdue"] >= 94
    assert row["aging_bucket"] == AGING_OLDEST
    assert row["ap_contact"]["phone"] == "416-555-0001"
    assert row["ap_contact"]["name"] == "Dana Patel"
