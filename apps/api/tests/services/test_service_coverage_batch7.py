"""Batch 7 — final lines to cross 60% *_service.py coverage."""

from __future__ import annotations

from datetime import UTC, datetime

from porterchain_api.admin_engine.clerk_directory_service import clerk_kind_for_user_type
from porterchain_api.admin_engine.pricing_service import AdminPricingService
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


def test_pricing_publish_tariff(db, admin_ctx) -> None:
    svc = AdminPricingService()
    tariff = svc.create_tariff(
        db,
        admin_ctx,
        name=f"Pub {datetime.now(UTC).timestamp()}",
        tariff_type="retail",
        base_cents=1000,
        per_km_cents=100,
    )
    published = svc.publish_tariff(db, admin_ctx, tariff.id)
    assert published.is_active is True


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
    assert result.role == "super_admin"
    assert "settings" in result.modules
    db.refresh(staff)
    assert staff.role == "super_admin"
    assert staff.is_active is True


def test_merchant_reports_export(db, merchant_ctx) -> None:
    reports = MerchantReportsService()
    assert isinstance(reports.summary(db, merchant_ctx), dict)
    assert isinstance(reports.delivery_performance(db, merchant_ctx), dict)
    assert isinstance(reports.executive(db, merchant_ctx), dict)
    assert isinstance(reports.order_volume(db, merchant_ctx), dict)
    assert isinstance(reports.export_csv(db, merchant_ctx, "orders"), str)


def test_admin_pricing_promotion_and_zone(db, admin_ctx) -> None:
    svc = AdminPricingService()
    code = f"Z{int(datetime.now(UTC).timestamp())}"[:12]
    promo = svc.create_promotion(db, admin_ctx, code=code, discount_percent=5.0, is_active=True)
    assert promo.code == code
    zones = svc.list_zones_enriched(db)
    assert isinstance(zones, list)


def test_hook_wildcard_events() -> None:
    assert _hook_matches_event(["order.*"], "order.created") is True
