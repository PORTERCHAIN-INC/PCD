"""Phase 5 — sequence version lock, idempotent apply, rollback, NIM/stub freeze."""

from __future__ import annotations

from unittest.mock import patch

from porterchain_driver.sequence_store import (
    SequenceConflictError,
    apply_run_to_driver,
    rollback_sequence,
)

from porterchain_api.intelligence_engine.copilot_service import ALLOWED_ACTIONS


def test_apply_run_increments_version_and_is_idempotent() -> None:
    store: dict[str, dict] = {}

    def _read(driver_id: str):
        return store.get(driver_id)

    def _write(driver_id: str, payload: dict) -> None:
        store[driver_id] = payload

    rec = {
        "status": "ready",
        "run_id": "run-a",
        "engine": "vroom",
        "assignments": [
            {"order_id": "o1", "sequence": 1, "vehicle_id": "v1"},
            {"order_id": "o2", "sequence": 2, "vehicle_id": "v1"},
        ],
        "metrics": {"after_distance_km": 12.5},
    }
    with (
        patch("porterchain_driver.sequence_store.read_sequence", side_effect=_read),
        patch("porterchain_driver.sequence_store.write_sequence", side_effect=_write),
    ):
        first = apply_run_to_driver("drv-1", rec)
        assert len(first) == 4  # pickup+dropoff × 2
        assert store["drv-1"]["version"] == 1
        assert store["drv-1"]["run_id"] == "run-a"

        again = apply_run_to_driver("drv-1", rec)
        assert again == first
        assert store["drv-1"]["version"] == 1  # idempotent — no bump


def test_apply_run_conflicts_on_stale_expected_version() -> None:
    store: dict[str, dict] = {
        "drv-1": {
            "version": 2,
            "run_id": "run-old",
            "waypoints": [{"sequence": 0, "order_id": "o0", "stop_type": "pickup"}],
        }
    }

    def _read(driver_id: str):
        return store.get(driver_id)

    rec = {
        "status": "ready",
        "run_id": "run-new",
        "assignments": [{"order_id": "o1", "sequence": 1}],
    }
    with patch("porterchain_driver.sequence_store.read_sequence", side_effect=_read):
        try:
            apply_run_to_driver("drv-1", rec, expected_version=1)
            raise AssertionError("expected SequenceConflictError")
        except SequenceConflictError as exc:
            assert exc.current_version == 2
            assert exc.expected_version == 1


def test_rollback_restores_previous_snapshot() -> None:
    store: dict[str, dict] = {}

    def _read(driver_id: str):
        return store.get(driver_id)

    def _write(driver_id: str, payload: dict) -> None:
        store[driver_id] = payload

    with (
        patch("porterchain_driver.sequence_store.read_sequence", side_effect=_read),
        patch("porterchain_driver.sequence_store.write_sequence", side_effect=_write),
    ):
        apply_run_to_driver(
            "drv-1",
            {
                "status": "ready",
                "run_id": "run-1",
                "assignments": [{"order_id": "o1", "sequence": 1}],
            },
        )
        apply_run_to_driver(
            "drv-1",
            {
                "status": "ready",
                "run_id": "run-2",
                "assignments": [{"order_id": "o2", "sequence": 1}],
            },
        )
        assert store["drv-1"]["run_id"] == "run-2"
        assert store["drv-1"]["previous"]["run_id"] == "run-1"

        restored = rollback_sequence("drv-1")
        assert restored is not None
        assert restored["run_id"] == "run-1"
        assert store["drv-1"]["run_id"] == "run-1"
        assert store["drv-1"]["source"] == "rollback"


def test_nim_phase5_actions_closed_set() -> None:
    for action in (
        "run_optimize_preview",
        "compare_cuopt_shadow",
        "reoptimize_after_pickup",
        "explain_fsa_coverage",
        "hold_for_out_of_tile",
    ):
        assert action in ALLOWED_ACTIONS
