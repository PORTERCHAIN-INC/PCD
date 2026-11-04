"""Declared-value cover at booking / Shopify / quotes (Ravi 2026-10-29, off until G-INS)."""
from porterchain_pricing.declared_value import RULES

from porterchain_api.merchant_engine.booking_validation import declared_value_block


def test_block_only_when_cover_requested():
    assert declared_value_block(None) is None
    assert declared_value_block({"requested": False, "unavailable": ["declared_value_cover_unavailable"]}) is None
    code, msg = declared_value_block({"requested": True, "unavailable": ["declared_value_cover_unavailable"]})
    assert code == "declared_value_cover_unavailable" and "4.41" in msg
    assert declared_value_block({"requested": True, "unavailable": ["declared_value_excluded_goods"]})[0] == (
        "declared_value_excluded_goods")
    assert declared_value_block({"requested": True, "unavailable": []}) is None


def test_flag_off_and_terms():
    assert RULES["enabled"] is False and RULES["flag"] == "G-INS"
    assert (RULES["rate_bps"], RULES["min_cents"], RULES["max_value_cents"]) == (150, 300, 250_000)
    assert RULES["default_liability_cents_per_kg"] == 441 and RULES["proof_of_value_required"] is True
