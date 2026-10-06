"""Wave 4 Batch G: nav modules, claim driver snapshot, privacy export, vehicle attach."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import modules_for_role
from porterchain_api.support_engine.claims_constants import claim_meta, set_claim_meta


def test_readonly_modules_exclude_book() -> None:
    mods = modules_for_role(MerchantRole.READONLY)
    assert "dashboard" in mods
    assert "book" not in mods
    assert "api_keys" not in mods


def test_claim_meta_snapshots_driver() -> None:
    claim = SimpleNamespace(evidence={})
    set_claim_meta(claim, priority="high", driver_id="drv-9")
    assert claim_meta(claim)["driver_id"] == "drv-9"
    assert claim_meta(claim)["priority"] == "high"


def test_incidents_includes_support_tickets() -> None:
    from porterchain_api.admin_engine.driver360_service import Driver360Service

    ticket = SimpleNamespace(
        id="t1",
        subject="Help",
        status="open",
        order_id=None,
        created_at=None,
        driver_id="d1",
    )
    db = MagicMock()
    chain = MagicMock()
    # Universal chain: join/filter/order_by/limit/all
    chain.join.return_value = chain
    chain.filter.return_value = chain
    chain.order_by.return_value = chain
    chain.limit.return_value = chain
    chain.all.side_effect = [[], [], [], [ticket]]
    db.query.return_value = chain

    out = Driver360Service().incidents(db, "d1")
    assert out["support_tickets"][0]["id"] == "t1"


def test_privacy_export_includes_payments_and_tickets() -> None:
    from porterchain_api.compliance_engine.privacy_service import PrivacyService

    customer = SimpleNamespace(
        id="c1",
        email="a@b.com",
        phone=None,
        customer_reference="CUST-1",
        stripe_customer_id="cus_x",
        created_at=None,
        clerk_user_id="user_x",
    )
    db = MagicMock()
    empty = MagicMock()
    empty.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    db.query.return_value = empty

    with patch(
        "porterchain_api.notification_engine.user_settings.UserSettingsService.get",
        return_value=None,
    ), patch(
        "porterchain_api.notification_engine.user_settings.UserSettingsService.to_dict",
        return_value={"email_enabled": True},
    ):
        out = PrivacyService().export_customer(db, customer)

    assert "payments" in out
    assert "support_tickets" in out
    assert "notification_preferences" in out
    assert out["profile"]["stripe_customer_id"] == "cus_x"


def test_attach_vehicle_stays_on_porterchain() -> None:
    from porterchain_api.admin_engine.driver_service import AdminDriverService

    svc = AdminDriverService()
    driver = SimpleNamespace(id="d1")
    db = MagicMock()
    ctx = SimpleNamespace(user=SimpleNamespace(id="a1"))
    settings = SimpleNamespace()
    svc._get_or_raise = MagicMock(return_value=driver)  # type: ignore[method-assign]
    svc._audit = MagicMock()  # type: ignore[method-assign]
    db.query.return_value.filter.return_value.first.return_value = None

    vehicle = svc.attach_vehicle(
        db,
        ctx,
        "d1",
        vehicle_class="cargo_van",
        plate_number=" ABC123 ",
        settings=settings,
    )
    assert vehicle.plate_number == "ABC123"
    assert vehicle.is_active is True
    assert not hasattr(svc, "_fleetbase")
