"""Unit tests for construction site access notes (§8.1.6)."""

from porterchain_api.booking_engine.site_access import (
    SITE_ACCESS_DROP_KEY,
    dropoff_address_fields,
    enrich_dropoff,
    extract_site_access_notes,
)


def test_enrich_dropoff_adds_notes():
    drop = {"formatted": "123 Site Rd", "lat": 43.7, "lng": -79.4}
    out = enrich_dropoff(drop, "  Gate 2 · liftgate  ")
    assert out[SITE_ACCESS_DROP_KEY] == "Gate 2 · liftgate"
    assert out["formatted"] == "123 Site Rd"


def test_enrich_dropoff_skips_blank():
    drop = {"formatted": "123 Site Rd"}
    assert enrich_dropoff(drop, "   ") == drop


def test_extract_and_strip_from_address_input():
    drop = {"formatted": "123 Site Rd", SITE_ACCESS_DROP_KEY: "Code 9912"}
    assert extract_site_access_notes(drop) == "Code 9912"
    addr = dropoff_address_fields(drop)
    assert SITE_ACCESS_DROP_KEY not in addr
    assert addr["formatted"] == "123 Site Rd"
