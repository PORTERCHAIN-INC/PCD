"""Model monitoring — drift alerts (§4.2.7)."""

from __future__ import annotations

from typing import Any


def check_model_drift(
    model_name: str,
    *,
    flags: dict[str, bool],
    baseline_mae: float | None = None,
    current_mae: float | None = None,
) -> dict[str, Any]:
    from porterchain_api.intelligence_engine import phase2_intelligence_enabled

    if not phase2_intelligence_enabled(flags):
        return {"model": model_name, "status": "phase2_disabled", "drift": False}

    drift = False
    if baseline_mae is not None and current_mae is not None:
        drift = current_mae > baseline_mae * 1.15

    return {
        "model": model_name,
        "status": "ok",
        "drift": drift,
        "baseline_mae": baseline_mae,
        "current_mae": current_mae,
    }
