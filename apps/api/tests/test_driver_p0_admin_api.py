"""P0 — admin /v1/admin/drivers contracts (API-A-*)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.driver360_service import Driver360Service
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.main import app


@pytest.mark.driver_p0
def test_api_a_02_lifecycle_reject_rehire_roundtrip() -> None:
    """API-A-02 — reject → rehire → pending (unit, mirrors catalog)."""
    from porterchain_api.admin_engine.driver_service import AdminDriverService

    driver = SimpleNamespace(
        id="d-admin-p0",
        status=DriverStatus.PENDING.value,
        clerk_user_id="user_admin_p0",
        vehicles=[],
        fleetbase_driver_id=None,
        is_online=True,
        availability="idle",
    )
    svc = AdminDriverService()
    svc._get_or_raise = MagicMock(return_value=driver)  # type: ignore[method-assign]
    svc._audit = MagicMock()  # type: ignore[method-assign]
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))
    db = MagicMock()

    with patch("porterchain_api.admin_engine.driver_service.emit_event"), patch(
        "porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation",
    ):
        out, _ = svc.reject_driver(db, ctx, driver.id, None)
        assert out.status == DriverStatus.REJECTED.value
        out = svc.rehire_driver(db, ctx, driver.id)
        assert out.status == DriverStatus.PENDING.value


@pytest.mark.driver_p0
def test_api_a_01_admin_drivers_openapi_surface() -> None:
    paths = set(app.openapi().get("paths", {}))
    required = {
        "/v1/admin/drivers",
        "/v1/admin/drivers/facets",
        "/v1/admin/drivers/stats",
        "/v1/admin/drivers/{driver_id}",
        "/v1/admin/drivers/{driver_id}/approve",
        "/v1/admin/drivers/{driver_id}/suspend",
        "/v1/admin/drivers/{driver_id}/reject",
        "/v1/admin/drivers/{driver_id}/rehire",
        "/v1/admin/drivers/{driver_id}/invite",
        "/v1/admin/drivers/{driver_id}/action",
        "/v1/admin/drivers/{driver_id}/documents",
        "/v1/admin/drivers/{driver_id}/vehicles",
        "/v1/admin/drivers/{driver_id}/payouts",
        "/v1/admin/drivers/{driver_id}/timeline",
        "/v1/admin/drivers/{driver_id}/analytics",
    }
    missing = sorted(p for p in required if p not in paths)
    assert not missing, f"missing admin driver OpenAPI paths: {missing}"


@pytest.mark.driver_p0
def test_api_a_01_unauthenticated_list_not_200() -> None:
    """API-A-01 / AUTH-04 — anonymous list rejected when bypass is off."""
    from porterchain_api.config import Settings, get_settings

    settings = Settings(
        app_env="local",
        clerk_dev_bypass=False,
        stripe_mock=True,
        jwt_secret="test-jwt-secret-local",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        client = TestClient(app)
        r = client.get("/v1/admin/drivers")
        assert r.status_code in {401, 403, 422}, r.text[:300]
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.driver_p0
def test_api_a_04_driver360_board_envelopes() -> None:
    """API-A-04 — Driver360Service facets/stats/orders envelopes."""
    svc = Driver360Service()
    db = MagicMock()

    # facets: three group_by().all() chains
    grouped = MagicMock()
    db.query.return_value.group_by.return_value = grouped
    grouped.all.side_effect = [
        [("APPROVED", 2), ("PENDING", 1)],
        [("clear", 2)],
        [("van", 1)],
    ]
    facets = svc.facets(db)
    assert facets["statuses"] == [{"value": "APPROVED", "count": 2}, {"value": "PENDING", "count": 1}]
    assert facets["background_check"] == [{"value": "clear", "count": 2}]
    assert facets["vehicle_types"] == [{"value": "van", "count": 1}]

    q = MagicMock()
    db.query.return_value = q
    q.scalar.return_value = 10
    q.filter.return_value.scalar.return_value = 3
    stats = svc.stats(db)
    assert stats["total"] == 10
    assert stats["approved"] == 3
    assert stats["pending"] == 3
    assert stats["suspended"] == 3
    assert stats["pending_payout_cents"] == 3
    assert "online" not in stats

    order_q = MagicMock()
    db.query.return_value = order_q
    order_q.filter.return_value = order_q
    order_q.order_by.return_value = order_q
    order_q.count.return_value = 0
    order_q.offset.return_value.limit.return_value.all.return_value = []
    page = svc.orders(db, "d-360")
    assert page == {"items": [], "total": 0, "limit": 50, "offset": 0}


@pytest.mark.driver_p0
def test_auth_06_invite_existing_driver_requires_clerk() -> None:
    """AUTH-06 — invite_existing_driver fails closed when Clerk secret missing."""
    settings = SimpleNamespace(clerk_driver_secret_key="", clerk_driver_jwks_url="")
    driver = SimpleNamespace(id="d1", email="driver@example.com", full_name="D")
    with patch(
        "porterchain_api.auth.invitation_service.is_clerk_secret_configured",
        return_value=False,
    ):
        with pytest.raises(RuntimeError, match="clerk_not_configured"):
            InvitationService().invite_existing_driver(MagicMock(), None, settings, driver)
