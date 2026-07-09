"""Intelligence engine boundary — Phase 2 scaffold only."""

from __future__ import annotations

from porterchain_api.intelligence_engine import PHASE2_BOUNDARY, phase2_intelligence_enabled


def test_phase2_boundary_default_off() -> None:
    assert PHASE2_BOUNDARY == "intelligence_engine"
    assert phase2_intelligence_enabled({}) is False
    assert phase2_intelligence_enabled({"crm": True}) is False


def test_phase2_boundary_flags() -> None:
    assert phase2_intelligence_enabled({"intelligence": True}) is True
    assert phase2_intelligence_enabled({"ai_dispatch": True}) is True
