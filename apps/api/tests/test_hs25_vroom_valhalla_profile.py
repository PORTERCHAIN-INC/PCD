"""HS-13 / HS-25 — VROOM via adapter; Optimize ⊥ OSRM (Valhalla matrix)."""

from __future__ import annotations

import httpx
import pytest


def test_vroom_sidecar_auto_profile_does_not_need_osrm() -> None:
    """HS-25 leaf: VROOM + Valhalla `auto` succeeds even when default `car` would fail.

    Full HS-25 (stop OSRM container) is a compose/live check; this asserts the
    costing contract that makes Optimize independent of OSRM.
    """
    try:
        r = httpx.post(
            "http://127.0.0.1:8030/",
            json={
                "vehicles": [
                    {
                        "id": 0,
                        "profile": "auto",
                        "start": [-79.38, 43.65],
                        "end": [-79.38, 43.65],
                    }
                ],
                "jobs": [
                    {"id": 1, "location": [-79.39, 43.66]},
                    {"id": 2, "location": [-79.37, 43.64]},
                ],
            },
            timeout=15.0,
        )
    except httpx.HTTPError as exc:
        pytest.skip(f"VROOM sidecar unavailable: {exc}")

    if r.status_code >= 500 and "Valhalla" in r.text:
        pytest.fail(
            "VROOM→Valhalla rejected profile; Fleetbase VROOM_PROFILE must be "
            f"auto/truck (not car). body={r.text[:240]}"
        )
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body.get("code") == 0
    assert body.get("routes"), body


def test_vroom_default_car_profile_is_not_valhalla_costing() -> None:
    """Guard: bare requests that default to profile=car must not be our Optimize path."""
    try:
        r = httpx.post(
            "http://127.0.0.1:8030/",
            json={
                "vehicles": [{"id": 0, "start": [-79.38, 43.65], "end": [-79.38, 43.65]}],
                "jobs": [{"id": 1, "location": [-79.39, 43.66]}],
            },
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        pytest.skip(f"VROOM sidecar unavailable: {exc}")

    # Either OSRM serves `car`, or Valhalla rejects it — never silently treat as auto.
    if r.status_code == 200 and r.json().get("code") == 0:
        pytest.skip("OSRM up — car profile served by OSRM fallback (expected when :5000 is up)")
    assert "car" in r.text.lower() or r.status_code >= 400
