"""Phase 6 — Valhalla date_time + failed-delivery reopt + soft sequence."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_services.maps.date_time import (
    attach_date_time,
    format_valhalla_date_time,
)


def test_format_valhalla_date_time_departure() -> None:
    payload = format_valhalla_date_time(datetime(2026, 9, 17, 17, 30), time_type=1)
    assert payload == {"type": 1, "value": "2026-09-17T17:30"}
    body: dict = {"costing": "auto"}
    assert attach_date_time(body, "2026-09-17T08:15:00Z") is True
    assert body["date_time"]["value"] == "2026-09-17T08:15"
    assert attach_date_time(body, None) is False


def test_reoptimize_skips_when_on_break() -> None:
    from porterchain_driver.route_optimizer import DriverRouteOptimizer

    driver = SimpleNamespace(id="drv-1", availability="on_break")
    out = DriverRouteOptimizer().reoptimize_remaining(MagicMock(), driver, "stop-1")
    assert out is None


def test_report_exception_triggers_reoptimize() -> None:
    from porterchain_driver.stops import StopsService

    db = MagicMock()
    driver = SimpleNamespace(id="drv-1")
    order = SimpleNamespace(
        id="ord-1",
        state="IN_TRANSIT",
        fleetbase_order_id="order_abc123",
        assigned_driver_id="drv-1",
    )

    def _flush() -> None:
        # Simulate DB assigning PK after flush.
        for call in db.add.call_args_list:
            obj = call.args[0]
            if getattr(obj, "id", None) is None:
                obj.id = "exc-1"

    db.flush.side_effect = _flush
    svc = StopsService()
    with (
        patch.object(svc, "_order_for_stop", return_value=order),
        patch(
            "porterchain_api.booking_engine.order_transitions.transition_order_state",
            return_value=order,
        ),
        patch("porterchain_api.booking_engine._core.emit_event"),
        patch(
            "porterchain_driver.route_optimizer.DriverRouteOptimizer.reoptimize_remaining",
            return_value={"run_id": "run-x", "status": "pending"},
        ) as reopt,
    ):
        out = svc.report_exception(
            db,
            driver,
            "ord-1-dropoff",
            exception_type="FAILED_DELIVERY",
            auto_reoptimize=True,
        )
    assert out["exception_id"] == "exc-1"
    assert out["reoptimize"]["run_id"] == "run-x"
    reopt.assert_called_once()


def test_soft_sequence_orders_prior_assignments() -> None:
    from porterchain_driver.route_optimizer import DriverRouteOptimizer

    db = MagicMock()
    driver = SimpleNamespace(
        id="drv-1",
        availability="online",
        fleetbase_driver_id="driver_abc123xyz",
    )
    o1 = SimpleNamespace(id="o1", state="PICKED_UP", fleetbase_order_id="order_aaa111")
    o2 = SimpleNamespace(id="o2", state="DRIVER_ACCEPTED", fleetbase_order_id="order_bbb222")
    vehicle = SimpleNamespace(
        driver_id="drv-1",
        is_active=True,
        fleetbase_vehicle_id="vehicle_ccc333",
    )
    plan = {
        "waypoints": [
            {"order_id": "o2", "stop_type": "pickup"},
            {"order_id": "o1", "stop_type": "dropoff"},
        ]
    }
    with (
        patch(
            "porterchain_driver.stops.StopsService._today_orders",
            return_value=[o1, o2],
        ),
        patch(
            "porterchain_driver.sequence_store.read_sequence",
            return_value=plan,
        ),
        patch(
            "porterchain_api.dispatch_engine.day_plan.queue_one_van",
            return_value={"run_id": "r1", "status": "pending"},
        ) as enqueue,
        patch.object(
            DriverRouteOptimizer,
            "can_optimize",
            return_value=True,
        ),
    ):
        db.query.return_value.filter.return_value.all.return_value = [vehicle]
        out = DriverRouteOptimizer().reoptimize_remaining(db, driver, "x")
    assert out and out.get("soft_sequence") is True
    # Soft order: o2 before o1 from sequence waypoints.
    assert enqueue.call_args.args[0]["order_ids"] == ["o2", "o1"]
