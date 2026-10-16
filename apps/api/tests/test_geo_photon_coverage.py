"""Photon coverage: keep typed house numbers on street hits; Canadian postal codes."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from porterchain_api import geo_photon, geo_text
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
            200,
            json={
                "features": [STREET] if q == "8500 Mount Pleasant Way Milton" else []
            },
        )

    real = httpx.Client
    monkeypatch.setenv("PHOTON_URL", "http://photon:2322")
    monkeypatch.setattr(
        geo.httpx,
        "Client",
        lambda *a, **kw: real(*a, transport=httpx.MockTransport(handler)),
    )
    out = geo.photon_search("8500 Mount Pleasant Way Milton Ontario Canada", 5)
    assert calls[0] == "8500 Mount Pleasant Way Milton Ontario Canada"
    assert calls[-1] == "8500 Mount Pleasant Way Milton"
    assert out[0]["formatted"].startswith("8500 Mount Pleasant Way")
    assert geo_text.relaxed_queries("L9T 8W7", True) == ["L9T 8W7"]


def test_short_forms_and_city_split() -> None:
    assert (
        geo_text.expand_short_forms("1880 Steeles Ave W") == "1880 Steeles Avenue West"
    )
    assert geo_text.expand_short_forms("12 St Clair Ave E") == "12 St Clair Avenue East"
    assert geo_text.split_city("1880 Steeles Avenue West North York") == (
        "1880 Steeles Avenue West",
        "north york",
    )
    assert geo_text.split_city("8500 Mount Pleasant Way Milton, ON")[1] == "milton"


def test_number_not_invented_on_far_apart_segments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def seg(lng: float) -> dict[str, Any]:
        return {
            "geometry": {"coordinates": [lng, 43.79]},
            "properties": {
                "name": "Steeles Avenue West",
                "osm_value": "secondary",
                "type": "street",
                "city": "Toronto",
                "district": "North York",
                "state": "Ontario",
            },
        }

    seen: list[dict[str, Any]] = []
    monkeypatch.setenv("PHOTON_URL", "http://photon:2322")
    monkeypatch.setattr(geo.httpx, "Client", _client([seg(-79.43), seg(-79.54)], seen))
    out, confident = geo.photon_search_scored("1880 Steeles Ave W North York", 5)
    assert seen[0]["q"] == "1880 Steeles Avenue West North York"
    assert not confident
    assert all(not r["formatted"].startswith("1880") for r in out)
    assert "North York, Toronto" in out[0]["formatted"]


def test_google_fallback_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    from porterchain_api import geo_google

    class R:
        n = 0

        def incr(self, _k):
            R.n += 1
            return R.n

        def expire(self, *_a):
            return True

    monkeypatch.setenv("GOOGLE_MAPS_SERVER_API_KEY", "k")
    monkeypatch.setenv("GEO_GOOGLE_FALLBACK", "1")
    monkeypatch.setenv("GEO_GOOGLE_DAILY_CAP", "1")
    monkeypatch.setattr(geo_google, "_redis", lambda: R())
    assert geo_google._take_slot() is True
    assert geo_google._take_slot() is False
    monkeypatch.setenv("GEO_GOOGLE_FALLBACK", "0")
    assert geo_google.suggest("x", 3, geo.BBOX) == []


def test_leading_city_moved_last() -> None:
    assert (
        geo_text.lead_city_last("Milton 8500 Mount Pleasant Way")
        == "8500 Mount Pleasant Way Milton"
    )


def test_postal_must_fit_city(monkeypatch: pytest.MonkeyPatch) -> None:
    def hit(pc: str, lng: float, name: str | None = None) -> dict[str, Any]:
        return {
            "geometry": {"coordinates": [lng, 43.786]},
            "properties": {
                "housenumber": "1881",
                "street": "Steeles Avenue West",
                "name": name,
                "postcode": pc,
                "city": "Toronto",
                "district": "North York",
                "state": "Ontario",
                "osm_value": "house",
            },
        }

    seen: list[dict[str, Any]] = []
    monkeypatch.setenv("PHOTON_URL", "http://photon:2322")
    feats = [
        hit("L4J 4H6", -79.4695),
        hit("M3H 5Y4", -79.4687),
        hit("M3H 5Y4", -79.4687, "Shoppers"),
    ]
    monkeypatch.setattr(geo.httpx, "Client", _client(feats, seen))
    out, confident = geo.photon_search_scored("1881 Steeles Ave W", 5)
    assert confident
    assert out[0]["formatted"].endswith("M3H 5Y4")
    assert not any("L4J" in r["formatted"] for r in out)
    assert geo_photon.postal_fits({"city": "Vaughan", "postcode": "L4J 4H6"})
    assert not geo_photon.postal_fits({"city": "Milton", "postcode": "M3H 5Y4"})


def test_trailing_postal_and_unknown_town_dont_break_exact_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def house(num: str, street: str, city: str, pc: str) -> dict[str, Any]:
        return {
            "geometry": {"coordinates": [-79.45, 43.67]},
            "properties": {
                "housenumber": num,
                "street": street,
                "city": city,
                "state": "Ontario",
                "postcode": pc,
                "osm_value": "house",
                "countrycode": "CA",
            },
        }

    seen: list[dict[str, Any]] = []
    monkeypatch.setenv("PHOTON_URL", "http://photon:2322")
    monkeypatch.setattr(
        geo.httpx, "Client", _client([house("7", "Connolly Street", "Toronto", "M6N 4Y5")], seen)
    )
    out, confident = geo.photon_search_scored("7 Connolly St, Toronto M6N 4Y5", 5)
    assert confident and out[0]["formatted"].startswith("7 Connolly Street")
    monkeypatch.undo()
    monkeypatch.setenv("PHOTON_URL", "http://photon:2322")
    monkeypatch.setattr(
        geo.httpx, "Client", _client([house("42", "Willoughby Place", "Clarington", "L1C 0W4")], seen)
    )
    out, confident = geo.photon_search_scored("42 Willoughby Pl, Bowmanville", 5)
    assert confident and out[0]["formatted"].startswith("42 Willoughby Place")
    assert geo_text.split_city("7 Connolly Street, Toronto M6N 4Y5") == ("7 Connolly Street", "toronto")


def test_street_loose_match() -> None:
    m = geo_photon.street_loose_match
    assert m("willoughby place, bowmanville", "willoughby place")
    assert m("woody vine way", "woody vineway")
    assert not m("king street east", "king street")
    assert not m("kingston road", "king street")
