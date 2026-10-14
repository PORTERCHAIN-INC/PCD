"""Offline replay of a multi-stop route check-in goes through DriverRouteService.check_in."""

from unittest.mock import MagicMock, patch

from porterchain_api.driver_engine.offline_executor import DriverOfflineExecutor


def test_dispatch_checkin_replays_through_route_service():
    driver = MagicMock(id="drv-1")
    db = MagicMock()
    with patch("porterchain_api.dispatch_engine.driver_route.DriverRouteService.check_in") as check_in:
        DriverOfflineExecutor(platform=MagicMock()).execute(
            db,
            driver,
            "dispatch_checkin",
            {"keys": ["o1:drop"], "event": "arrived", "lat": 43.5, "lng": -79.8, "client_id": "c-1"},
        )
    kwargs = check_in.call_args.kwargs
    assert kwargs["keys"] == ["o1:drop"]
    assert kwargs["event"] == "arrived"
    assert kwargs["lat"] == 43.5 and kwargs["client_id"] == "c-1"
    assert kwargs["pod_photo"] is None
    assert callable(kwargs["scan_gate"])
