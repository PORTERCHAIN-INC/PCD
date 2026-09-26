"""Valhalla costing selector for box vs auto vehicle classes."""

from __future__ import annotations

from porterchain_services.maps.costing import (
    resolve_valhalla_costing,
    valhalla_costing_for_vehicle_class,
)


def test_box_truck_uses_truck_costing() -> None:
    assert valhalla_costing_for_vehicle_class("box_truck") == "truck"
    assert valhalla_costing_for_vehicle_class("boxTruck") == "truck"
    assert valhalla_costing_for_vehicle_class("straight-truck") == "truck"
    assert valhalla_costing_for_vehicle_class("box_16") == "truck"
    assert valhalla_costing_for_vehicle_class("box16") == "truck"
    assert valhalla_costing_for_vehicle_class("box_20") == "truck"
    assert valhalla_costing_for_vehicle_class("box20") == "truck"
    assert valhalla_costing_for_vehicle_class("box_16") == "truck"
    assert valhalla_costing_for_vehicle_class("box_20") == "truck"
    assert valhalla_costing_for_vehicle_class("box16") == "truck"


def test_vans_and_cars_use_auto() -> None:
    assert valhalla_costing_for_vehicle_class("cargo_van") == "auto"
    assert valhalla_costing_for_vehicle_class("sedan") == "auto"
    assert valhalla_costing_for_vehicle_class("sprinter_van") == "auto"
    assert valhalla_costing_for_vehicle_class(None) == "auto"
    assert valhalla_costing_for_vehicle_class("") == "auto"


def test_explicit_costing_wins() -> None:
    assert resolve_valhalla_costing(costing="truck", vehicle_class="sedan") == "truck"
    assert resolve_valhalla_costing(costing="auto", vehicle_class="box_truck") == "auto"
    assert resolve_valhalla_costing(vehicle_class="box_truck") == "truck"
