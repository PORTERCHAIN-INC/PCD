"""ETA calibration v0 — Phase 2 read-model enrichment (§4.2.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def predict_eta_minutes(
    *,
    distance_km: float,
    duration_min: float,
    flags: dict[str, bool],
    recorded_at: datetime | None = None,
) -> dict[str, Any]:
    """Deterministic baseline until model trained; never on pay path."""
    from porterchain_api.intelligence_engine import phase2_intelligence_enabled

    if not phase2_intelligence_enabled(flags):
        return {
            "eta_minutes": round(duration_min),
            "confidence": 0.5,
            "source": "routing_engine",
            "phase2": False,
        }

    # Phase 2 placeholder: slight calibration bump for urban density
    calibrated = duration_min * (1.0 + min(distance_km, 50.0) * 0.002)
    return {
        "eta_minutes": round(calibrated),
        "confidence": 0.65,
        "source": "eta_calibration_v0_stub",
        "phase2": True,
        "recorded_at": recorded_at.isoformat() if recorded_at else None,
    }
