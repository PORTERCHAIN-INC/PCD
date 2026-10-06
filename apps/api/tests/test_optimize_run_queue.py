"""Admin optimize run queues the PorterChain day plan — no Fleetbase HTTP."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService


def test_enqueue_run_queues_porterchain_day_plan() -> None:
    db = MagicMock()
    svc = OrchestratorOpsService()
    order = SimpleNamespace(
        id="pc-1",
        assigned_driver_id="drv-1",
        merchant_id=None,
        pickup={"lat": 43.65, "lng": -79.38},
        dropoff={"lat": 43.7, "lng": -79.4},
        state="DISPATCH_READY",
        weight_kg=10,
        volume_m3=0,
        pallets=0,
        parcels=1,
        service_minutes=5,
        scheduled_at=None,
    )
    driver = SimpleNamespace(id="drv-1", is_online=True, availability="online", status="approved")
    vehicle = SimpleNamespace(
        id="veh-1",
        driver_id="drv-1",
        is_active=True,
        vehicle_class="cargo_van",
        capacity_kg=500,
    )
    pending = {
        "run_id": "run-1",
        "status": "pending",
        "ok": True,
        "engine": "porterchain",
        "assignments": [],
        "pc_driver_id": "drv-1",
    }

    def _query_side(model):
        q = MagicMock()
        name = getattr(model, "__name__", str(model))
        if name == "Order" or model is order.__class__:
            q.filter.return_value.all.return_value = [order]
            return q
        if "Vehicle" in name:
            q.filter.return_value.first.return_value = vehicle
            q.filter.return_value.all.return_value = [vehicle]
            return q
        if "Driver" in name:
            q.filter.return_value.all.return_value = [driver]
            return q
        q.filter.return_value.all.return_value = []
        q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = _query_side
    db.get.side_effect = lambda model, key: driver if key == "drv-1" else (vehicle if key == "veh-1" else None)

    with (
        patch.object(svc, "_load_orders", return_value=[order]),
        patch.object(svc, "_resolve_pc_driver", return_value="drv-1"),
        patch.object(svc, "_vehicle_for_driver", return_value=vehicle),
        patch("porterchain_api.driver_engine.last_known.read_last_known", return_value=None),
        patch(
            "porterchain_api.dispatch_engine.day_plan.queue_one_van",
            return_value=pending,
        ) as enq,
        patch(
            "porterchain_api.dispatch_engine.day_plan.payload_from_orders",
            return_value={"stops": [], "jobs": [], "order_ids": ["pc-1"]},
        ),
    ):
        out = svc.enqueue_run(db, mode="allocate", engine="porterchain", order_ids=["pc-1"])
    assert out["status"] == "pending"
    assert out["ok"] is True
    assert out["run_id"] == "run-1"
    assert out["engine"] == "porterchain"
    enq.assert_called_once()


def test_enqueue_run_no_orders_skips_queue() -> None:
    db = MagicMock()
    svc = OrchestratorOpsService()
    with (
        patch.object(svc, "_load_orders", return_value=[]),
        patch("porterchain_api.dispatch_engine.day_plan.queue_one_van") as enq,
    ):
        out = svc.enqueue_run(db, order_ids=["missing"])
    assert out["status"] == "error"
    assert out["error"] == "no_eligible_orders"
    assert out["ok"] is False
    enq.assert_not_called()


def test_enqueue_run_no_driver_skips_queue() -> None:
    db = MagicMock()
    svc = OrchestratorOpsService()
    order = SimpleNamespace(id="pc-1", assigned_driver_id=None)
    with (
        patch.object(svc, "_load_orders", return_value=[order]),
        patch.object(svc, "_resolve_pc_driver", return_value=None),
        patch("porterchain_api.dispatch_engine.day_plan.queue_one_van") as enq,
    ):
        out = svc.enqueue_run(db, order_ids=["pc-1"])
    assert out["status"] == "error"
    assert out["error"] == "no_driver"
    assert out["ok"] is False
    enq.assert_not_called()


def test_execute_queued_run_finishes_day_plan() -> None:
    db = MagicMock()
    svc = OrchestratorOpsService()
    pending = {
        "run_id": "run-1",
        "status": "pending",
        "order_ids": ["pc-1"],
        "engine": "porterchain",
        "pc_driver_id": "drv-1",
        "apply_on_ready": False,
        "assignments": [],
    }
    solved = {
        "ok": True,
        "status": "ready",
        "assignments": [{"order_id": "pc-1", "porterchain_order_id": "pc-1"}],
        "metrics": {"engine": "porterchain"},
        "pc_driver_id": "drv-1",
    }
    with (
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.read_optimize_run",
            return_value=pending,
        ),
        patch(
            "porterchain_api.dispatch_engine.day_plan.finish_porterchain_run",
            return_value=solved,
        ),
    ):
        out = svc.execute_queued_run(db, "run-1")
    assert out["status"] == "ready"
    assert out["ok"] is True
    assert len(out["assignments"]) == 1
