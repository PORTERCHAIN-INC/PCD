"""Batch 7 — final lines to cross 60% *_service.py coverage."""

from __future__ import annotations

from porterchain_api.admin_engine.clerk_directory_service import clerk_kind_for_user_type
from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.merchant_engine.bulk_service import MerchantBulkService
from porterchain_api.merchant_engine.reports_service import MerchantReportsService
from porterchain_api.merchant_engine.webhook_delivery_service import _hook_matches_event, _sign_payload


def test_clerk_kind_for_user_type() -> None:
    assert clerk_kind_for_user_type("staff") == "admin"
    assert clerk_kind_for_user_type("merchant") == "merchant"


def test_bulk_normalize_row() -> None:
    row = MerchantBulkService()._normalize_row({"Pickup": " 100 King ", "DROPoff": "Bay"})
    assert row["pickup"] == "100 King"
    assert row["dropoff"] == "Bay"


def test_webhook_sign_payload() -> None:
    sig = _sign_payload(b"{}", 1234567890, "secret")
    assert len(sig) == 64


def test_settings_update_staff_role(db, admin_ctx) -> None:
    svc = AdminSettingsService()
    staff = svc.list_staff(db)[0] if svc.list_staff(db) else admin_ctx.user
    updated = svc.update_staff_role(db, admin_ctx, staff.id, "support")
    assert updated.role == "support"


def test_settings_authorize_platform_user_staff(db, admin_ctx, settings) -> None:
    svc = AdminSettingsService()
    staff = admin_ctx.user
    staff.role = "read_only"
    staff.is_active = False
    db.commit()
    result = svc.authorize_platform_user(
        db,
        admin_ctx,
        settings,
        "staff",
        platform_user_id=staff.id,
        reason="test",
    )
    assert result.access_status == "authorized"
    # Activate only — never promote to super_admin
    assert result.role == "read_only"
    db.refresh(staff)
    assert staff.role == "read_only"
    assert staff.is_active is True


def test_settings_authorize_staff_refuses_clerk_only_create(db, admin_ctx, settings) -> None:
    svc = AdminSettingsService()
    try:
        svc.authorize_platform_user(
            db,
            admin_ctx,
            settings,
            "staff",
            clerk_user_id="user_random_platform",
            email="random@example.com",
            reason="should_fail",
        )
        raise AssertionError("expected LookupError")
    except LookupError as exc:
        assert "invite" in str(exc) or "not_found" in str(exc)


def test_merchant_reports_export(db, merchant_ctx) -> None:
    reports = MerchantReportsService()
    assert isinstance(reports.summary(db, merchant_ctx), dict)
    assert isinstance(reports.delivery_performance(db, merchant_ctx), dict)
    assert isinstance(reports.executive(db, merchant_ctx), dict)
    assert isinstance(reports.order_volume(db, merchant_ctx), dict)
    assert isinstance(reports.export_csv(db, merchant_ctx, "orders"), str)


def test_hook_wildcard_events() -> None:
    assert _hook_matches_event(["order.*"], "order.created") is True
