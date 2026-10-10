"""Wave 3 — ops-mirror shrink + H3 candidate prefilter (no Fleetbase HTTP)."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from porterchain_api.admin_engine.control_tower.scoring import (
    compute_ranked_suggestions,
)
from porterchain_api.driver_engine.last_known import LastKnown, write_last_known
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

    def eval(self, _script: str, _numkeys: int, *args: str) -> int:
        key = args[0]
        new_epoch = float(args[2])
        current = self.hashes.get(key, {})
        old = current.get("recorded_at_epoch")
        if old and float(old) >= new_epoch:
            return 0
        ver = int(float(current.get("version") or 0)) + 1
        self.hashes[key] = {
            "lat": args[3],
            "lng": args[4],
            "recorded_at": args[5],
            "recorded_at_epoch": args[2],
            "accuracy_m": args[6],
            "heading": args[7],
            "speed_mps": args[8],
            "h3": args[9],
            "version": str(ver),
        }
        return ver

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))


def _driver(**kwargs):
    base = dict(
        id=str(uuid4()),
        full_name="Driver",
        status="APPROVED",
        rating=4.0,
        is_online=True,
        availability="online",
        license_verified=True,
        insurance_verified=True,
        background_check_status="passed",
        medical_transport_certified=False,
        documents={},
        vehicles=[],
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


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


class TestLastKnownH3Cell:
    def test_write_stores_h3_cell(self):
        redis = _FakeLastKnownRedis()
        stored = write_last_known(
            driver_id="drv-h3",
            lat=NEAR[0],
            lng=NEAR[1],
            recorded_at=datetime.now(UTC),
            client=redis,
        )
        assert stored is not None
        assert stored.h3
        assert stored.h3 == cell(*NEAR)


class TestScoringH3Neighbors:
    def test_matrix_only_includes_h3_neighbors(self):
        pickup = {"lat": PICKUP[0], "lng": PICKUP[1]}
        order = SimpleNamespace(
            id="ord-h3",
            pickup=pickup,
            dropoff={},
            compliance_metadata={},
            quote=None,
        )
        db = MagicMock()
        db.get.return_value = order
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.group_by.return_value = q
        near = _driver(id="near", rating=3.0)
        far = _driver(id="far", rating=5.0)
        q.all.side_effect = [[far, near], []]

        known = {
            "near": LastKnown(
                driver_id="near",
                lat=NEAR[0],
                lng=NEAR[1],
                recorded_at=datetime.now(UTC),
                h3=cell(*NEAR),
            ),
            "far": LastKnown(
                driver_id="far",
                lat=FAR[0],
                lng=FAR[1],
                recorded_at=datetime.now(UTC),
                h3=cell(*FAR),
            ),
        }

        maps = MagicMock()
        maps.matrix_durations.return_value = ([[(600, 4200)]], "valhalla")

        with (
            patch(
                "porterchain_api.driver_engine.last_known.read_last_known",
                side_effect=lambda did, **_k: known.get(did),
            ),
        ):
            result = compute_ranked_suggestions(db, "ord-h3", maps=maps)

        assert result.get("drivers") is not None
        sources = maps.matrix_durations.call_args[0][0]
        assert sources == [NEAR]
