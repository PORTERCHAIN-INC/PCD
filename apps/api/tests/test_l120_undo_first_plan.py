"""L120: undo after the first Accept restores "no plan"; nothing to undo is a clean 200 shape."""

from unittest.mock import patch

from porterchain_api.schemas_driver import DriverJobsListResponse, DriverJobsOptimizeResponse
from porterchain_driver.sequence_store import apply_run_to_driver, can_undo, rollback_sequence


def _store():
    store: dict[str, dict] = {}
    return store, (
        patch("porterchain_driver.sequence_store.read_sequence", side_effect=lambda d: store.get(d)),
        patch("porterchain_driver.sequence_store.write_sequence", side_effect=lambda d, p: store.__setitem__(d, p)),
    )


def test_undo_first_accept_restores_empty_plan() -> None:
    store, (r, w) = _store()
    with r, w:
        apply_run_to_driver("drv", {"status": "ready", "run_id": "run-1",
                                    "assignments": [{"order_id": "o1", "sequence": 1}]})
        assert store["drv"]["previous"] is None
        assert can_undo(store["drv"]) is True
        restored = rollback_sequence("drv")
        assert restored is not None
        assert store["drv"]["waypoints"] == []
        assert store["drv"]["source"] == "rollback"
        assert can_undo(store["drv"]) is False


def test_nothing_to_undo_matches_response_model() -> None:
    body = {"ok": False, "status": "error", "error": "nothing_to_undo",
            "message": "No previous stop order to restore.",
            "jobs": DriverJobsListResponse().model_dump(), "plan_id": "none"}
    out = DriverJobsOptimizeResponse.model_validate(body)
    assert out.error == "nothing_to_undo"
    assert DriverJobsListResponse().can_undo is False
