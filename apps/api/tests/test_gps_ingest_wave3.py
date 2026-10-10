"""Wave 3 — ops-mirror shrink + H3 candidate prefilter (no Fleetbase HTTP)."""

from __future__ import annotations

import inspect

import pytest

from porterchain_api.admin_engine.control_tower.scoring import (
    compute_ranked_suggestions,
)
from porterchain_api.spatial.h3_index import cell, pick_nearby

pytest.importorskip("h3")

PICKUP = (43.6532, -79.3832)
NEAR = (43.6538, -79.3825)
FAR = (43.8890, -79.2630)  # Markham — well outside res-9 k=3


class _KvRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.kv.get(key)

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.kv[key] = value


class _FakeLastKnownRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}


    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))


class TestH3Neighborhood:
    def test_nearby_included_far_excluded(self):
        near_cell = cell(*NEAR)
        far_cell = cell(*FAR)
        pickup_cell = cell(*PICKUP)
        assert near_cell and far_cell and pickup_cell
        assert near_cell != far_cell
        chosen = pick_nearby(
            PICKUP,
            {
                "near": (*NEAR, near_cell),
                "far": (*FAR, far_cell),
            },
        )
        assert "near" in chosen
        assert "far" not in chosen


class TestScoringNoFleetbaseHttp:
    def test_source_has_no_adapter_http(self):
        src = inspect.getsource(compute_ranked_suggestions)
        assert "get_fleetbase_integration" not in src
        assert "adapter.list_drivers" not in src
        assert "adapter.drivers.get" not in src


