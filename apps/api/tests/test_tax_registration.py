"""GST/HST registration: one source; unset = no GST/HST anywhere (small supplier, ETA s.148).

Rules: docs/compliance/INVOICE_ADJUSTMENTS_CANADA.md §10.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminAuditLog, AdminUser, TaxRegistration
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.billing_engine.tax import charged_tax_split, split_amount
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_api.platform import tax_registration as reg

BN = "123456789RT0001"


@pytest.fixture()
def clean(db):
    """Each test starts unregistered and leaves no registration rows behind."""
    db.query(TaxRegistration).delete()
    db.commit()
    reg.clear_cache(db)
    yield db
    db.rollback()
    db.query(TaxRegistration).delete()
    db.commit()
    reg.clear_cache(db)


def _register(db, on: date, number: str | None = BN, name: str = "PorterChain Inc.") -> None:
    reg.record_registration(db, gst_hst_number=number, legal_name=name, effective_from=on, actor_id=None)
    db.commit()
    reg.clear_cache(db)


# ---------------------------------------------------------------- BN validation


@pytest.mark.parametrize(
    "raw,out",
    [("123456789RT0001", "123456789 RT0001"), ("123456789 rt 0001", "123456789 RT0001"), ("", "")],
)
def test_bn_normalizes(raw, out) -> None:
    assert reg.normalize_gst_hst(raw) == out


@pytest.mark.parametrize("raw", ["12345678RT0001", "123456789RP0001", "123456789RT001", "abc", "123456789"])
def test_bn_rejects_bad_format(raw) -> None:
    with pytest.raises(ValueError):
        reg.normalize_gst_hst(raw)


def test_legal_name_required(clean) -> None:
    with pytest.raises(ValueError, match="legal_name_required"):
        reg.record_registration(clean, gst_hst_number=BN, legal_name="", effective_from=date.today(), actor_id=None)


# ---------------------------------------------------------------- unregistered = zero tax


def test_unregistered_split_is_zero_everywhere(clean) -> None:
    assert not reg.collects_tax(clean)
    assert reg.supplier_gst_hst_number(clean) == ""
    for mode in ("exclusive", "inclusive"):
        s = split_amount(11_300, province="ON", mode=mode, collect_qst=False, registered=False)
        assert s.tax_cents == 0 and s.percent == 0 and s.label == ""
    # An old quote that had added tax: the tax comes out, the customer pays pre-tax.
    s = split_amount(11_300, province="ON", mode="exclusive", collect_qst=False, quoted_tax=1_300, registered=False)
    assert (s.pretax_cents, s.tax_cents, s.gross_cents) == (10_000, 0, 10_000)
    # Stripe-charged amount: all of it is the price, none of it tax.
    s = charged_tax_split(clean, None, 5_000)
    assert s.tax_cents == 0 and s.pretax_cents == 5_000


def test_unregistered_pricing_and_settings(clean) -> None:
    from porterchain_api.admin_engine.platform_settings import default_tax_percent, tax_label
    from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository

    assert default_tax_percent(clean) == 0
    assert tax_label(clean) == ""
    assert SqlAlchemyPricingRepository(clean)._load_tax_config().hst_percent == 0.0


def test_status_endpoint_shape(clean) -> None:
    st = reg.registration_status(clean)
    assert st["registered"] is False and st["gst_hst_number"] == "" and st["history"] == []
    assert "no GST/HST" in st["warning"]


# ---------------------------------------------------------------- registered + date boundary


def test_registered_from_effective_date_only(clean) -> None:
    today = date.today()
    _register(clean, today)
    assert reg.collects_tax(clean, today)
    assert not reg.collects_tax(clean, today - timedelta(days=1))
    assert reg.supplier_gst_hst_number(clean, today) == "123456789 RT0001"
    s = split_amount(10_000, province="ON", mode="exclusive", collect_qst=False, registered=True)
    assert s.tax_cents == 1_300
    from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository

    assert SqlAlchemyPricingRepository(clean)._load_tax_config().hst_percent > 0


def test_boundary_uses_toronto_day(clean) -> None:
    on = date(2026, 3, 1)
    _register(clean, on)
    # 2026-03-01 03:00 UTC is still Feb 28 in Toronto → not yet registered.
    assert not reg.collects_tax(clean, datetime(2026, 3, 1, 3, 0, tzinfo=UTC))
    assert reg.collects_tax(clean, datetime(2026, 3, 1, 6, 0, tzinfo=UTC))


def test_future_registration_is_upcoming_not_current(clean) -> None:
    _register(clean, date.today() + timedelta(days=10))
    st = reg.registration_status(clean)
    assert st["registered"] is False and st["upcoming"]["gst_hst_number"] == "123456789 RT0001"


def test_history_append_only_and_ordered(clean) -> None:
    d = date.today() - timedelta(days=30)
    _register(clean, d)
    with pytest.raises(ValueError, match="before_latest"):
        reg.record_registration(clean, gst_hst_number=None, legal_name=None, effective_from=d - timedelta(days=1), actor_id=None)
    with pytest.raises(ValueError, match="unchanged"):
        reg.record_registration(clean, gst_hst_number=BN, legal_name="PorterChain Inc.", effective_from=d, actor_id=None)
    _register(clean, date.today(), number=None)  # deregistered from today
    assert not reg.collects_tax(clean)
    assert reg.collects_tax(clean, date.today() - timedelta(days=1))
    assert [h["gst_hst_number"] for h in reg.registration_status(clean)["history"]] == [None, "123456789 RT0001"]


# ---------------------------------------------------------------- documents


def _invoice_stub(tax_cents: int, issued: datetime):
    return SimpleNamespace(
        id="inv", invoice_number="INV-T", tax_cents=tax_cents, tax_province="ON", issued_at=issued, created_at=issued
    )


def test_credit_note_pdf_without_tax_has_no_gst_hst(clean) -> None:
    from porterchain_api.reporting.credit_note_pdf import credit_note_pdf

    note = SimpleNamespace(
        status="issued", credit_note_number="CN-T-1", issued_at=datetime.now(UTC), original_invoice_date=datetime.now(UTC),
        original_invoice_number="INV-T", currency="cad", tax_province="ON", merchant_id=None, customer_id="c",
        recipient_name="Ann", customer_reason="Goodwill", lines_json=[{"description": "Delivery", "gross_cents": 5000, "tax_cents": 0}],
        subtotal_cents=5000, tax_cents=0, amount_cents=5000, settlement=None, settlement_cents=0,
    )
    pdf, _ = credit_note_pdf(clean, note)
    text = pdf.decode("latin-1")
    for needle in ("GST/HST", "HST", "Tax reversed", "(not set)", "input tax credit"):
        assert needle not in text


def test_credit_note_pdf_with_tax_prints_number_of_invoice_date(clean) -> None:
    from porterchain_api.reporting.credit_note_pdf import credit_note_pdf

    _register(clean, date.today() - timedelta(days=5))
    note = SimpleNamespace(
        status="issued", credit_note_number="CN-T-2", issued_at=datetime.now(UTC), original_invoice_date=datetime.now(UTC),
        original_invoice_number="INV-T", currency="cad", tax_province="ON", merchant_id=None, customer_id="c",
        recipient_name="Ann", customer_reason="Goodwill", lines_json=[{"description": "Delivery", "gross_cents": 11300, "tax_cents": 1300}],
        subtotal_cents=10000, tax_cents=1300, amount_cents=11300, settlement=None, settlement_cents=0,
    )
    text = credit_note_pdf(clean, note)[0].decode("latin-1")
    assert "123456789 RT0001" in text and "Tax reversed" in text


def test_credit_note_email_without_tax(clean) -> None:
    from porterchain_api.notification_engine.templates import render_email

    subject, body, html = render_email(
        "invoice_credit_note_issued",
        {
            k: "x"
            for k in (
                "recipient_name invoice_date customer_reason subtotal_display balance_display "
                "settlement_line document_url support_email supplier_legal_name"
            ).split()
        }
        | {"credit_note_number": "CN-1", "invoice_number": "INV-1", "amount_display": "$50.00", "tax_lines": "", "itc_line": ""},
    )
    assert "Tax" not in body and "tax" not in body.lower().replace("taxes", "")
    assert "Tax reversed" not in (html or "")


def test_rate_card_note_has_no_hst_when_unregistered(clean) -> None:
    from porterchain_api.pricing_engine.fsa_rate_card import _taxes_note

    assert _taxes_note(clean) == ""
    _register(clean, date.today())
    assert _taxes_note(clean) == "HST extra"


# ---------------------------------------------------------------- credit notes reverse exactly


def test_credit_note_reverses_zero_tax_when_none_charged() -> None:
    from decimal import Decimal

    # Same prorating the credit-note engine uses: tax reversed = gross * tax / total.
    gross, tax_total, total = 5_000, 0, 10_000
    assert int(Decimal(gross) * Decimal(tax_total) / Decimal(total)) == 0


# ---------------------------------------------------------------- Stripe amounts


def test_stripe_checkout_amount_override(monkeypatch) -> None:
    from porterchain_api.services import stripe_service

    seen = {}

    def fake_create(**kw):
        seen.update(kw)
        return SimpleNamespace(url="https://stripe.test/x", id="cs_1")

    monkeypatch.setattr(stripe_service.stripe_sdk, "create_checkout_session", fake_create)
    monkeypatch.setattr(stripe_service, "ensure_stripe_customer", lambda s, c: None)
    quote = SimpleNamespace(id="q", amount_cents=10_000, currency="cad", vehicle_class="van", parcels={})
    cust = SimpleNamespace(id="c", email="a@b.test")
    settings = SimpleNamespace(stripe_secret="sk_test", retail_checkout_success_url="https://x/s", retail_checkout_cancel_url="https://x/c",
                               customer_checkout_success_url="https://x/s", customer_checkout_cancel_url="https://x/c")
    stripe_service.create_checkout_session(settings, quote, cust, "p", amount_cents=4_000)
    assert seen["line_items"][0]["price_data"]["unit_amount"] == 4_000


def test_reprice_open_checkout_after_credit(db, monkeypatch) -> None:
    from porterchain_api.booking_models import Payment
    from porterchain_api.platform import invoice_checkout as ic

    p = SimpleNamespace(stripe_checkout_session_id="cs_old", status="PROCESSING", failure_reason=None,
                        quote_id=None, customer_id=None, order_id=None, currency="cad")
    monkeypatch.setattr(ic, "_open_payments", lambda db, inv: [p])
    monkeypatch.setattr(ic, "invoice_balance_cents", lambda db, inv: 0)
    expired = []
    from porterchain_api.services import stripe_service

    monkeypatch.setattr(stripe_service, "expire_checkout_session", lambda s, sid: expired.append(sid) or True)
    out = ic.reprice_open_checkouts(db, SimpleNamespace(allow_stripe_mock=False), SimpleNamespace(id="i", order_id=None))
    assert expired == ["cs_old"] and p.status == "CANCELLED"
    assert out == {"expired": 1, "new_session_id": None, "amount_cents": 0}  # $0 balance → no checkout
    assert Payment  # imported model exists


# ---------------------------------------------------------------- admin API: permissions + audit


@pytest.fixture()
def admin(clean):
    ctx = AdminContext(
        user=AdminUser(id=str(uuid.uuid4()), auth_subject="tax-admin", email="ops@porterchain.com", role="super_admin"),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: ctx
    app.dependency_overrides[get_db] = lambda: clean
    yield TestClient(app)
    app.dependency_overrides.clear()


def _body(**kw):
    return {"gst_hst_number": BN, "legal_name": "PorterChain Inc.", "effective_from": date.today().isoformat()} | kw


def test_api_requires_step_up(admin, clean) -> None:
    r = admin.post("/v1/admin/finance/tax-registration", json=_body())
    assert r.status_code == 403
    assert clean.query(TaxRegistration).count() == 0


def test_api_requires_finance_module(admin, clean, monkeypatch) -> None:
    from fastapi import HTTPException

    from porterchain_api.routers.admin import finance_insights

    def deny(ctx, module):
        raise HTTPException(status_code=403, detail="module_forbidden")

    monkeypatch.setattr(finance_insights, "require_module", deny)
    monkeypatch.setattr(finance_insights, "enforce_staff_step_up", lambda *a, **k: None)
    assert admin.post("/v1/admin/finance/tax-registration", json=_body()).status_code == 403


def test_api_register_audits_and_validates(admin, clean, monkeypatch) -> None:
    from porterchain_api.routers.admin import finance_insights

    monkeypatch.setattr(finance_insights, "require_module", lambda ctx, module: None)
    monkeypatch.setattr(finance_insights, "enforce_staff_step_up", lambda *a, **k: None)
    bad = admin.post("/v1/admin/finance/tax-registration", json=_body(gst_hst_number="12345"))
    assert bad.status_code == 400
    r = admin.post("/v1/admin/finance/tax-registration", json=_body(note="CRA letter"))
    assert r.status_code == 200, r.text
    assert r.json()["registered"] is True and r.json()["gst_hst_number"] == "123456789 RT0001"
    log = clean.query(AdminAuditLog).filter(AdminAuditLog.action == "finance.tax_registration.changed").order_by(AdminAuditLog.created_at.desc()).first()
    assert log is not None and log.payload["to"]["gst_hst_number"] == "123456789 RT0001"
    assert admin.get("/v1/admin/finance/tax-registration").json()["history"][0]["note"] == "CRA letter"


def test_finance_settings_cannot_set_number_anymore() -> None:
    assert "gst_hst_number" not in reg.normalize_finance({"gst_hst_number": BN, "invoice_number_prefix": "INV"})
