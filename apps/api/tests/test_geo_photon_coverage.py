"""Photon coverage: keep typed house numbers on street hits; Canadian postal codes."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from porterchain_api import geo_text
from porterchain_api.routers import geo


def _client(features: list[dict[str, Any]], seen: list[dict[str, Any]]):
    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(dict(req.url.params))
        return httpx.Response(200, json={"features": features})

    real = httpx.Client

    def factory(*a, **kw):
        kw["transport"] = httpx.MockTransport(handler)
        return real(*a, **kw)

    return factory


STREET = {
    "geometry": {"coordinates": [-79.9268, 43.5311]},
    "properties": {
        "name": "Mount Pleasant Way",
        "osm_value": "residential",
        "type": "street",
        "city": "Milton",
        "state": "Ontario",
        "postcode": "L9T 2X7",
        "countrycode": "CA",
    },
}


def test_typed_house_number_kept_on_street_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, Any]] = []
    monkeypatch.setenv("PHOTON_URL", "http://photon:2322")
    monkeypatch.setattr(geo.httpx, "Client", _client([STREET], seen))
    out = geo.photon_search("8500 Mount Pleasant Way Milton", 5)
    assert out[0]["formatted"] == "8500 Mount Pleasant Way, Milton, ON, L9T 2X7"


def test_no_house_number_added_to_a_named_place(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    poi = {
        "geometry": {"coordinates": [-79.64, 43.59]},
        "properties": {
            "name": "Square One",
            "osm_value": "mall",
            "street": "City Centre Dr",
            "housenumber": "100",
            "city": "Mississauga",
            "state": "Ontario",
        },
    }
    seen: list[dict[str, Any]] = []
    monkeypatch.setenv("PHOTON_URL", "http://photon:2322")
    monkeypatch.setattr(geo.httpx, "Client", _client([poi], seen))
    out = geo.photon_search("1 Square One", 5)
    assert out[0]["main"] == "Square One, 100 City Centre Dr"


@pytest.mark.parametrize("raw", ["l9t8w7", "L9T 8W7", " L9T-8W7 "])
def test_postal_normalized_for_photon(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    seen: list[dict[str, Any]] = []
    monkeypatch.setenv("PHOTON_URL", "http://photon:2322")
    monkeypatch.setattr(geo.httpx, "Client", _client([], seen))
    geo.photon_search(raw, 5)
    assert seen[0]["q"] == "L9T 8W7"
    assert geo.normalize_postal(raw) == "L9T 8W7"


def test_house_number_helpers() -> None:
    assert geo_text.typed_house_number("8500 Mount Pleasant Way") == "8500"
    assert geo_text.strip_unit("12-34 King St W Toronto") == "34 King St W Toronto"
    assert geo_text.strip_unit("Unit 5, 345 Main St") == "345 Main St"
    assert geo_text.strip_unit("345 Main St Unit 5, Milton") == "345 Main St, Milton"
    assert geo_text.strip_unit("#210 - 50 Bay St") == "50 Bay St"
    assert geo_text.strip_unit("8500 Mount Pleasant Way") == "8500 Mount Pleasant Way"
    assert geo_text.typed_house_number(geo_text.strip_unit("12-34 King St")) == "34"
    assert geo_text.typed_house_number("Square One") is None
    assert geo.normalize_postal("L9T") is None


def test_postal_fallback_uses_fsa(monkeypatch: pytest.MonkeyPatch) -> None:
    import porterchain_api.marketing_site.fsa_geo as fsa

    monkeypatch.setattr(fsa, "fsa_centroid", lambda v: ("L9T", 43.52, -79.88))
    hit = geo._postal_fallback("l9t8w7")
    assert hit and hit["main"] == "L9T 8W7"
    assert geo._postal_fallback("Main St") is None


def test_relaxed_retry_drops_city(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        q = req.url.params["q"]
        calls.append(q)
        return httpx.Response(
            200, json={"features": [STREET] if q == "8500 Mount Pleasant Way" else []}
        )

    real = httpx.Client
    monkeypatch.setenv("PHOTON_URL", "http://photon:2322")
    monkeypatch.setattr(
        geo.httpx,
        "Client",
        lambda *a, **kw: real(*a, transport=httpx.MockTransport(handler)),
    )
    out = geo.photon_search("8500 Mount Pleasant Way Halton Hills", 5)
    assert calls == [
        "8500 Mount Pleasant Way Halton Hills",
        "8500 Mount Pleasant Way Halton",
        "8500 Mount Pleasant Way",
    ]
    assert out[0]["formatted"].startswith("8500 Mount Pleasant Way")
    assert geo_text.relaxed_queries("L9T 8W7", True) == ["L9T 8W7"]
