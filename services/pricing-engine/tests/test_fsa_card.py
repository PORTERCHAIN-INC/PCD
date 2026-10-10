import pytest
from porterchain_pricing.fsa_card import (
    band_cents,
    default_fsa_card,
    drop_price_cents,
    normalize_fsa_card,
)


def test_bands_round_up_to_clean_prices() -> None:
    card = default_fsa_card()
    assert band_cents(1840, card) == 1900
    assert band_cents(1900, card) == 1900
    assert band_cents(4300, card) == 4500
    assert band_cents(4000, card) == 4000


def test_drop_price_uses_km_minutes_minimum_and_downtown() -> None:
    card = default_fsa_card()
    # 1200 + 85*10 + 30*15 = 2500 → $25
    assert drop_price_cents(10, 15, "M6P", card) == 2500
    # same trip into the core: +20% = 3000
    assert drop_price_cents(10, 15, "M5V", card) == 3000
    # very short hop is held at the minimum
    assert drop_price_cents(0.5, 2, "M6P", card) == 1800
    # 40 km / 45 min = 1200+3400+1350 = 5950 → $5 band → 6000
    assert drop_price_cents(40, 45, "L4Z", card) == 6000


def test_settings_overlay_is_validated() -> None:
    card = normalize_fsa_card({"per_km_cents": 100, "tier_columns": [10, 5, 5], "unknown": 1})
    assert card["per_km_cents"] == 100 and card["tier_columns"] == [5, 10]
    assert "unknown" not in card
    with pytest.raises(ValueError, match="fsa_card_invalid:base_cents"):
        normalize_fsa_card({"base_cents": -1})
    with pytest.raises(ValueError, match="fsa_card_invalid:bands"):
        normalize_fsa_card({"bands": [{"below_cents": 100, "step_cents": 50}]})


def test_card_radius_defaults_to_service_radius_and_is_editable() -> None:
    from porterchain_pricing.fsa_card import default_fsa_card, normalize_fsa_card

    assert default_fsa_card()["radius_km"] == 150.0
    assert normalize_fsa_card({"radius_km": 90})["radius_km"] == 90
