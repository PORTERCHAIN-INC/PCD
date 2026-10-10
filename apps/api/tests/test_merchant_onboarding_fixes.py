"""Merchant onboarding E2E fixes: text-only CSV rows geocode; API keys work as Bearer tokens."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.auth import merchant_api
from porterchain_api.merchant_engine.bulk_service import MerchantBulkService
from porterchain_api.merchant_engine.import_geocode import GeocodeResult


def _geo(lat: float | None) -> GeocodeResult:
    return GeocodeResult(
        lat=lat, lng=None if lat is None else -79.38, formatted="200 Bay St, Toronto", status="ok",
        confidence=0.9, unit=None, raw="", geocode_query="", issues=[], postal="M5J 2J2",
    )


def test_csv_text_address_is_geocoded() -> None:
    with patch("porterchain_api.merchant_engine.bulk_service.geocode_stop", return_value=_geo(43.65)):
        addr = MerchantBulkService()._address_from_row({"dropoff": "200 Bay St Toronto"}, prefix="dropoff")
    assert (addr.lat, addr.lng, addr.postal) == (43.65, -79.38, "M5J 2J2")


def test_csv_coordinates_skip_geocoding() -> None:
    with patch("porterchain_api.merchant_engine.bulk_service.geocode_stop") as geo:
        addr = MerchantBulkService()._address_from_row(
            {"pickup": "x", "pickup_lat": "43.6", "pickup_lng": "-79.4"}, prefix="pickup"
        )
    geo.assert_not_called()
    assert (addr.lat, addr.lng) == (43.6, -79.4)


def test_csv_address_not_found_keeps_text() -> None:
    with patch("porterchain_api.merchant_engine.bulk_service.geocode_stop", return_value=_geo(None)):
        addr = MerchantBulkService()._address_from_row({"pickup": "nowhere"}, prefix="pickup")
    assert addr.lat is None and addr.formatted == "nowhere"


def test_api_key_accepted_as_bearer_token() -> None:
    merchant = SimpleNamespace(id="m1", status="ACTIVE")
    record = SimpleNamespace(merchant_id="m1")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = merchant
    request = SimpleNamespace(state=SimpleNamespace())
    with (
        patch.object(merchant_api._oauth, "resolve_bearer_token", return_value=None),
        patch.object(merchant_api._api_keys, "authenticate_key", return_value=record) as auth,
    ):
        ctx = merchant_api.get_merchant_api_context(request, db, None, "Bearer pk_live_abc")
    auth.assert_called_once_with(db, "pk_live_abc")
    assert ctx.merchant is merchant
