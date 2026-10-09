"""GTA field bar — coded stop exceptions, attempts → RTS, access notes."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_driver.next_stop import NextStopResolver, mask_phone
from porterchain_driver.stop_exceptions import (
    MAX_DELIVERY_ATTEMPTS,
    normalize_exception_type,
    resolve_outcome,
)
from porterchain_driver.stops import StopsService


def test_normalize_aliases_and_rejects_unknown() -> None:
    assert normalize_exception_type("FAILED_DELIVERY") == "unable_to_deliver"
    assert normalize_exception_type("not_home") == "customer_not_available"
    with pytest.raises(ValueError, match="unknown_exception_type"):
        normalize_exception_type("delay")


def test_second_retryable_attempt_is_rts() -> None:
    assert resolve_outcome("customer_not_available", 0) == "retry"
    assert resolve_outcome("customer_not_available", 1) == "return_to_sender"
    assert resolve_outcome("refused", 0) == "failed"
    assert MAX_DELIVERY_ATTEMPTS == 2


def _order() -> SimpleNamespace:
    return SimpleNamespace(
        id="ord-1",
        state="AT_DESTINATION",
        fleetbase_order_id=None,
        assigned_driver_id="drv-1",
    )


def _svc_order(order: SimpleNamespace) -> StopsService:
    svc = StopsService()
    svc._order_for_stop = MagicMock(return_value=order)  # noqa: SLF001
    return svc


def test_refused_requires_photo() -> None:
    svc = _svc_order(_order())
    with pytest.raises(ValueError, match="photo_required"):
        svc.report_exception(MagicMock(), SimpleNamespace(id="drv-1"), "ord-1-dropoff", exception_type="refused")


def test_not_home_stays_on_stop_no_reopt() -> None:
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    order = _order()
    svc = _svc_order(order)

    def _flush() -> None:
        for call in db.add.call_args_list:
            obj = call.args[0]
            if getattr(obj, "id", None) is None:
                obj.id = "exc-retry"

    db.flush.side_effect = _flush
    with (
        patch("porterchain_api.booking_engine.order_transitions.transition_order_state") as trans,
        patch("porterchain_api.booking_engine._core.emit_event"),
        patch(
            "porterchain_driver.route_optimizer.DriverRouteOptimizer.reoptimize_remaining"
        ) as reopt,
    ):
        out = svc.report_exception(
            db,
            SimpleNamespace(id="drv-1"),
            "ord-1-dropoff",
            exception_type="customer_not_available",
            auto_reoptimize=True,
        )
    assert out["outcome"] == "retry"
    assert out["attempt"] == 1
    trans.assert_not_called()
    reopt.assert_not_called()
    assert order.state == "AT_DESTINATION"


def test_second_not_home_returns_to_sender() -> None:
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [
        SimpleNamespace(type="customer_not_available")
    ]
    order = _order()
    svc = _svc_order(order)

    def _flush() -> None:
        for call in db.add.call_args_list:
            obj = call.args[0]
            if getattr(obj, "id", None) is None:
                obj.id = "exc-rts"

    db.flush.side_effect = _flush
    with (
        patch(
            "porterchain_api.booking_engine.order_transitions.transition_order_state",
            side_effect=lambda _db, ord_, target, **_kw: setattr(ord_, "state", target.value) or ord_,
        ),
        patch("porterchain_api.booking_engine._core.emit_event"),
        patch(
            "porterchain_driver.route_optimizer.DriverRouteOptimizer.reoptimize_remaining",
            return_value={"run_id": "run-rts", "status": "pending"},
        ) as reopt,
    ):
        out = svc.report_exception(
            db,
            SimpleNamespace(id="drv-1"),
            "ord-1-dropoff",
            exception_type="customer_not_available",
            auto_reoptimize=True,
        )
    assert out["outcome"] == "return_to_sender"
    assert out["attempt"] == 2
    assert order.state == "RETURN_TO_SENDER"
    reopt.assert_called_once()


def test_next_stop_access_and_masked_phone() -> None:
    assert mask_phone("4165551212") == "•••-••12"
    stop = SimpleNamespace(
        stop_id="s1",
        stop_type="dropoff",
        order_id="o1",
        order_number="N",
        tracking_number="T",
        sequence=1,
        status="pending",
        special_instructions="Leave with concierge",
        address={
            "formatted": "12 King St W",
            "unit": "1402",
            "buzzer": "1402",
            "dock": "3",
            "call_on_arrival": True,
            "phone": "4165551212",
            "lat": 43.65,
            "lng": -79.38,
        },
    )
    out = NextStopResolver()._to_dict(stop, distance_m=None, eta_minutes=None, source=None)
    assert out["access_unit"] == "1402"
    assert out["access_buzzer"] == "1402"
    assert out["access_dock"] == "3"
    assert out["call_on_arrival"] is True
    assert out["contact_phone_masked"] == "•••-••12"
    assert out["special_instructions"] == "Leave with concierge"
    assert "4165551212" not in str(out["contact_phone_masked"])


def test_dropoff_open_when_pod_paused(monkeypatch) -> None:
    """Kill switch DRIVER_POD_ENFORCED=false: missing proof does not block complete delivery.

    (Enforcement is ON by default since readiness audit #5.)"""
    from porterchain_driver.stops import _assert_dropoff_pod_ready

    monkeypatch.setenv("DRIVER_POD_ENFORCED", "false")
    db = MagicMock()
    order = SimpleNamespace(id="ord-1", state="AT_DESTINATION", compliance_metadata={})
    _assert_dropoff_pod_ready(db, order)
    db.query.assert_not_called()


def test_dropoff_requires_proof_when_pod_enforced() -> None:
    from porterchain_driver.stops import _assert_dropoff_pod_ready

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    order = SimpleNamespace(id="ord-1", state="AT_DESTINATION", compliance_metadata={})
    with (
        patch("porterchain_driver.stops.ENFORCE_DROP_POD", True),
        pytest.raises(PermissionError, match="pod_required"),
    ):
        _assert_dropoff_pod_ready(db, order)
