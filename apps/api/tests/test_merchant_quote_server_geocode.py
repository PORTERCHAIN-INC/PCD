"""Typed address without lat/lng still quotes: server geocodes (Kaylulu 2026-10-15)."""

from porterchain_api.merchant_engine import import_geocode
from porterchain_api.merchant_engine.booking_flow_service import MerchantBookingFlowService
from porterchain_api.schemas_merchant import AddressInput


def test_missing_coords_geocoded_via_nominatim(monkeypatch):
    monkeypatch.setattr(
        import_geocode, "_nominatim_search", lambda q: {"lat": "43.52", "lon": "-79.84", "display_name": q}
    )
    pickup = AddressInput(formatted="8500 Mount Pleasant Wy, Unit 1, Milton, ON L9T 8W7")
    dropoff = AddressInput(formatted="100 Queen St W, Toronto, ON M5H 2N2")
    errors = MerchantBookingFlowService().validate_addresses(pickup, dropoff)
    assert errors == []
    assert pickup.lat == 43.52 and pickup.lng == -79.84
    assert dropoff.lat is not None


def test_fsa_fallback_when_geocoder_down(monkeypatch):
    monkeypatch.setattr(import_geocode, "_nominatim_search", lambda q: None)
    dropoff = AddressInput(formatted="100 Queen St W, Toronto, ON M5H 2N2")
    pickup = AddressInput(formatted="x", lat=43.5, lng=-79.8)
    errors = MerchantBookingFlowService().validate_addresses(pickup, dropoff)
    assert errors == []
    assert abs(dropoff.lat - 43.65) < 0.1


def test_unresolvable_still_reports_error(monkeypatch):
    monkeypatch.setattr(import_geocode, "_nominatim_search", lambda q: None)
    pickup = AddressInput(formatted="nowhere", lat=43.5, lng=-79.8)
    dropoff = AddressInput(formatted="asdfgh")
    errors = MerchantBookingFlowService().validate_addresses(pickup, dropoff)
    assert errors and errors[0]["error"] == "coordinates_required"


def test_supplied_coords_untouched(monkeypatch):
    called = []
    monkeypatch.setattr(import_geocode, "_nominatim_search", lambda q: called.append(q))
    a = AddressInput(formatted="a", lat=1.0, lng=2.0)
    MerchantBookingFlowService().validate_addresses(a, AddressInput(formatted="b", lat=3.0, lng=4.0))
    assert called == [] and a.lat == 1.0
