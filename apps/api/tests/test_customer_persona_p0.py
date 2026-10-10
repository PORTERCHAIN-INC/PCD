"""Customer persona + Admin Customers P0 — catalog docs/CUSTOMER_PERSONA_DEV_TEST_CASES.md.

Covers API auth gates, RBAC, IDOR-adjacent service checks, privacy hold, Quote≡Book
cents, and UI/architecture smoke contracts (Playwright is not in this monorepo).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.customer_admin_service import CustomerAdminService
from porterchain_api.admin_engine.customer_booking_admin_service import (
    CustomerBookingAdminService,
)
from porterchain_api.admin_engine.rbac import (
    MODULE_PERMISSIONS,
    AdminContext,
    parse_admin_role,
)
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk import get_clerk_claims
from porterchain_api.booking_engine.booking_service import BookingService
from porterchain_api.booking_engine.confirmation_service import (
    BookingConfirmationService,
)
from porterchain_api.booking_engine.customer_service import CustomerService
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.booking_models import Customer, Order
from porterchain_api.compliance_engine.privacy_service import PrivacyService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.states import OrderState
from porterchain_api.main import app
from porterchain_api.schemas import (
    AddressInput,
    CreateQuoteRequest,
    WebsitePricingSnapshot,
)


def _matrix_require_module(ctx: AdminContext, module: str) -> None:
    """SpiceDB-free module gate for HTTP tests — still honors MODULE_PERMISSIONS."""
    allowed = MODULE_PERMISSIONS.get(module, frozenset())
    if ctx.role not in allowed:
        raise PermissionError(f"admin_forbidden:{module}")

REPO_ROOT = Path(__file__).resolve().parents[3]
CUSTOMER_SRC = REPO_ROOT / "apps" / "customer" / "src"
ADMIN_SRC = REPO_ROOT / "apps" / "admin" / "src"
MOBILE_CUSTOMER_SRC = REPO_ROOT / "apps" / "mobile-customer" / "src"
API_SRC = REPO_ROOT / "apps" / "api" / "src" / "porterchain_api"


def _read_globs(root: Path, pattern: str) -> str:
    chunks: list[str] = []
    if not root.exists():
        return ""
    for path in root.rglob(pattern):
        if "node_modules" in path.parts or ".venv" in path.parts:
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(chunks)


def _addr_dict() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


def _addr() -> AddressInput:
    return AddressInput(
        formatted="100 King St W, Toronto ON M5X 1A9",
        lat=43.6488,
        lng=-79.3817,
    )


def _dropoff() -> AddressInput:
    return AddressInput(
        formatted="200 Bay St, Toronto ON M5J 2J2",
        lat=43.6476,
        lng=-79.3797,
    )


def _website_pricing() -> WebsitePricingSnapshot:
    return WebsitePricingSnapshot(
        customer_price_cad=48.0,
        driver_payout_cad=32.0,
        platform_margin_cad=16.0,
        distance_km=8.0,
        duration_minutes=24.0,
        engine_vehicle_id="cargo_van",
        breakdown={"base": 12.0, "distance": 36.0},
    )


def _make_customer(
    db: Session,
    *,
    suffix: str | None = None,
    clerk_user_id: str | None = None,
    email: str | None = None,
) -> Customer:
    tag = f"{suffix or 'c'}-{uuid4().hex[:10]}"
    customer = Customer(
        clerk_user_id=clerk_user_id or f"customer_clerk_{tag}",
        email=email or f"customer-{tag}@p0.test",
        phone="+14165550100",
    )
    db.add(customer)
    db.flush()
    return customer


def _make_order(db: Session, *, customer_id: str) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.BOOKED.value,
        customer_id=customer_id,
        amount_cents=2500,
        currency="cad",
        pickup=_addr_dict(),
        dropoff=_addr_dict(),
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def _admin_ctx(role: str = "super_admin") -> AdminContext:
    return AdminContext(
        user=AdminUser(
            clerk_user_id=f"admin-{role}-{uuid4().hex[:6]}",
            email=f"{role}@porterchain.com",
            role=role,
        ),
        role=parse_admin_role(role),
    )


def _customer_settings() -> Settings:
    return Settings(
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt-secret-local",
        spicedb_enabled=False,
        spicedb_use_memory=True,
        spicedb_required=False,
        clerk_dev_bypass=True,
    )


# ---------------------------------------------------------------------------
# Architecture / UI smoke (no Playwright — monorepo uses verify_* + pytest)
# ---------------------------------------------------------------------------


def test_arch_customer_portal_pages_exist() -> None:
    """C-UI inventory: required App Router pages present."""
    required = [
        "app/page.tsx",
        "app/sign-in/[[...sign-in]]/page.tsx",
        "app/sign-up/[[...sign-up]]/page.tsx",
        "app/onboarding/page.tsx",
        "app/dashboard/page.tsx",
        "app/book/page.tsx",
        "app/book/success/page.tsx",
        "app/track/page.tsx",
        "app/track/[trackingNumber]/page.tsx",
        "app/account/page.tsx",
        "app/notifications/page.tsx",
        "lib/api.ts",
        "lib/booking.ts",
        "lib/onboarding.ts",
        "lib/notifications.ts",
        "lib/visitor-session.ts",
    ]
    missing = [rel for rel in required if not (CUSTOMER_SRC / rel).is_file()]
    assert missing == [], f"missing customer portal files: {missing}"


def test_arch_admin_customers_pages_and_tabs() -> None:
    """A-UI inventory: list/detail + tabs + Add order + Create customer modal."""
    list_page = (ADMIN_SRC / "app/(ops)/customers/screen.tsx").read_text(encoding="utf-8")
    detail = (ADMIN_SRC / "components/customers/CustomerDetailClient.tsx").read_text(encoding="utf-8")
    lib = (ADMIN_SRC / "lib/customers.ts").read_text(encoding="utf-8")
    assert "Add customer" in list_page
    assert "CustomerCreateModal" in list_page
    # Five tabs (Customers 360): billing→money, trust/activity/tasks→care, consent+DSR→privacy.
    for tab in ("overview", "orders", "money", "care", "privacy"):
        assert f'"{tab}"' in detail
    assert "CustomerAddOrderModal" in detail
    assert "Send invite" in detail or "customersApi.invite" in lib
    assert (ADMIN_SRC / "components/customers/CustomerAddOrderModal.tsx").is_file()
    assert (ADMIN_SRC / "components/customers/CustomerCreateModal.tsx").is_file()
    assert "/v1/admin/customers" in lib
    assert "invite:" in lib or "invite:" in lib.replace(" ", "")
    assert "customers" in (ADMIN_SRC / "lib/admin-nav.ts").read_text(encoding="utf-8")


def test_arch_customer_ui_no_fleetbase_socketcluster_or_8000() -> None:
    """FB-006 / C-MOB-003: customer web+mobile must not hit Fleetbase/SC/:8000."""
    web = _read_globs(CUSTOMER_SRC, "*.ts") + _read_globs(CUSTOMER_SRC, "*.tsx")
    mobile = _read_globs(MOBILE_CUSTOMER_SRC, "*.ts") + _read_globs(MOBILE_CUSTOMER_SRC, "*.tsx")
    blob = (web + "\n" + mobile).lower()
    for needle in ("fleetbase.io", "socketcluster", "localhost:8000", ":8000/api"):
        assert needle not in blob, f"forbidden reference in customer apps: {needle}"
    pkg_customer = (REPO_ROOT / "apps/customer/package.json").read_text(encoding="utf-8").lower()
    assert "socketcluster" not in pkg_customer


def test_arch_no_google_distance_matrix_on_customer_quote_path() -> None:
    """SPA-003 / C-UI-048: Google Places OK; Distance Matrix forbidden on quote path."""
    targets = [
        API_SRC / "booking_engine",
        API_SRC / "routers" / "quotes.py",
        API_SRC / "routers" / "customers.py",
        CUSTOMER_SRC / "lib" / "booking.ts",
        CUSTOMER_SRC / "components" / "booking",
    ]
    blob = ""
    for t in targets:
        if t.is_file():
            blob += t.read_text(encoding="utf-8", errors="ignore")
        elif t.is_dir():
            blob += _read_globs(t, "*.py") + _read_globs(t, "*.ts") + _read_globs(t, "*.tsx")
    lowered = blob.lower()
    for needle in ("distancematrix", "distance_matrix", "maps.googleapis.com/maps/api/distancematrix"):
        assert needle not in lowered, f"Google Distance Matrix on customer quote path: {needle}"


def test_arch_no_vroom_client_in_api() -> None:
    """SPA-006: VROOM stays behind Fleetbase orchestrator."""
    assert list(API_SRC.rglob("*vroom*")) == []


def test_arch_admin_can_post_create_customer() -> None:
    """API-A-014 / A-UI-005: Admin POST create-customer identity is available."""
    router = (API_SRC / "routers" / "customers_admin.py").read_text(encoding="utf-8")
    assert '@router.post(""' in router
    assert "def create_customer" in router
    assert "AdminCreateCustomerRequest" in router
    # Positive: read + create + phone-book draft
    assert '@router.get("")' in router or '@router.get(""' in router
    assert "booking-drafts" in router
    svc = (API_SRC / "admin_engine" / "customer_admin_service.py").read_text(encoding="utf-8")
    assert "def create_customer" in svc
    assert "pending:" in svc or "send_invite" in svc


def test_arch_openapi_keeps_customer_prefixes() -> None:
    """ARCH-001: OpenAPI census keep-list includes customer surfaces."""
    census = (REPO_ROOT / "scripts" / "openapi_census.py").read_text(encoding="utf-8")
    assert '"/v1/customers"' in census or "'/v1/customers'" in census
    assert "/v1/admin" in census
    assert "/v1/quotes" in census and "/v1/bookings" in census


def test_arch_customer_lib_hits_expected_endpoints() -> None:
    """Portal client contracts for dashboard / book / track / privacy / inbox."""
    api = (CUSTOMER_SRC / "lib/api.ts").read_text(encoding="utf-8")
    booking = (CUSTOMER_SRC / "lib/booking.ts").read_text(encoding="utf-8")
    notif = (CUSTOMER_SRC / "lib/notifications.ts").read_text(encoding="utf-8")
    onboarding = (CUSTOMER_SRC / "lib/onboarding.ts").read_text(encoding="utf-8")
    assert "/v1/customers/me/dashboard" in api
    assert "/v1/customers/me/support" in api
    assert "/v1/customers/me/rebook/" in api
    assert "/v1/customers/me/privacy/export" in api
    assert "/v1/customers/me/privacy/delete-request" in api
    assert "/v1/quotes" in booking and "/v1/bookings" in booking
    assert "/v1/orders/" in booking
    assert "/v1/notifications/inbox" in notif
    assert "/v1/auth/customer/onboarding" in onboarding


# ---------------------------------------------------------------------------
# RBAC / AUTH
# ---------------------------------------------------------------------------


def test_auth_customers_rbac_split() -> None:
    """AUTH-004: customers write ⊂ customers_read."""
    assert "customers" in MODULE_PERMISSIONS
    assert "customers_read" in MODULE_PERMISSIONS
    assert MODULE_PERMISSIONS["customers_read"] >= MODULE_PERMISSIONS["customers"]
    assert parse_admin_role("dispatcher") in MODULE_PERMISSIONS["customers_read"]
    assert parse_admin_role("dispatcher") not in MODULE_PERMISSIONS["customers"]
    assert parse_admin_role("developer") not in MODULE_PERMISSIONS["customers_read"]


# ---------------------------------------------------------------------------
# Engine / privacy / IDOR
# ---------------------------------------------------------------------------


def test_eng_rebook_owned_order_payload(db: Session) -> None:
    """ENG-004 / API-C-007 service layer."""
    customer = _make_customer(db)
    order = _make_order(db, customer_id=customer.id)
    db.commit()
    payload = CustomerService().rebook_payload(db, customer.id, order.id)
    assert payload["source_order_id"] == order.id
    assert payload["tracking_number"] == order.tracking_number
    assert payload["pickup"] == order.pickup


def test_eng_support_rejects_foreign_order(db: Session) -> None:
    """API-C-006 service layer."""
    owner = _make_customer(db, suffix="own")
    other = _make_customer(db, suffix="oth")
    foreign = _make_order(db, customer_id=other.id)
    db.commit()
    with pytest.raises(PermissionError, match="order_not_owned"):
        CustomerService().create_support_ticket(
            db,
            customer_id=owner.id,
            subject="help",
            order_id=foreign.id,
        )


def test_eng_privacy_delete_sets_hold_and_blocks_admin_draft(db: Session, settings: Settings) -> None:
    """API-C-010 / ENG-007 / A-UI-012 backend."""
    customer = _make_customer(db)
    db.commit()
    out = PrivacyService().request_customer_deletion(db, customer, reason="p0_test")
    db.refresh(customer)
    assert out["status"] == "received"
    assert customer.privacy_status == "deletion_hold"
    assert customer.privacy_hold_reference

    export = PrivacyService().export_customer(db, customer)
    assert export["subject_type"] == "customer"
    assert export["customer_id"] == customer.id
    assert "profile" in export and "orders" in export

    ctx = _admin_ctx()
    with pytest.raises(ValueError, match="customer_privacy_hold"):
        CustomerBookingAdminService().create_for_customer(
            db,
            settings,
            ctx,
            customer.id,
            pickup=_addr_dict(),
            dropoff=_addr_dict(),
            vehicle_class="cargo_van",
            scheduled_at=datetime.now(UTC) + timedelta(hours=2),
            schedule_mode="scheduled",
            send_payment_link=False,
        )


def test_eng_admin_stats_list_detail(db: Session) -> None:
    """API-A-001/002/003 service layer."""
    linked = _make_customer(db, suffix="lnk", clerk_user_id=f"user_{uuid4().hex[:10]}")
    orphan = _make_customer(db, suffix="orp", clerk_user_id=f"pending:orphan-{uuid4().hex[:6]}@p0.test")
    db.commit()
    svc = CustomerAdminService()
    stats = svc.stats(db)
    assert stats["total"] >= 2
    assert "clerk_linked" in stats and "orphan" in stats and "dsr_hold" in stats

    rows = svc.list_customers(db, search=linked.email, limit=20)
    assert any(r["id"] == linked.id for r in rows)
    orphans = svc.list_customers(db, clerk_linked=False, limit=50)
    assert any(r["id"] == orphan.id for r in orphans)

    detail = svc.detail(db, linked.id)
    assert detail["id"] == linked.id
    assert detail["clerk_linked"] is True
    with pytest.raises(LookupError, match="customer_not_found"):
        svc.detail(db, "missing-customer-id")


def test_api_b_quote_equals_book_amount_cents(db: Session, settings: Settings) -> None:
    """API-B-009: Quote≡Book amount invariant on retail loop."""
    session_id = f"p0-qeqb-{uuid4().hex[:8]}"
    scheduled = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=3)
    quote = QuoteService().create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=session_id,
            pickup=_addr(),
            dropoff=_dropoff(),
            vehicle_class="cargo_van",
            package_type="looseParcel",
            weight_kg=5.0,
            scheduled_at=scheduled,
            schedule_mode="scheduled",
            website_pricing=_website_pricing(),
        ),
        ip_address="127.0.0.1",
    )
    quote_cents = int(quote.amount_cents)
    quote, _customer, _url = BookingService().start_booking(
        db,
        settings,
        quote_id=quote.id,
        email=f"qeqb-{uuid4().hex[:6]}@p0.test",
        phone="+14165550999",
        clerk_user_id=f"clerk_qeqb_{uuid4().hex[:8]}",
        anonymous_session_id=session_id,
        consent={
            "terms_accepted": True,
            "privacy_accepted": True,
            "dangerous_goods_confirmed": True,
            "consent_at": datetime.now(UTC).isoformat(),
        },
    )
    order = BookingConfirmationService().mock_complete_checkout(db, settings, quote.id)
    assert order.amount_cents == quote_cents
    assert order.tracking_number


# ---------------------------------------------------------------------------
# HTTP — unauth + admin + customer portal
# ---------------------------------------------------------------------------


def test_http_customer_and_admin_routes_require_auth() -> None:
    """API-C-002 / API-A auth gate (bypass off — local CLERK_DEV_BYPASS would otherwise open admin)."""
    locked = Settings(
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt-secret-local",
        spicedb_enabled=False,
        spicedb_use_memory=True,
        spicedb_required=False,
        clerk_dev_bypass=False,
    )
    app.dependency_overrides[get_settings] = lambda: locked
    try:
        client = TestClient(app)
        paths = [
            "/v1/customers/me/dashboard",
            "/v1/customers/me/support",
            "/v1/customers/me/privacy/export",
            "/v1/admin/customers",
            "/v1/admin/customers/stats",
        ]
        for path in paths:
            resp = client.get(path)
            assert resp.status_code in {401, 403, 404, 422}, f"{path} -> {resp.status_code}"
            assert resp.status_code != 200
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def admin_client(db: Session, monkeypatch: pytest.MonkeyPatch):
    holder: dict = {"ctx": _admin_ctx("super_admin")}

    def _ctx() -> AdminContext:
        return holder["ctx"]

    monkeypatch.setattr(
        "porterchain_api.routers.customers_admin.require_module",
        _matrix_require_module,
    )
    app.dependency_overrides[get_admin_context] = _ctx
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app), holder
    app.dependency_overrides.clear()


def test_http_admin_customers_stats_list_detail(admin_client, db: Session) -> None:
    """API-A-001/002/003 HTTP."""
    client, _holder = admin_client
    customer = _make_customer(db)
    db.commit()

    stats = client.get("/v1/admin/customers/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert {"total", "clerk_linked", "orphan", "dsr_hold"} <= set(body)

    listed = client.get("/v1/admin/customers", params={"search": customer.email})
    assert listed.status_code == 200
    assert any(row["id"] == customer.id for row in listed.json())

    detail = client.get(f"/v1/admin/customers/{customer.id}")
    assert detail.status_code == 200
    assert detail.json()["email"] == customer.email

    missing = client.get("/v1/admin/customers/does-not-exist")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "customer_not_found"

    for sub in ("orders", "invoices", "payments", "care"):
        res = client.get(f"/v1/admin/customers/{customer.id}/{sub}")
        assert res.status_code == 200, sub


def test_http_admin_customers_rbac_developer_forbidden(admin_client, db: Session) -> None:
    """API-A-012: developer lacks customers_read."""
    client, holder = admin_client
    holder["ctx"] = _admin_ctx("developer")
    resp = client.get("/v1/admin/customers/stats")
    assert resp.status_code == 403


def test_http_admin_dispatcher_cannot_create_booking_draft(admin_client, db: Session) -> None:
    """A-UI-036 / API-A: customers_read without customers cannot POST drafts."""
    client, holder = admin_client
    customer = _make_customer(db)
    db.commit()
    holder["ctx"] = _admin_ctx("dispatcher")
    resp = client.post(
        f"/v1/admin/customers/{customer.id}/booking-drafts",
        json={
            "pickup": _addr_dict(),
            "dropoff": _addr_dict(),
            "vehicle_class": "cargo_van",
            "scheduled_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            "schedule_mode": "scheduled",
            "send_payment_link": False,
        },
    )
    assert resp.status_code == 403


def test_http_admin_create_customer_orphan(admin_client, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """API-A-014: POST creates orphan retail customer."""
    monkeypatch.setattr(
        "porterchain_api.admin_engine.customer_admin_mutations.is_clerk_secret_configured",
        lambda *a, **k: False,
    )
    client, _holder = admin_client
    email = f"mint-{uuid4().hex[:8]}@p0.test"
    resp = client.post(
        "/v1/admin/customers",
        json={"email": email, "full_name": "Minted P0", "send_invite": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == email
    assert body["created"] is True
    assert body["clerk_linked"] is False
    assert body["identity_status"] == "orphan"
    assert body["id"]

    listed = client.get("/v1/admin/customers", params={"search": email})
    assert listed.status_code == 200
    assert any(row["id"] == body["id"] for row in listed.json())


def test_http_admin_create_customer_conflict_when_linked(
    admin_client, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """API-A-014: 409 when email already Clerk-linked."""
    monkeypatch.setattr(
        "porterchain_api.admin_engine.customer_admin_mutations.is_clerk_secret_configured",
        lambda *a, **k: False,
    )
    client, _holder = admin_client
    email = f"linked-{uuid4().hex[:8]}@p0.test"
    _make_customer(db, suffix="lnk", clerk_user_id=f"user_{uuid4().hex[:10]}", email=email)
    db.commit()

    resp = client.post(
        "/v1/admin/customers",
        json={"email": email, "send_invite": False},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "customer_email_exists"


def test_http_admin_create_customer_invite_requires_clerk(
    admin_client, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """API-A-014: send_invite without Clerk secrets → 400 clerk_not_configured."""
    monkeypatch.setattr(
        "porterchain_api.admin_engine.customer_admin_mutations.is_clerk_secret_configured",
        lambda *a, **k: False,
    )
    client, _holder = admin_client
    resp = client.post(
        "/v1/admin/customers",
        json={"email": f"invite-{uuid4().hex[:8]}@p0.test", "send_invite": True},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "clerk_not_configured"


def test_http_admin_dispatcher_cannot_create_customer(admin_client, db: Session) -> None:
    """API-A-014 / AUTH-004: customers_read without customers cannot POST create."""
    client, holder = admin_client
    holder["ctx"] = _admin_ctx("dispatcher")
    resp = client.post(
        "/v1/admin/customers",
        json={"email": f"disp-{uuid4().hex[:6]}@p0.test", "send_invite": False},
    )
    assert resp.status_code == 403


def test_http_admin_invite_orphan_customer(admin_client, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """API-A-014 companion: POST /{id}/invite for orphan rows."""
    from porterchain_api.auth.clerk_client import ClerkInviteResult

    client, _holder = admin_client
    customer = _make_customer(db, suffix="inv", clerk_user_id=f"pending:inv-{uuid4().hex[:6]}@p0.test")
    db.commit()

    class _FakeClerk:
        def invite_user(self, email, *, redirect_url, public_metadata):
            return ClerkInviteResult(action="invited", clerk_invitation_id="inv_test")

    monkeypatch.setattr(
        "porterchain_api.auth.invitation_service.is_clerk_secret_configured",
        lambda *a, **k: True,
    )
    monkeypatch.setattr(
        "porterchain_api.auth.invitation_service.clerk_client_for_kind",
        lambda *a, **k: _FakeClerk(),
    )
    monkeypatch.setattr(
        "porterchain_api.admin_engine.customer_admin_mutations.is_clerk_secret_configured",
        lambda *a, **k: True,
    )

    resp = client.post(f"/v1/admin/customers/{customer.id}/invite")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == customer.id
    assert body["clerk_action"] == "invited"


@pytest.fixture
def customer_client(db: Session):
    settings = _customer_settings()
    email = "dev-customer@p0.test"
    claims = ClerkClaims(
        clerk_user_id="dev_clerk_user",
        email=email,
        phone="+14165550001",
        clerk_app="customer",
    )
    # Keep email aligned with claims — seed DBs often already bind dev_clerk_user.
    existing = db.query(Customer).filter(Customer.clerk_user_id == "dev_clerk_user").first()
    if existing is None:
        db.add(
            Customer(
                clerk_user_id="dev_clerk_user",
                email=email,
                phone="+14165550001",
            )
        )
    else:
        existing.email = email
        existing.phone = existing.phone or "+14165550001"
    db.commit()

    async def _claims() -> ClerkClaims:
        return claims

    app.dependency_overrides[get_clerk_claims] = _claims
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app), settings
    app.dependency_overrides.clear()


def test_http_customer_dashboard_support_rebook_privacy(customer_client, db: Session) -> None:
    """API-C-001/004/005/007/009/010 HTTP happy path."""
    client, _settings = customer_client
    customer = db.query(Customer).filter(Customer.clerk_user_id == "dev_clerk_user").one()
    order = _make_order(db, customer_id=customer.id)
    db.commit()

    dash = client.get("/v1/customers/me/dashboard")
    assert dash.status_code == 200, dash.text
    assert "orders" in dash.json()

    created = client.post(
        "/v1/customers/me/support",
        json={"subject": "P0 help", "description": "need ETA", "order_id": order.id},
        headers={"Idempotency-Key": f"p0-support-{order.id}"},
    )
    assert created.status_code == 200, created.text
    ticket_id = created.json()["ticket_id"]

    replay = client.post(
        "/v1/customers/me/support",
        json={"subject": "P0 help", "description": "need ETA", "order_id": order.id},
        headers={"Idempotency-Key": f"p0-support-{order.id}"},
    )
    assert replay.status_code == 200
    assert replay.json()["ticket_id"] == ticket_id

    listed = client.get("/v1/customers/me/support")
    assert listed.status_code == 200
    assert any(t["ticket_id"] == ticket_id for t in listed.json())

    rebook = client.post(f"/v1/customers/me/rebook/{order.id}")
    assert rebook.status_code == 200
    assert rebook.json()["source_order_id"] == order.id

    foreign = _make_customer(db, suffix="fx")
    foreign_order = _make_order(db, customer_id=foreign.id)
    db.commit()
    stolen = client.post(f"/v1/customers/me/rebook/{foreign_order.id}")
    assert stolen.status_code == 404

    export = client.get("/v1/customers/me/privacy/export")
    assert export.status_code == 200
    assert export.json()["customer_id"] == customer.id

    delete_req = client.post("/v1/customers/me/privacy/delete-request")
    assert delete_req.status_code == 200
    assert delete_req.json()["status"] == "received"
    db.refresh(customer)
    assert customer.privacy_status == "deletion_hold"


def test_http_public_track_returns_order(db: Session, settings: Settings) -> None:
    """API-B-007 / C-UI-051: public track without auth."""
    customer = _make_customer(db)
    order = _make_order(db, customer_id=customer.id)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        client = TestClient(app)
        res = client.get(f"/v1/orders/{order.tracking_number}")
        assert res.status_code == 200, res.text
        payload = res.json()
        assert order.tracking_number in str(payload) or payload.get("tracking_number") == order.tracking_number
    finally:
        app.dependency_overrides.clear()


def test_customer_router_surface_matches_catalog() -> None:
    """Router verbs stay aligned with the P0 catalog."""
    text = (API_SRC / "routers" / "customers.py").read_text(encoding="utf-8")
    for route in (
        '/me/dashboard',
        '/me/support',
        '/me/rebook/{order_id}',
        '/me/privacy/export',
        '/me/privacy/delete-request',
    ):
        assert route in text
    admin = (API_SRC / "routers" / "customers_admin.py").read_text(encoding="utf-8")
    assert re.search(r'@router\.get\(\s*"/stats"', admin)
    assert "booking-drafts" in admin
    assert "send-payment-link" in admin
