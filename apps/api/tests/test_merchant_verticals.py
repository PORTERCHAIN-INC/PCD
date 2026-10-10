"""Merchant vertical constants tests (§8.1.12)."""

from porterchain_api.merchant_engine.verticals import (
    MERCHANT_VERTICAL_SLUGS,
    VERTICAL_INDUSTRY,
    is_valid_merchant_vertical,
)


def test_vertical_slugs_are_website_solution_slugs():
    assert set(MERCHANT_VERTICAL_SLUGS) == {"construction", "medical", "food-beverage", "wholesale", "3pl"}


def test_industry_mapping_present():
    for slug in MERCHANT_VERTICAL_SLUGS:
        assert slug in VERTICAL_INDUSTRY
        assert is_valid_merchant_vertical(slug)
