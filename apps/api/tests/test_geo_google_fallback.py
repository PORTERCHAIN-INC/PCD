"""Photon-confident skips Google; Photon-miss hits capped Google Places backup."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from porterchain_api.routers import geo


@pytest.fixture
def app_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PHOTON_URL", "http://photon:2322")
    monkeypatch.setenv("GOOGLE_MAPS_SERVER_API_KEY", "test-server-key")
    monkeypatch.setenv("GEO_GOOGLE_FALLBACK", "1")
    monkeypatch.setenv("GEO_GOOGLE_DAILY_CAP", "300")

    fake = MagicMock()
    fake.get.return_value = None
    fake.setex.return_value = True
    fake.incr.side_effect = lambda *_a, **_k: 1
    fake.expire.return_value = True
    fake.set.return_value = True

    monkeypatch.setattr(geo, "_redis", lambda: fake)
    monkeypatch.setattr(geo, "check_fixed_window", lambda *a, **k: (True, 1, None))
    from porterchain_api import geo_google

    monkeypatch.setattr(geo_google, "_redis", lambda: fake)

    app = FastAPI()
    app.include_router(geo.router)
    return TestClient(app), fake


def test_photon_confident_skips_google(
    app_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _fake = app_client
    calls: dict[str, int] = {"google": 0}

    def scored(q: str, limit: int) -> tuple[list[dict[str, Any]], bool]:
        return (
            [
                {
                    "id": "p1",
                    "main": "8500 Mount Pleasant Way",
                    "secondary": "Milton, ON",
                    "formatted": "8500 Mount Pleasant Way, Milton, ON",
                }
            ],
            True,
        )

    def boom(*_a, **_k):
        calls["google"] += 1
        raise AssertionError("google must not run when Photon is confident")

    monkeypatch.setattr(geo, "photon_search_scored", scored)
    monkeypatch.setattr(geo, "_google_suggest", boom)

    r = client.get("/v1/geo/autocomplete", params={"q": "8500 Mount Pleasant Way Milton"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "photon"
    assert body["results"][0]["main"].startswith("8500")
    assert calls["google"] == 0


def test_photon_miss_hits_google(app_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _fake = app_client

    def scored(q: str, limit: int) -> tuple[list[dict[str, Any]], bool]:
        return ([], False)

    def google_rows(q: str, limit: int) -> list[dict[str, Any]]:
        return [
            {
                "id": "g1",
                "main": "1 Unknown Lane",
                "secondary": "Toronto, ON",
                "formatted": "1 Unknown Lane, Toronto, ON",
            }
        ]

    monkeypatch.setattr(geo, "photon_search_scored", scored)
    monkeypatch.setattr(geo, "_google_suggest", google_rows)

    r = client.get("/v1/geo/autocomplete", params={"q": "1 Unknown Lane Toronto"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "photon+google"
    assert body["results"][0]["main"] == "1 Unknown Lane"


def test_fallback_off_stays_photon_only(
    app_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _fake = app_client
    monkeypatch.setenv("GEO_GOOGLE_FALLBACK", "0")

    def scored(q: str, limit: int) -> tuple[list[dict[str, Any]], bool]:
        return ([], False)

    monkeypatch.setattr(geo, "photon_search_scored", scored)
    monkeypatch.setattr(
        geo,
        "_google_suggest",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("disabled")),
    )

    r = client.get("/v1/geo/autocomplete", params={"q": "1 Unknown Lane Toronto"})
    assert r.status_code == 200
    assert r.json() == {"results": [], "source": "photon"}
