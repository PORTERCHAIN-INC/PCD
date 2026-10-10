"""Step 2 Waves 1–2 — driver/merchant optimize enqueue, no in-process TSP."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_driver.jobs import JobsService

from porterchain_api.merchant_engine.route_import_service import (
    MerchantRouteImportService,
)


def test_driver_optimize_route_queues_one_van() -> None:
    db = MagicMock()
    driver = SimpleNamespace(id="drv-1", fleetbase_driver_id="driver_abc123xyz")
    order = SimpleNamespace(
        id="ord-1",
        state="DRIVER_ASSIGNED",
        fleetbase_order_id="order_abc123xyz",
        pickup={"lat": 43.65, "lng": -79.38},
        dropoff={"lat": 43.7, "lng": -79.4},
    )
    vehicle = SimpleNamespace(
        driver_id="drv-1",
        is_active=True,
        fleetbase_vehicle_id="vehicle_abc123xyz",
        vehicle_class="cargo_van",
    )
    db.query.return_value.filter.return_value.all.return_value = [vehicle]
    svc = JobsService()
    pending = {
        "run_id": "run-9",
        "status": "pending",
        "assignments": [],
        "metrics": {"engine": "porterchain"},
        "order_ids": ["ord-1"],
        "engine": "porterchain",
    }
    with (
        patch.object(svc, "_today_orders", return_value=[order]),
        patch.object(svc, "list_jobs", return_value={"jobs": [], "optimize_available": True}),
        patch("porterchain_driver.sequence_store.read_sequence", return_value=None),
        patch("porterchain_api.dispatch_engine.day_plan.queue_one_van", return_value=pending) as enq,
    ):
        out = svc.optimize_route(db, driver)
    enq.assert_called_once()
    payload = enq.call_args.args[0]
    assert payload["order_ids"] == ["ord-1"]
    assert payload["vehicle_class"] == "cargo_van"
    assert payload["pc_driver_id"] == "drv-1"
    assert payload["jobs"][0]["picked_up"] is False
    assert out["status"] == "pending"
    assert out["run_id"] == "run-9"
    assert out["metrics"]["engine"] == "porterchain"


def test_driver_optimize_route_requires_jobs_with_coords() -> None:
    db = MagicMock()
    driver = SimpleNamespace(id="drv-1")
    svc = JobsService()
    with patch.object(svc, "_today_orders", return_value=[]):
        try:
            svc.optimize_route(db, driver)
        except ValueError as exc:
            assert str(exc) == "no_synced_jobs"
        else:
            raise AssertionError("expected no_synced_jobs")
    order = SimpleNamespace(
        id="ord-1",
        state="DRIVER_ASSIGNED",
        pickup={},
        dropoff={},
    )
    with patch.object(svc, "_today_orders", return_value=[order]):
        try:
            svc.optimize_route(db, driver)
        except ValueError as exc:
            assert str(exc) == "no_synced_jobs"
        else:
            raise AssertionError("expected no_synced_jobs")


def test_reoptimize_remaining_queues_the_van() -> None:
    from porterchain_driver.route_optimizer import DriverRouteOptimizer

    db = MagicMock()
    driver = SimpleNamespace(id="drv-1", fleetbase_driver_id="driver_abc123xyz")
    orders = [
        SimpleNamespace(
            id="ord-1",
            state="PICKED_UP",
            fleetbase_order_id="order_abc123xyz",
            pickup={"lat": 43.65, "lng": -79.38},
            dropoff={"lat": 43.66, "lng": -79.39},
            amount_cents=1000,
            scheduled_at=None,
        ),
        SimpleNamespace(
            id="ord-2",
            state="DRIVER_ASSIGNED",
            fleetbase_order_id="order_def456uvw",
            pickup={"lat": 43.67, "lng": -79.40},
            dropoff={"lat": 43.68, "lng": -79.41},
            amount_cents=500,
            scheduled_at=None,
        ),
    ]
    vehicle = SimpleNamespace(
        driver_id="drv-1",
        is_active=True,
        fleetbase_vehicle_id="vehicle_abc123xyz",
        vehicle_class="cargo_van",
    )
    db.query.return_value.filter.return_value.all.return_value = [vehicle]
    pending = {"run_id": "run-reopt-1", "status": "pending", "error": None}
    with (
        patch("porterchain_driver.stops.StopsService._today_orders", return_value=orders),
        patch("porterchain_driver.sequence_store.read_sequence", return_value=None),
        patch(
            "porterchain_api.dispatch_engine.day_plan.queue_one_van",
            return_value=pending,
        ) as enq,
    ):
        out = DriverRouteOptimizer().reoptimize_remaining(db, driver, "stop-done")
    assert out is not None
    assert out["run_id"] == "run-reopt-1"
    assert out["engine"] == "porterchain"
    assert out["order_ids"] == ["ord-1", "ord-2"]
    payload = enq.call_args.args[0]
    assert payload["jobs"][0]["picked_up"] is True
    assert payload["jobs"][1]["picked_up"] is False
    assert payload["pc_driver_id"] == "drv-1"


def test_driver_optimize_midday_insert_excludes_new_from_prior() -> None:
    db = MagicMock()
    driver = SimpleNamespace(id="drv-1", fleetbase_driver_id="driver_abc123xyz")
    existing = SimpleNamespace(
        id="ord-old",
        state="PICKED_UP",
        fleetbase_order_id="order_abc123xyz",
        pickup={"lat": 43.65, "lng": -79.38},
        dropoff={"lat": 43.66, "lng": -79.39},
    )
    inserted = SimpleNamespace(
        id="ord-new",
        state="DRIVER_ASSIGNED",
        fleetbase_order_id="order_def456uvw",
        pickup={"lat": 43.67, "lng": -79.40},
        dropoff={"lat": 43.68, "lng": -79.41},
    )
    vehicle = SimpleNamespace(
        driver_id="drv-1",
        is_active=True,
        fleetbase_vehicle_id="vehicle_abc123xyz",
    )
    db.query.return_value.filter.return_value.all.return_value = [vehicle]
    svc = JobsService()
    pending = {"run_id": "run-ins", "status": "pending", "assignments": [], "metrics": {}, "order_ids": []}
    with (
        patch.object(svc, "_today_orders", return_value=[existing, inserted]),
        patch.object(svc, "list_jobs", return_value={"jobs": []}),
        patch("porterchain_driver.sequence_store.read_sequence", return_value=None),
        patch("porterchain_api.dispatch_engine.day_plan.queue_one_van", return_value=pending) as enq,
    ):
        svc.optimize_route(db, driver, insert_order_id="ord-new")
    jobs = enq.call_args.args[0]["jobs"]
    by_id = {job["id"]: job for job in jobs}
    assert by_id["ord-old"]["picked_up"] is True
    assert by_id["ord-new"]["picked_up"] is False
    assert enq.call_args.args[0]["order_ids"] == ["ord-old", "ord-new"]


def test_merchant_optimize_sets_pending_and_enqueues() -> None:
    db = MagicMock()
    job = SimpleNamespace(
        id="job-1",
        status="preview",
        job_config={"stops": [{"geocode_status": "ok", "lat": 43.65, "lng": -79.38}]},
    )
    svc = MerchantRouteImportService()
    with (
        patch.object(svc, "get_job", return_value=job),
        patch.object(svc, "_assert_unconfirmed"),
        patch.object(svc, "_enqueue_optimize") as enq,
    ):
        out = svc.optimize(db, MagicMock(), "job-1")
    assert out.job_config["optimize_status"] == "pending"
    assert out.job_config["optimized"] is False
    enq.assert_called_once_with("job-1")
    db.commit.assert_called()
