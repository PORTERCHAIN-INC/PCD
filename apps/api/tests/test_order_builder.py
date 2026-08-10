"""Admin multi-waypoint order builder — stop validation + kind rules (P1-4)."""

from __future__ import annotations

import pytest

from porterchain_api.admin_engine.order_builder_service import (
    _normalize_stops,
    _validate_kind,
)
from porterchain_api.schemas_admin import AdminOrderStopInput


def _stop(type_: str, seq: int, addr: str = "1 King St") -> AdminOrderStopInput:
    return AdminOrderStopInput(
        type=type_,
        sequence=seq,
        formatted=addr,
        lat=43.65 + seq * 0.01,
        lng=-79.38,
    )


def test_normalize_sorts_and_maps_drop_alias():
    stops = _normalize_stops([_stop("drop", 2, "B"), _stop("pickup", 0, "A"), _stop("dropoff", 1, "C")])
    assert [s["type"] for s in stops] == ["pickup", "dropoff", "dropoff"]
    assert [s["sequence"] for s in stops] == [0, 1, 2]
    assert stops[0]["id"] == "s0"


def test_single_kind_ok():
    stops = _normalize_stops([_stop("pickup", 0), _stop("dropoff", 1)])
    _validate_kind("single", stops)


def test_hub_spoke_requires_multi_drop():
    stops = _normalize_stops([_stop("pickup", 0), _stop("dropoff", 1)])
    with pytest.raises(ValueError, match="hub_spoke"):
        _validate_kind("hub_spoke", stops)

    stops = _normalize_stops([_stop("pickup", 0), _stop("dropoff", 1), _stop("dropoff", 2)])
    _validate_kind("hub_spoke", stops)


def test_multi_requires_two_each():
    stops = _normalize_stops(
        [_stop("pickup", 0), _stop("pickup", 1), _stop("dropoff", 2), _stop("dropoff", 3)]
    )
    _validate_kind("multi_pickup_delivery", stops)

    with pytest.raises(ValueError, match="multi_requires"):
        _validate_kind(
            "multi_pickup_delivery",
            _normalize_stops([_stop("pickup", 0), _stop("dropoff", 1), _stop("dropoff", 2)]),
        )


def test_invalid_stop_type():
    with pytest.raises(ValueError, match="invalid_stop_type"):
        _normalize_stops([AdminOrderStopInput(type="hub", sequence=0, formatted="X")])
