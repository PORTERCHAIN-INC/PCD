"""Demand forecast — admin widget data (§4.2.5)."""

from __future__ import annotations

from typing import Any


def weekly_volume_forecast(
    *,
    flags: dict[str, bool],
    historical_weekly: list[int] | None = None,
) -> dict[str, Any]:
    from porterchain_api.intelligence_engine import phase2_intelligence_enabled

    if not phase2_intelligence_enabled(flags):
        return {"status": "phase2_disabled", "forecast": []}

    history = historical_weekly or []
    baseline = int(sum(history) / len(history)) if history else 0
    return {
        "status": "stub",
        "forecast": [baseline] * 4,
        "model": "moving_average_v0",
    }
