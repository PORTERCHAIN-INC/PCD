"""gps_board — on-duty pins from last_known, no Fleetbase id required."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from porterchain_api.dispatch_engine import gps_board
from porterchain_api.driver_engine.last_known import LastKnown


def test_board_pins_includes_driver_without_fleetbase_id():
    driver_id = str(uuid4())
    driver = SimpleNamespace(
        id=driver_id,
        full_name="Ada Driver",
        fleetbase_driver_id=None,
        is_online=True,
        availability="online",
        status="APPROVED",
    )
    shift = SimpleNamespace(
        driver_id=driver_id,
        status="active",
        ended_at=None,
        break_started_at=None,
        started_at=datetime.now(UTC),
    )
    known = LastKnown(
        driver_id=driver_id,
        lat=43.65,
        lng=-79.38,
        recorded_at=datetime.now(UTC),
    )
    db = MagicMock()
    shift_q = MagicMock()
    shift_q.filter.return_value.order_by.return_value.all.return_value = [shift]
    driver_q = MagicMock()
    driver_q.filter.return_value.all.return_value = [driver]

    def _query(model):
        name = getattr(model, "__name__", str(model))
        if "DriverShift" in name or model.__name__ == "DriverShift":
            return shift_q
        return driver_q

    db.query.side_effect = _query

    with patch("porterchain_api.dispatch_engine.gps_board.read_last_known", return_value=known):
        pins, source = gps_board.board_pins(db)

    assert source == "last_known"
    assert len(pins) == 1
    assert pins[0]["id"] == driver_id
    assert pins[0]["fleetbase_driver_id"] == ""
    assert pins[0]["lat"] == 43.65
    assert pins[0]["gps_source"] == "last_known"


def test_board_pins_skips_when_no_last_known():
    driver_id = str(uuid4())
    driver = SimpleNamespace(
        id=driver_id,
        full_name="No Pin",
        fleetbase_driver_id=None,
        is_online=True,
        availability="online",
        status="APPROVED",
    )
    shift = SimpleNamespace(
        driver_id=driver_id,
        status="active",
        ended_at=None,
        break_started_at=None,
        started_at=datetime.now(UTC),
    )
    db = MagicMock()
    shift_q = MagicMock()
    shift_q.filter.return_value.order_by.return_value.all.return_value = [shift]
    driver_q = MagicMock()
    driver_q.filter.return_value.all.return_value = [driver]
    db.query.side_effect = lambda model: (
        shift_q if getattr(model, "__name__", "") == "DriverShift" else driver_q
    )

    with patch("porterchain_api.dispatch_engine.gps_board.read_last_known", return_value=None):
        pins, source = gps_board.board_pins(db)

    assert pins == []
    assert source == "miss"
