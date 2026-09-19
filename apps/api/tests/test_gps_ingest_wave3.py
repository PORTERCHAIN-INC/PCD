"""Wave 3 — ops-mirror shrink + H3 candidate prefilter (no Fleetbase HTTP)."""

from __future__ import annotations

import inspect
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from porterchain_api.admin_engine.control_tower.scoring import compute_ranked_suggestions
from porterchain_api.driver_engine.last_known import LastKnown, write_last_known
from porterchain_api.fleetbase_engine import ops_mirror
from porterchain_api.fleetbase_engine.ops_mirror_refresh import OpsMirrorRefreshService
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
            "fleetbase_driver_id": args[9],
            "h3": args[10],
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
        fleetbase_driver_id=f"fb-{uuid4().hex[:8]}",
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


class TestLastKnownH3:
    def test_write_stores_h3_cell(self):
        redis = _FakeLastKnownRedis()
        stored = write_last_known(
            driver_id="drv-h3",
            lat=NEAR[0],
            lng=NEAR[1],
            recorded_at=datetime.now(UTC),
            fleetbase_driver_id="fb-h3",
            client=redis,
        )
        assert stored is not None
        assert stored.h3
        assert stored.h3 == cell(*NEAR)


class TestOpsMirrorPerDriver:
    def test_driver_by_fleetbase_id_prefers_per_driver_key(self):
        fake = _KvRedis()
        with patch.object(ops_mirror, "_client", return_value=fake):
            ops_mirror.write_drivers(
                [{"id": "fb-1", "online": False, "location": {"lat": 1.0, "lng": 1.0}}]
            )
            ops_mirror.overlay_driver_location(
                "fb-1",
                lat=43.65,
                lng=-79.38,
                recorded_at=datetime.now(UTC),
            )
            row = ops_mirror.driver_by_fleetbase_id("fb-1")
        assert row is not None
        loc = row.get("location") or {}
        assert loc.get("lat") == 43.65
        assert loc.get("lng") == -79.38
        assert row.get("location_source") == "ingest"

    def test_roster_write_does_not_clobber_newer_ingest(self):
        fake = _KvRedis()
        stamp = datetime.now(UTC)
        with patch.object(ops_mirror, "_client", return_value=fake):
            ops_mirror.overlay_driver_location(
                "fb-keep",
                lat=43.65,
                lng=-79.38,
                recorded_at=stamp,
            )
            ops_mirror.write_drivers(
                [{"id": "fb-keep", "online": True, "location": {"lat": 0.1, "lng": 0.1}}]
            )
            row = ops_mirror.driver_by_fleetbase_id("fb-keep")
        assert row is not None
        loc = row.get("location") or {}
        assert loc.get("lat") == 43.65
        assert row.get("online") is True


