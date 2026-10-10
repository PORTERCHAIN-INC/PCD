"""Geocoder misses must never price as a 0 km route (Ingersoll = downtown bug)."""

from __future__ import annotations

import math
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from porterchain_api.integrations import shopify_carrier_rates as rates
from porterchain_api.schemas_merchant import AddressInput

_HUB = (43.6532, -79.3832)
# town, postal, rough straight-line km from downtown Toronto
TOWNS = [
    ("Mississauga", "L5B 3C1", 25),
    ("Oakville", "L6H 0H3", 35),
    ("Oshawa", "L1H 3Z7", 55),
    ("Hamilton", "L8P 4Y5", 60),
    ("Barrie", "L4M 4T5", 85),
    ("Guelph", "N1H 3A1", 75),
    ("Kitchener", "N2G 4G7", 90),
    ("Niagara Falls", "L2E 6X5", 85),
    ("Peterborough", "K9H 3R9", 115),
    ("Ingersoll", "N5C 2V5", 140),
]


def _km(lat: float, lng: float) -> float:
    p1, p2 = math.radians(_HUB[0]), math.radians(lat)
    dp, dl = p2 - p1, math.radians(lng - _HUB[1])
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


@pytest.mark.parametrize(("town", "postal", "km"), TOWNS)
def test_geocoder_miss_falls_back_to_fsa_centroid(town: str, postal: str, km: int) -> None:
    addr = AddressInput(formatted=f"Main St, {town}, ON {postal}", postal=postal)
    miss = SimpleNamespace(lat=None, lng=None, formatted=None)
    with patch("porterchain_api.merchant_engine.import_geocode.geocode_stop", return_value=miss):
        got = rates._ensure_geo(addr)
    assert got.lat is not None and got.lng is not None
    assert abs(_km(got.lat, got.lng) - km) < 35, (town, _km(got.lat, got.lng))


def test_distance_grows_with_town_distance() -> None:
    miss = SimpleNamespace(lat=None, lng=None, formatted=None)
    kms = []
    with patch("porterchain_api.merchant_engine.import_geocode.geocode_stop", return_value=miss):
        for town, postal, _ in (TOWNS[0], TOWNS[4], TOWNS[9]):
            g = rates._ensure_geo(AddressInput(formatted=town, postal=postal))
            kms.append(_km(g.lat, g.lng))
    assert kms == sorted(kms) and kms[0] > 5


def test_unknown_postal_and_geocoder_miss_stays_without_coords() -> None:
    miss = SimpleNamespace(lat=None, lng=None, formatted=None)
    with patch("porterchain_api.merchant_engine.import_geocode.geocode_stop", return_value=miss):
        got = rates._ensure_geo(AddressInput(formatted="nowhere", postal="X0X 0X0"))
    assert got.lat is None
