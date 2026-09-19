"""Phase 2 intelligence scaffold smoke tests."""

from __future__ import annotations

from porterchain_api.intelligence_engine.assignment_service import recommend_batch_assignment
from porterchain_api.intelligence_engine.eta_service import predict_eta_minutes


def test_phase2_stubs_default_off() -> None:
    flags: dict[str, bool] = {}
    eta = predict_eta_minutes(distance_km=10.0, duration_min=20.0, flags=flags)
    assert eta["phase2"] is False
    assert recommend_batch_assignment(["o1"], ["d1"], flags=flags)["status"] == "phase2_disabled"


def test_phase2_eta_when_enabled() -> None:
    flags = {"intelligence": True}
    eta = predict_eta_minutes(distance_km=10.0, duration_min=20.0, flags=flags)
    assert eta["phase2"] is True
    assert eta["confidence"] > 0.5