class TestOpsMirrorRefreshSkip:
    def test_skips_tracking_get_when_last_known_fresh(self):
        adapter = MagicMock()
        adapter.fetch_tracking.return_value = {"ok": True}
        adapter.position_history.return_value = {"points": []}
        order = SimpleNamespace(
            fleetbase_order_id="fb-ord",
            assigned_driver_id="drv-1",
            scheduled_at=datetime.now(UTC),
        )
        driver = SimpleNamespace(id="drv-1", fleetbase_driver_id="fb-drv")
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = [order]
        db.get.return_value = driver

        known = LastKnown(
            driver_id="drv-1",
            lat=NEAR[0],
            lng=NEAR[1],
            recorded_at=datetime.now(UTC),
            fleetbase_driver_id="fb-drv",
        )
        meta = {"history_refreshed_at": datetime.now(UTC).isoformat()}
        with (
            patch(
                "porterchain_api.driver_engine.last_known.read_last_known",
                return_value=known,
            ),
            patch.object(ops_mirror, "read_meta", return_value=meta),
            patch.object(ops_mirror, "read_tracking", return_value=({"stale": False}, "fleetbase_mirror")),
            patch.object(ops_mirror, "write_tracking") as write_tracking,
            patch.object(ops_mirror, "write_history") as write_history,
        ):
            tracking_n, history_n, skipped, _hist_at = OpsMirrorRefreshService()._refresh_orders(
                db, adapter
            )

        adapter.fetch_tracking.assert_not_called()
        adapter.position_history.assert_not_called()
        write_history.assert_not_called()
        write_tracking.assert_called_once()
        assert skipped == 1
        assert tracking_n == 1
        assert history_n == 0

    def test_fetches_tracking_when_last_known_stale(self):
        adapter = MagicMock()
        adapter.fetch_tracking.return_value = {"ok": True}
        adapter.position_history.return_value = {"points": []}
        order = SimpleNamespace(
            fleetbase_order_id="fb-ord",
            assigned_driver_id="drv-1",
            scheduled_at=datetime.now(UTC),
        )
        driver = SimpleNamespace(id="drv-1", fleetbase_driver_id="fb-drv")
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = [order]
        db.get.return_value = driver

        known = LastKnown(
            driver_id="drv-1",
            lat=NEAR[0],
            lng=NEAR[1],
            recorded_at=datetime.now(UTC) - timedelta(seconds=90),
            fleetbase_driver_id="fb-drv",
        )
        with (
            patch(
                "porterchain_api.driver_engine.last_known.read_last_known",
                return_value=known,
            ),
            patch.object(ops_mirror, "read_meta", return_value={}),
            patch.object(ops_mirror, "write_tracking"),
            patch.object(ops_mirror, "write_history"),
        ):
            OpsMirrorRefreshService()._refresh_orders(db, adapter)

        adapter.fetch_tracking.assert_called_once_with("fb-ord")
        adapter.position_history.assert_called_once()


class TestScoringNoFleetbaseHttp:
    def test_source_has_no_adapter_http(self):
        src = inspect.getsource(compute_ranked_suggestions)
        assert "get_fleetbase_integration" not in src
        assert "adapter.list_drivers" not in src
        assert "adapter.drivers.get" not in src

    def test_matrix_only_includes_h3_neighbors(self):
        pickup = {"lat": PICKUP[0], "lng": PICKUP[1]}
        order = SimpleNamespace(
            id="ord-h3",
            pickup=pickup,
            dropoff={},
            compliance_metadata={},
            quote=None,
        )
        near = _driver(id="near", rating=3.0, fleetbase_driver_id="fb-near")
        far = _driver(id="far", rating=5.0, fleetbase_driver_id="fb-far")
        db = MagicMock()
        db.get.return_value = order
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.group_by.return_value = q
        q.all.side_effect = [[far, near], []]

        known = {
            "near": LastKnown(
                driver_id="near",
                lat=NEAR[0],
                lng=NEAR[1],
                recorded_at=datetime.now(UTC),
                fleetbase_driver_id="fb-near",
                h3=cell(*NEAR),
            ),
            "far": LastKnown(
                driver_id="far",
                lat=FAR[0],
                lng=FAR[1],
                recorded_at=datetime.now(UTC),
                fleetbase_driver_id="fb-far",
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
            patch.object(ops_mirror, "online_map_from_mirror", return_value={}),
            patch.object(ops_mirror, "driver_by_fleetbase_id", return_value=None),
            patch(
                "porterchain_api.services.fleetbase_integration.get_fleetbase_integration"
            ) as get_fb,
        ):
            result = compute_ranked_suggestions(db, "ord-h3", maps=maps)

        get_fb.assert_not_called()
        sources = maps.matrix_durations.call_args[0][0]
        assert sources == [NEAR]


class TestWorkerInterval:
    def test_ops_mirror_interval_is_30s(self):
        worker_root = Path(__file__).resolve().parents[2] / "worker"
        # apps/api/run.py shadows apps/worker/run.py if already imported.
        sys.modules.pop("run", None)
        if str(worker_root) not in sys.path:
            sys.path.insert(0, str(worker_root))
        else:
            sys.path.remove(str(worker_root))
            sys.path.insert(0, str(worker_root))
        from run import OPS_MIRROR_INTERVAL_SECONDS

        assert OPS_MIRROR_INTERVAL_SECONDS == 30
