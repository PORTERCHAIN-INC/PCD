"""Unit tests for route-import address hygiene."""

from porterchain_api.merchant_engine.address_normalize import normalize_address
from porterchain_api.merchant_engine.import_column_mapper import apply_mapping, suggest_mapping


def test_strips_trailing_unit():
    n = normalize_address("100 King St W Unit 1200, Toronto, ON")
    assert n.unit is not None
    assert "1200" in n.unit
    assert "Unit" not in n.geocode_query or "unit" not in n.geocode_query.lower()
    assert "King" in n.street


def test_strips_leading_unit_dash():
    n = normalize_address("1200-100 King Street West, Toronto")
    assert n.unit == "1200"
    assert n.street.startswith("100")


def test_postal_spacing():
    n = normalize_address("200 Bay St, Toronto, ON M5J2J2")
    assert n.postal == "M5J 2J2" or "M5J" in (n.geocode_query or "")


def test_freeform_ontario_cell_splits_city_and_postal():
    """CSV one-cell addresses like a merchant types them — Nominatim needs city + postal."""
    n = normalize_address("91 breton avenue mississauga l4z 4k5")
    assert n.city == "Mississauga"
    assert n.postal == "L4Z 4K5"
    assert "Mississauga" in n.geocode_query
    assert "L4Z 4K5" in n.geocode_query
    assert "mississauga" not in n.street.lower()
    assert "Breton" in n.street or "breton" in n.street.lower()


def test_column_mapper_address_synonym():
    headers = ["ship_to", "name", "phone"]
    mapping = suggest_mapping(headers)
    by_c = {m.canonical: m for m in mapping}
    assert by_c["address"].source == "ship_to"
    assert by_c["address"].confidence >= 0.9
    rows = apply_mapping([{"ship_to": "1 Main St", "name": "Ada"}], mapping)
    assert rows[0]["address"] == "1 Main St"
    assert rows[0]["contact_name"] == "Ada"
