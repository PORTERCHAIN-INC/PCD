"""Persona HTTP gates — owner / dispatcher / accounting / viewer.

SpiceDB is bypassed with a MODULE_PERMISSIONS matrix patch so these stay unit-fast
and do not duplicate deep SpiceDB suites. Playwright e2e fills the UI layer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.main import app
from porterchain_api.merchant_engine.rbac import MODULE_PERMISSIONS, MerchantContext, modules_for_role
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.routers.merchant._deps import get_db, get_merchant_context


def _ctx(db: Session, role: MerchantRole) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Persona {role.value} {suffix}",
        email=f"persona-{role.value}-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        payment_terms="NET_30",
        profile={},
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{role.value}_{suffix}",
        email=f"user-{role.value}-{suffix}@test.local",
        role=role.value,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=role)


def _matrix_require(ctx: MerchantContext, module: str) -> None:
    """Mirror MODULE_PERMISSIONS UX matrix as HTTP 403 (SpiceDB bypass for P0)."""
    allowed = MODULE_PERMISSIONS.get(module, frozenset())
    if ctx.role not in allowed:
        raise HTTPException(status_code=403, detail=f"merchant_forbidden:{module}")


def _book_body() -> dict:
    return {
        "pickup": {
            "formatted": "100 King St W, Toronto",
            "postal": "M5J 1A1",
            "lat": 43.65,
            "lng": -79.38,
        },
        "dropoff": {
            "formatted": "200 Bay St, Toronto",
            "postal": "M5J 2J2",
            "lat": 43.65,
            "lng": -79.38,
        },
        "vehicle_class": "cargoVan",
        "package_type": "looseParcel",
        "scheduled_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def persona_client(db: Session):
    def _make(role: MerchantRole) -> tuple[TestClient, MerchantContext]:
        ctx = _ctx(db, role)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_merchant_context] = lambda: ctx
        return TestClient(app), ctx

    yield _make
    app.dependency_overrides.clear()
    db.rollback()


@pytest.mark.merchant_p0
@pytest.mark.tc_id("MP-TEAM-002")
@pytest.mark.parametrize(
    ("role", "job", "expect_book", "expect_billing", "expect_keys"),
    [
        (MerchantRole.OWNER, "owner", True, True, True),
        (MerchantRole.OPS, "dispatcher", True, False, False),
        (MerchantRole.FINANCE, "accounting", False, True, False),
        (MerchantRole.READONLY, "viewer", False, False, False),
    ],
)
def test_persona_module_matrix_matches_job(
    role: MerchantRole,
    job: str,
    expect_book: bool,
    expect_billing: bool,
    expect_keys: bool,
) -> None:
    mods = modules_for_role(role)
    assert ("book" in mods) is expect_book
    assert ("billing" in mods) is expect_billing
    assert ("api_keys" in mods) is expect_keys
    book = "book" in mods
    billing = "billing" in mods
    manage = "users" in mods or "api_keys" in mods
    if manage or (book and billing):
        derived = "owner"
    elif book:
        derived = "dispatcher"
    elif billing:
        derived = "accounting"
    else:
        derived = "viewer"
    assert derived == job


@pytest.mark.merchant_p0
@pytest.mark.tc_id("MP-AUTH-003")
def test_viewer_cannot_hit_booking_preview(persona_client) -> None:
    client, _ctx = persona_client(MerchantRole.READONLY)
    with patch("porterchain_api.routers.merchant.dashboard_booking.require_module", _matrix_require):
        res = client.post("/v1/merchant/booking/preview", json=_book_body())
    assert res.status_code == 403


@pytest.mark.merchant_p0
@pytest.mark.tc_id("MP-BOOK-GATE")
def test_dispatcher_passes_book_module_gate(persona_client) -> None:
    client, _ctx = persona_client(MerchantRole.OPS)
    with (
        patch("porterchain_api.routers.merchant.dashboard_booking.require_module", _matrix_require),
        patch(
            "porterchain_api.routers.merchant.dashboard_booking._booking_flow.preview",
            return_value={
                "valid": True,
                "amount_cents": 2500,
                "currency": "cad",
                "vehicle_class": "cargoVan",
                "distance_meters": 1000,
                "estimated_duration_minutes": 15,
            },
        ),
    ):
        res = client.post("/v1/merchant/booking/preview", json=_book_body())
    assert res.status_code != 403


@pytest.mark.merchant_p0
@pytest.mark.tc_id("MP-INT-GATE")
def test_accounting_cannot_open_shopify_connection(persona_client) -> None:
    client, _ctx = persona_client(MerchantRole.FINANCE)
    with patch("porterchain_api.routers.merchant.shopify.require_module", _matrix_require):
        res = client.get("/v1/merchant/shopify")
    assert res.status_code == 403


@pytest.mark.merchant_p0
@pytest.mark.tc_id("MP-INT-OWNER")
def test_owner_can_open_shopify_connection(persona_client) -> None:
    client, _ctx = persona_client(MerchantRole.OWNER)
    with (
        patch("porterchain_api.routers.merchant.shopify.require_module", _matrix_require),
        patch(
            "porterchain_api.routers.merchant.shopify.shopify.connection_payload",
            return_value={"connected": False, "shops": []},
        ),
    ):
        res = client.get("/v1/merchant/shopify")
    assert res.status_code != 403
