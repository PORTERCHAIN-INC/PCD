"""Orchestrator normalize helpers (P1-3)."""

from porterchain_fleetbase_adapter.orchestrator import (
    normalize_commit_result,
    normalize_run_result,
)


def test_normalize_run_sums_metrics():
    raw = {
        "assignments": [
            {"order_id": "order_1", "vehicle_id": "v1", "distance": 5000, "duration": 600},
            {"order_id": "order_2", "vehicle_id": "v1", "distance": 3000, "duration": 400},
            {"order_id": "order_3", "vehicle_id": "v2", "distance_m": 2000, "duration_s": 200},
        ],
        "unassigned": ["order_4"],
    }
    out = normalize_run_result(raw)
    assert out["ok"] is True
    assert out["metrics"]["assigned_count"] == 3
    assert out["metrics"]["unassigned_count"] == 1
    assert out["metrics"]["capacity_reject_count"] == 0
    assert out["metrics"]["vehicles_used"] == 2
    assert out["metrics"]["after_distance_m"] == 10000
    assert out["metrics"]["after_duration_s"] == 1200
    assert out["metrics"]["after_distance_km"] == 10.0
    assert out["metrics"]["utilization_orders_per_vehicle"] == 1.5


def test_normalize_run_surfaces_capacity_rejects():
    raw = {
        "assignments": [],
        "unassigned": ["order_heavy"],
        "summary": {
            "unassigned_reasons": [
                {"id": "order_heavy", "reason": "no_available_vehicle"},
            ]
        },
    }
    out = normalize_run_result(raw)
    assert out["ok"] is True
    assert out["unassigned"] == ["order_heavy"]
    assert out["unassigned_details"] == [
        {"order_id": "order_heavy", "reason": "no_available_vehicle"}
    ]
    assert out["metrics"]["capacity_reject_count"] == 1


def test_normalize_run_engine_error():
    out = normalize_run_result({"error": "VROOM down", "hint": "use greedy", "engine": "vroom"})
    assert out["ok"] is False
    assert out["error"] == "VROOM down"
    assert out["hint"] == "use greedy"
    assert out["assignments"] == []


def test_normalize_commit():
    out = normalize_commit_result(
        {"committed": ["a"], "failed": [], "manifests": [{"id": "m1"}, {"id": "m2"}]}
    )
    assert out["ok"] is True
    assert out["manifest_count"] == 2
