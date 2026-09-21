"""GTA leftover P1 — 30s pre-trip on shift meta, honest arrive via last-known geofence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.driver_engine.last_known import LastKnown
from porterchain_driver.navigation import assert_driver_inside_stop
from porterchain_driver.shift import PRETRIP_ITEMS, require_pretrip


def _all_pretrip() -> dict[str, bool]:
    return {key: True for key, _label in PRETRIP_ITEMS}


def test_require_pretrip_fail_closed() -> None:
    with pytest.raises(ValueError, match="pretrip_required"):
        require_pretrip(None)
    with pytest.raises(ValueError, match="pretrip_required"):
        require_pretrip({"lights": True})
    incomplete = _all_pretrip()
    incomplete["winter_kit"] = False
    with pytest.raises(ValueError, match="pretrip_required"):
        require_pretrip(incomplete)
    assert require_pretrip(_all_pretrip()) == _all_pretrip()


def _order() -> SimpleNamespace:
    return SimpleNamespace(
        id="ord-1",
        tracking_number="PC-1",
        pickup={"lat": 43.65, "lng": -79.38},
        dropoff={"lat": 43.66, "lng": -79.39},
    )


def _known(lat: float, lng: float) -> LastKnown:
    return LastKnown(driver_id="drv-1", lat=lat, lng=lng, recorded_at=datetime.now(UTC))


def test_arrive_open_when_gps_missing() -> None:
    with patch("porterchain_api.driver_engine.last_known.read_last_known", return_value=None):
        assert_driver_inside_stop("drv-1", _order(), "ord-1-dropoff")


def test_arrive_fail_closed_when_outside_stop() -> None:
    with patch(
        "porterchain_api.driver_engine.last_known.read_last_known",
        return_value=_known(43.85, -79.38),
    ):
        with pytest.raises(ValueError, match="not_at_stop"):
            assert_driver_inside_stop("drv-1", _order(), "ord-1-dropoff")


def test_arrive_ok_inside_stop_circle() -> None:
    with patch(
        "porterchain_api.driver_engine.last_known.read_last_known",
        return_value=_known(43.66, -79.39),
    ):
        assert_driver_inside_stop("drv-1", _order(), "ord-1-dropoff")


def test_online_requires_active_shift() -> None:
    from porterchain_driver.shift import ShiftService

    svc = ShiftService()
    db = MagicMock()
    driver = SimpleNamespace(id="drv-1", availability="offline", is_online=False, fleetbase_driver_id=None)
    with (
        patch.object(svc, "_require_approved"),
        patch.object(svc, "_active_shift", return_value=None),
    ):
        with pytest.raises(ValueError, match="shift_required"):
            svc.set_availability(db, driver, "online")
        with (
            patch.object(svc, "_log"),
            patch.object(svc, "_emit"),
            patch.object(svc, "snapshot", return_value={}),
        ):
            svc.set_availability(db, driver, "offline")
    assert driver.is_online is False
    assert driver.availability == "offline"


def test_offline_executor_shift_start_passes_pretrip() -> None:
    from porterchain_api.driver_engine.offline_executor import DriverOfflineExecutor

    platform = MagicMock()
    checks = _all_pretrip()
    DriverOfflineExecutor(platform=platform).execute(
        MagicMock(),
        SimpleNamespace(id="drv-1"),
        "shift_start",
        {"route_id": "r1", "pretrip": checks},
    )
    platform.shift.start_shift.assert_called_once()
    kwargs = platform.shift.start_shift.call_args.kwargs
    assert kwargs["pretrip"] == checks
    assert kwargs["route_id"] == "r1"


def test_web_pretrip_gate_on_shift_and_dashboard() -> None:
    root = Path(__file__).resolve().parents[3]
    gate = (root / "apps/driver-portal/src/components/dashboard/PretripGate.tsx").read_text()
    assert "30-second pre-trip" in gate
    dash = (root / "apps/driver-portal/src/app/dashboard/page.tsx").read_text()
    assert "startShift(pretrip)" in dash
    shift = (root / "apps/driver-portal/src/app/shift/page.tsx").read_text()
    assert "startShift(snap.current_route?.route_id, pretrip)" in shift
    assert "mode !== \"offline\" && !snap.shift_active" in shift
    qa = (root / "apps/driver-portal/src/components/dashboard/QuickActions.tsx").read_text()
    assert "!isOnline && !shiftActive" in qa
    mobile = (root / "apps/mobile-driver/src/hooks/useFieldSession.ts").read_text()
    assert '"shift_start"' in mobile
