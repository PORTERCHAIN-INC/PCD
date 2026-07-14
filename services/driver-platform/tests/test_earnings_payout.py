"""Driver delivery payout resolution from rate card (pure unit tests)."""

from __future__ import annotations

from porterchain_pricing.rate_card import RateCard, default_rate_card, merge_merchant_overlay


def test_default_flat_matches_legacy_850():
    assert default_rate_card().compute_driver_payout_cents() == 850


def test_percent_respects_minimum():
    card = RateCard(
        driver_payout_mode="percent",
        driver_share_pct=50,
        driver_minimum_payout_cents=2000,
        vehicles=default_rate_card().vehicles,
    )
    assert card.compute_driver_payout_cents(order_amount_cents=1000) == 2000
    assert card.compute_driver_payout_cents(order_amount_cents=10_000) == 5000


def test_merchant_overlay_switches_to_percent():
    system = default_rate_card()
    effective = merge_merchant_overlay(
        system,
        {
            "rate_card": {
                "driver_payout_mode": "percent",
                "driver_share_pct": 60,
                "driver_minimum_payout_cents": 0,
            }
        },
    )
    assert effective.driver_payout_mode == "percent"
    assert effective.compute_driver_payout_cents(order_amount_cents=5000) == 3000
