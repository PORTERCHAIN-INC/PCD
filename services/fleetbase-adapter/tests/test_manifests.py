"""ManifestService normalize + list extraction (P1-5)."""

from __future__ import annotations

from porterchain_fleetbase_adapter.manifests import (
    _extract_list,
    normalize_manifest,
)


def test_extract_list_from_manifests_key():
    rows = _extract_list({"manifests": [{"id": "m1"}, "skip"]})
    assert rows == [{"id": "m1"}]


def test_extract_list_from_data_key():
    assert len(_extract_list({"data": [{"id": "a"}, {"id": "b"}]})) == 2


def test_normalize_manifest_flattens_stops_and_driver():
    raw = {
        "uuid": "man-1",
        "public_id": "manifest_abc",
        "status": "active",
        "scheduled_date": "2026-08-07",
        "driver": {"id": "d1", "name": "Alex"},
        "vehicle": {"id": "v1", "name": "Van 3"},
        "stops": [
            {"uuid": "s1", "sequence": 0, "status": "pending", "order_uuid": "o1"},
            {"id": "s2", "sequence": 1, "status": "completed", "order_id": "o2"},
        ],
    }
    m = normalize_manifest(raw)
    assert m["id"] == "man-1"
    assert m["public_id"] == "manifest_abc"
    assert m["driver_name"] == "Alex"
    assert m["vehicle_name"] == "Van 3"
    assert m["stop_count"] == 2
    assert m["stops"][0]["order_id"] == "o1"
    assert m["stops"][1]["status"] == "completed"
