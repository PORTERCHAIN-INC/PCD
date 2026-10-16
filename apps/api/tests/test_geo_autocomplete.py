"""/v1/geo: free address search (Nominatim), no Google."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from porterchain_api.routers import geo


class _FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, Any] = {}

    def get(self, k):
        return self.kv.get(k)

    def setex(self, k, _ttl, v):
        self.kv[k] = v

    def set(self, k, v, nx=False, px=None):
        if nx and k in self.kv:
            return None
        self.kv[k] = v
        return True


ROWS = [
    {
        "lat": "43.5183",
        "lon": "-79.8774",
        "name": "",
        "display_name": "8500 Main St E, Milton, Ontario",
        "address": {
            "house_number": "8500",
            "road": "Main Street East",
            "town": "Milton",
            "state": "Ontario",
            "postcode": "L9T 0A1",
        },
    },
    {  # Vancouver: outside 150 km, dropped
        "lat": "49.28",
        "lon": "-123.12",
        "display_name": "Main St, Vancouver",
        "address": {
            "road": "Main Street",
            "city": "Vancouver",
            "state": "British Columbia",
        },
    },
]


@pytest.fixture()
def client(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(geo, "_redis", lambda: fake)
    monkeypatch.setattr(geo, "check_fixed_window", lambda *a, **k: (True, 1, None))
    monkeypatch.setattr(geo, "photon_url", lambda: "")
    calls = {"n": 0}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return ROWS

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None, headers=None):
            calls["n"] += 1
            assert "google" not in url
            assert params["bounded"] == "1"
            return _Resp()

    monkeypatch.setattr(geo.httpx, "Client", _Client)
    app = FastAPI()
    app.include_router(geo.router)
    c = TestClient(app)
    c.calls = calls  # type: ignore[attr-defined]
    c.redis = fake  # type: ignore[attr-defined]
    return c


def test_autocomplete_filters_to_service_area_and_caches(client):
    r = client.get("/v1/geo/autocomplete", params={"q": "8500 main st milton"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "nominatim"
    assert len(body["results"]) == 1
    hit = body["results"][0]
    assert hit["main"] == "8500 Main Street East"
    assert "Milton" in hit["secondary"]
    # cached: no second upstream call even though the 1 req/s slot is taken
    r2 = client.get("/v1/geo/autocomplete", params={"q": "8500 MAIN ST MILTON"})
    assert r2.json()["results"] == body["results"]
    assert client.calls["n"] == 1


def test_place_resolves_suggestion_id(client):
    hit = client.get(
        "/v1/geo/autocomplete", params={"q": "8500 main st milton"}
    ).json()["results"][0]
    r = client.get("/v1/geo/place", params={"id": hit["id"]})
    assert r.status_code == 200
    d = r.json()
    assert d["lat"] == pytest.approx(43.5183)
    assert d["postal"] == "L9T 0A1"


def test_busy_slot_returns_empty_not_error(client):
    client.redis.set("pc:geo:nominatim:slot", "1")
    r = client.get("/v1/geo/autocomplete", params={"q": "front st toronto"})
    assert r.status_code == 200 and r.json()["results"] == []


def test_bad_place_id_is_400(client):
    assert client.get("/v1/geo/place", params={"id": "!!!"}).status_code == 400


def test_rate_limited(client, monkeypatch):
    monkeypatch.setattr(geo, "check_fixed_window", lambda *a, **k: (False, 999, None))
    assert client.get("/v1/geo/autocomplete", params={"q": "abc"}).status_code == 429
