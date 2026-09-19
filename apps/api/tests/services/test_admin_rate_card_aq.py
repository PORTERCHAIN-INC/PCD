"""AQ — admin writes the full rate card; engine reads pricing_rate_card."""

from __future__ import annotations

from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.merchant_engine.rate_card_view import merchant_rate_card
from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository
from porterchain_pricing.types import GeoPoint, PricingRequest


def test_settings_rate_card_write_reaches_quotes(db, admin_ctx, merchant_ctx) -> None:
    AdminSettingsService().set_config(
        db,
        admin_ctx,
        "pricing_rate_card",
        {"liftgate_cents": 8800, "weight_threshold_kg": 40, "weight_cents_per_kg": 250},
        reason="AQ platform card",
    )
    card = merchant_rate_card(db, merchant_ctx.merchant)
    assert card["liftgate_cents"] == 8800
    assert card["weight"]["threshold_kg"] == 40
    assert card["weight"]["cents_per_kg"] == 250
    assert "driver_flat_per_delivery_cents" not in card
    assert "driver_payout_mode" not in card

    ctx = SqlAlchemyPricingRepository(db).load_context(
        PricingRequest(
            pickup=GeoPoint(lat=43.65, lng=-79.38, postal="M5V 1A1"),
            dropoff=GeoPoint(lat=43.70, lng=-79.40, postal="M2N 1A1"),
            vehicle_class="cargo_van",
            channel="merchant",
            merchant_id=merchant_ctx.merchant.id,
        )
    )
    assert ctx.rate_card is not None
    assert ctx.rate_card.liftgate_cents == 8800


def test_rate_card_save_keeps_driver_payout(db, admin_ctx) -> None:
    svc = AdminSettingsService()
    svc.set_config(
        db,
        admin_ctx,
        "pricing_rate_card",
        {"driver_payout_mode": "percent", "driver_share_pct": 60.0, "liftgate_cents": 1000},
        reason="seed payout",
    )
    svc.set_config(
        db,
        admin_ctx,
        "pricing_rate_card",
        {"liftgate_cents": 2200},
        reason="commercial only",
    )
    stored = svc.get_config_value(db, "pricing_rate_card")
    assert stored["liftgate_cents"] == 2200
    assert stored["driver_payout_mode"] == "percent"
    assert stored["driver_share_pct"] == 60.0
