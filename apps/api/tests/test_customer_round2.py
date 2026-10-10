"""Customer round 2: geo fallback, ≤5 drops, address book/autofill, orders, report a problem,
risk/churn/reorder rules, approval-gated nudges, admin 360, reviewable erasure, FR emails."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser, SupportTicket
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk import get_clerk_claims
from porterchain_api.booking_engine.customer_service import CustomerService
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.booking_models import (
    Customer,
    CustomerAddress,
    PrivacyDeletionJob,
    ReorderNudge,
)
from porterchain_api.config import Settings, get_settings
from porterchain_api.crm_suppression import is_suppressed
from porterchain_api.customer_fast import (
    account,
    admin360,
    geo,
    privacy,
    rules,
    service,
)
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_api.notification_engine.templates import render_email
from porterchain_api.schemas import AddressInput, CreateQuoteRequest
from tests.test_customer_fast_book import _body, _paid_guest_order, _quote, _token


def _admin_ctx(role: str = "super_admin") -> AdminContext:
    return AdminContext(
        user=AdminUser(clerk_user_id=f"admin-{role}-{uuid4().hex[:6]}", email=f"{role}@porterchain.com", role=role),
        role=parse_admin_role(role),
    )


# ------------------------------------------------------------------ geo + drops


def test_with_coords_uses_fsa_centroid_when_missing() -> None:
    out = geo.with_coords({"formatted": "5 Bloor St E, Toronto, ON M4W 1A8"})
    assert out is not None and isinstance(out["lat"], float) and out["coords_source"] == "fsa"
    exact = {"formatted": "x", "lat": 43.1, "lng": -79.1}
    assert geo.with_coords(exact) is exact


def test_checkout_fills_missing_coords(db: Session, settings: Settings) -> None:
    quote = QuoteService().create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=f"geo-{uuid4().hex[:8]}",
            pickup=AddressInput(formatted="100 King St W, Toronto ON M5X 1A9", lat=43.6488, lng=-79.3817),
            dropoff=AddressInput(formatted="200 Bay St, Toronto ON M5J 2J2", lat=43.6476, lng=-79.3797),
            vehicle_class="sedan_suv",
            weight_kg=5.0,
            scheduled_at=datetime.now(UTC) + timedelta(hours=2),
        ),
        ip_address="127.0.0.1",
    )
    quote.dropoff = {"formatted": "5 Bloor St E, Toronto, ON M4W 1A8"}
    db.flush()
    service.express_checkout(db, settings, _body(quote.id), ip="10.9.0.1")
    db.refresh(quote)
    assert quote.dropoff.get("coords_source") == "fsa"


def test_more_than_five_drops_rejected(db: Session, settings: Settings) -> None:
    quote = _quote(db, settings)
    quote.additional_stops = [{"formatted": f"{i} Queen St W, Toronto ON M5H 2N2"} for i in range(5)]
    db.flush()
    with pytest.raises(ValueError, match="too_many_stops"):
        service.express_checkout(db, settings, _body(quote.id), ip="10.9.0.2")


# ------------------------------------------------------------------ address book + orders + problem


def test_addresses_learned_and_autofill(db: Session, settings: Settings) -> None:
    order, customer = _paid_guest_order(db, settings)
    items = account.suggestions(db, customer, "king")
    assert items and "King" in items[0]["formatted"]
    saved = account.save_address(db, customer, {"formatted": "1 Yonge St, Toronto ON M5E 1E5", "label": "Office"})
    assert saved["saved"] and saved["label"] == "Office" and saved["lat"] is not None
    assert account.list_addresses(db, customer)[0]["label"] == "Office"  # saved first
    account.delete_address(db, customer, saved["id"])
    assert db.get(CustomerAddress, saved["id"]) is None
    with pytest.raises(ValueError, match="address_invalid"):
        account.save_address(db, customer, {"formatted": "x"})


def test_my_orders_and_report_problem(db: Session, settings: Settings) -> None:
    order, customer = _paid_guest_order(db, settings)
    data = account.my_orders(db, settings, customer)
    row = data["orders"][0]
    assert row["tracking_number"] == order.tracking_number and row["can_cancel"] and "/en/track/" in row["track_url"]
    out = account.report_problem_signed(db, settings, order.tracking_number, _token(settings, order), "return", "Wrong size")
    assert out["status"] == "received"
    again = account.report_problem_signed(db, settings, order.tracking_number, _token(settings, order), "return", "x")
    assert again["ticket_id"] == out["ticket_id"]  # idempotent
    db.refresh(order)
    assert order.compliance_metadata["return_requested"] is True
    assert db.query(SupportTicket).filter(SupportTicket.order_id == order.id).count() == 1
    with pytest.raises(ValueError, match="problem_invalid"):
        account.report_problem_owner(db, customer, order.tracking_number, "other", "")


# ------------------------------------------------------------------ rules


def test_risk_first_order_high_value(db: Session, settings: Settings) -> None:
    quote = _quote(db, settings)
    assert rules.flag_order_risk(db, quote, None) == []  # normal price: no flag
    quote.amount_cents = 45_000
    assert rules.flag_order_risk(db, quote, None) == ["first_order_high_value"]
    assert quote.consent["risk_review"] == ["first_order_high_value"]


def test_usual_interval_is_median_gap() -> None:
    now = datetime(2026, 10, 9, tzinfo=UTC)
    dates = [now - timedelta(days=d) for d in (70, 56, 42, 41)]
    assert rules.usual_interval_days(dates) == 14
    assert rules.usual_interval_days(dates[:1]) is None


def test_churn_flag_from_orders(db: Session, settings: Settings) -> None:
    order, customer = _paid_guest_order(db, settings)
    order.created_at = datetime.now(UTC) - timedelta(days=90)
    db.commit()
    c = rules.churn(db, customer.id)
    assert c["flag"] is True and c["status"] == "at_risk"


def test_nudges_drafted_then_require_flag_and_approval(db: Session, settings: Settings, monkeypatch) -> None:
    order, customer = _paid_guest_order(db, settings)
    order.created_at = datetime.now(UTC) - timedelta(days=20)
    db.commit()
    admin360.draft_nudges(db)
    nudge = db.query(ReorderNudge).filter(ReorderNudge.customer_id == customer.id).one()
    assert nudge.status == "draft"
    monkeypatch.setattr(admin360, "nudges_enabled", lambda _db: False)
    with pytest.raises(PermissionError):
        admin360.decide_nudges(db, settings, [nudge.id], approve=True, actor="ops@porterchain.com")
    monkeypatch.setattr(admin360, "nudges_enabled", lambda _db: True)
    admin360.decide_nudges(db, settings, [nudge.id], approve=True, actor="ops@porterchain.com")
    db.refresh(nudge)
    assert nudge.status == "queued" and nudge.approved_by == "ops@porterchain.com"
    admin360.draft_nudges(db)  # idempotent per last order
    assert db.query(ReorderNudge).filter(ReorderNudge.customer_id == customer.id).count() == 1


# ------------------------------------------------------------------ admin 360


def test_admin_360_money_notes_link(db: Session, settings: Settings) -> None:
    order, customer = _paid_guest_order(db, settings)
    o = admin360.overview(db, settings, customer.id)
    assert o["numbers"]["orders"] == 1 and o["consent"]["reorder"]["basis"].startswith("implied")
    assert o["consent"]["deliverable"] is True
    admin360.add_note(db, customer.id, author="ops", body="Prefers side door")
    assert admin360.add_credit(db, customer.id, amount_cents=1500, reason="Late pickup", actor="ops")["balance_cents"] == 1500
    with pytest.raises(ValueError, match="credit_insufficient"):
        admin360.add_credit(db, customer.id, amount_cents=-5000, reason="use", actor="ops")
    refund = admin360.refund_order(db, settings, customer.id, tracking_number=order.tracking_number,
                                   amount_cents=500, reason="Partial goodwill", actor="ops")
    assert refund["refunded_total_cents"] == 500
    with pytest.raises(ValueError, match="refund_amount_invalid"):
        admin360.refund_order(db, settings, customer.id, tracking_number=order.tracking_number,
                              amount_cents=order.amount_cents, reason="too much", actor="ops")
    kinds = {i["kind"] for i in admin360.timeline(db, customer.id)}
    assert {"order", "note", "credit"} <= kinds
    draft = admin360.booking_link_draft(db, settings, customer.id)
    assert draft["sent"] is False and "/book?again=" in draft["link"] and draft["to"] == customer.email


def _matrix_require_module(ctx: AdminContext, module: str) -> None:
    from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS

    if ctx.role not in MODULE_PERMISSIONS.get(module, frozenset()):
        raise PermissionError(f"admin_forbidden:{module}")


def test_admin_routes_and_privacy_role_gate(db: Session, settings: Settings, monkeypatch) -> None:
    monkeypatch.setattr("porterchain_api.routers.customers_admin_360.require_module", _matrix_require_module)
    order, customer = _paid_guest_order(db, settings)
    holder = {"ctx": _admin_ctx("super_admin")}
    app.dependency_overrides[get_admin_context] = lambda: holder["ctx"]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        client = TestClient(app)
        assert client.get(f"/v1/admin/customers/{customer.id}/360").status_code == 200
        r = client.post(f"/v1/admin/customers/{customer.id}/booking-link-draft")
        assert r.status_code == 200 and r.json()["sent"] is False
        holder["ctx"] = _admin_ctx("support")
        job = privacy.open_job(db, customer, reference=f"DSR-{uuid4().hex[:8]}", source="test")
        db.commit()
        assert client.post(f"/v1/admin/customer-care/privacy-jobs/{job.id}/approve", json={}).status_code == 403
    finally:
        app.dependency_overrides.clear()


# ------------------------------------------------------------------ privacy erasure


def test_deletion_request_plans_then_executes_after_approval(db: Session, settings: Settings) -> None:
    from porterchain_api.customer_fast import tokens

    order, customer = _paid_guest_order(db, settings)
    email = customer.email
    prefs = tokens.prefs_token(settings.jwt_secret, customer.id)
    out = service.request_deletion(db, settings, prefs)
    job = db.query(PrivacyDeletionJob).filter(PrivacyDeletionJob.reference == out["reference"]).one()
    assert job.status == "pending_review" and job.plan["blockers"]["active_deliveries"] == [order.tracking_number]
    with pytest.raises(ValueError, match="active_deliveries"):
        privacy.approve_and_execute(db, job.id, reviewer="compliance@porterchain.com")
    order.state = "DELIVERED"
    db.commit()
    done = privacy.approve_and_execute(db, job.id, reviewer="compliance@porterchain.com", note="Verified")
    assert done["status"] == "executed" and done["reviewer"] == "compliance@porterchain.com"
    db.refresh(customer)
    db.refresh(order)
    assert customer.privacy_status == "erased" and customer.full_name is None and customer.phone is None
    assert email not in customer.email and order.dropoff.get("redacted") is True
    assert is_suppressed(db, email=email)
    assert order.amount_cents > 0  # tax record kept


def test_deletion_reject_releases_hold(db: Session, settings: Settings) -> None:
    from porterchain_api.customer_fast import tokens

    _, customer = _paid_guest_order(db, settings)
    out = service.request_deletion(db, settings, tokens.prefs_token(settings.jwt_secret, customer.id))
    job = db.query(PrivacyDeletionJob).filter(PrivacyDeletionJob.reference == out["reference"]).one()
    with pytest.raises(ValueError, match="note_required"):
        privacy.reject(db, job.id, reviewer="c", note="")
    privacy.reject(db, job.id, reviewer="c", note="Duplicate request; customer withdrew")
    db.refresh(customer)
    assert customer.privacy_status is None


# ------------------------------------------------------------------ accounts + FR


def test_pending_guest_adopted_on_first_sign_in(db: Session, settings: Settings) -> None:
    order, customer = _paid_guest_order(db, settings)
    clerk_id = f"user_{uuid4().hex[:10]}"
    adopted = CustomerService().get_or_create_from_clerk(db, clerk_user_id=clerk_id, email=customer.email, phone=None)
    assert adopted.id == customer.id and adopted.clerk_user_id == clerk_id


def test_french_emails(db: Session, settings: Settings) -> None:
    order, customer = _paid_guest_order(db, settings, locale="fr")
    links = service.confirmation_links(db, settings, order, customer)
    assert links["locale"] == "fr" and "/fr/track/" in links["manage_track_url"]
    subject, body, html = render_email("booking_confirmed", {**links, "tracking_number": order.tracking_number})
    assert subject.startswith("C'est réservé") and '<html lang="fr' in html and "Suivre et gérer" in html
    subject, _, html = render_email("fast_send_again", {"locale": "fr", "send_again_url": "https://x", "nudge": True})
    assert subject == "Comme la dernière fois?" and "Réserver à nouveau" in html


def test_signed_in_orders_and_addresses_routes(db: Session, settings: Settings) -> None:
    # Local dev-bypass subject (no SpiceDB tuples by design); bind it to a fresh guest for the test.
    order, customer = _paid_guest_order(db, settings)
    dev = db.query(Customer).filter(Customer.clerk_user_id == "dev_clerk_user").first()
    parked = f"parked:{uuid4().hex[:8]}"
    if dev is not None:
        dev.clerk_user_id = parked
        db.flush()
    original = customer.clerk_user_id
    customer.clerk_user_id = "dev_clerk_user"
    db.commit()
    claims = ClerkClaims(clerk_user_id="dev_clerk_user", email=customer.email, phone=None, clerk_app="customer")

    async def _claims() -> ClerkClaims:
        return claims

    local = settings.model_copy(update={"clerk_dev_bypass": True, "spicedb_required": False})
    app.dependency_overrides[get_clerk_claims] = _claims
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: local
    try:
        client = TestClient(app)
        r = client.get("/v1/customers/me/deliveries")
        assert r.status_code == 200, r.text
        assert r.json()["orders"][0]["tracking_number"] == order.tracking_number
        r = client.post("/v1/customers/me/addresses", json={"formatted": "1 Yonge St, Toronto ON M5E 1E5", "label": "Home"})
        assert r.status_code == 200, r.text
        assert client.get("/v1/customers/me/address-suggestions", params={"q": "yonge"}).json()[0]["label"] == "Home"
        r = client.post(f"/v1/customers/me/orders/{order.tracking_number}/problem", json={"kind": "late"})
        assert r.status_code == 200, r.text
    finally:
        app.dependency_overrides.clear()
        customer.clerk_user_id = original
        db.flush()
        if dev is not None:
            dev.clerk_user_id = "dev_clerk_user"
        db.commit()
