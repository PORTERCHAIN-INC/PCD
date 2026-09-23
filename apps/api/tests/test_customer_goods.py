"""Customer parcel load rules — no database."""

from __future__ import annotations

import pytest

from porterchain_api.domain.customer_goods import (
    default_vehicle_catalog,
    goods_line,
    presets_from_card,
    resolve_load,
)


def test_skid_is_not_allowed_on_sedan():
    with pytest.raises(ValueError, match="parcel_not_allowed"):
        resolve_load(
            booking_mode="parcels",
            parcels=[{"preset_id": "skid", "quantity": 1}],
            vehicle_id="sedan_suv",
            catalog=default_vehicle_catalog(),
            presets=presets_from_card(None),
        )


def test_whole_vehicle_creates_no_parcels():
    load = resolve_load(
        booking_mode="vehicle",
        parcels=[{"preset_id": "small", "quantity": 2}],
        vehicle_id="sedan_suv",
        catalog=default_vehicle_catalog(),
        presets=presets_from_card(None),
    )
    assert load.items == []
    assert load.package_type == "whole_vehicle"
    assert load.weight_kg is None


def test_goods_line_counts_parcels():
    line = goods_line(
        {
            "vehicle_class": "sedan_suv",
            "booking_mode": "parcels",
            "parcels": {"booking_mode": "parcels", "items": [{}, {}, {}], "declared_value_cents": 10000},
        }
    )
    assert line["goods_summary"] == "3 parcels"
    assert line["declared_value_cents"] == 10000
