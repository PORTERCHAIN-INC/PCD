"""Merchant vertical constants tests (§8.1.12)."""

from porterchain_api.merchant_engine.verticals import (
    MERCHANT_VERTICAL_SLUGS,
    VERTICAL_INDUSTRY,
    is_valid_merchant_vertical,
)


def test_vertical_slugs_include_website_solution_slugs():
    assert {"construction", "medical", "food-beverage", "wholesale", "3pl"} <= set(MERCHANT_VERTICAL_SLUGS)


def test_gta_small_vehicle_verticals_have_defaults_and_valid_vehicle():
    from porterchain_pricing.catalog import VehicleClass

    from porterchain_api.merchant_engine.verticals import VERTICAL_DEFAULTS, VERTICAL_LABELS, vertical_option

    new = {"automotive", "print-signage", "florist-garden", "office-it", "furniture-appliance",
           "industrial-mro", "legal-documents", "event-rentals"}
    assert new <= set(MERCHANT_VERTICAL_SLUGS)
    ok = {v.value for v in VehicleClass}
    for slug in MERCHANT_VERTICAL_SLUGS:
        assert slug in VERTICAL_LABELS and slug in VERTICAL_DEFAULTS
        assert VERTICAL_DEFAULTS[slug]["vehicle_class"] in ok
        assert vertical_option(slug)["default_vehicle_class"] in ok
    # Phase 0: nothing regulated or alcohol-based is offered as a type.
    for bad in ("cannabis", "alcohol", "liquor", "tobacco", "vape", "firearms"):
        assert not any(bad in s for s in MERCHANT_VERTICAL_SLUGS)


def test_industry_mapping_present():
    for slug in MERCHANT_VERTICAL_SLUGS:
        assert slug in VERTICAL_INDUSTRY
        assert is_valid_merchant_vertical(slug)
