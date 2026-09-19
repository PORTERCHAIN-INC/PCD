"""Dispatch scorer — admin recommendation only (§4.2.6)."""

from __future__ import annotations

from typing import Any


def score_driver_candidates(
    order_id: str,
    candidate_driver_ids: list[str],
    *,
    flags: dict[str, bool],
) -> dict[str, Any]:
    """Rank drivers for admin override UI; never auto-assign."""
    from porterchain_api.intelligence_engine import phase2_intelligence_enabled

    if not phase2_intelligence_enabled(flags):
        return {
            "order_id": order_id,
            "recommendations": [],
            "status": "phase2_disabled",
        }

    ranked = [
        {"driver_id": driver_id, "score": max(0.1, 1.0 - (idx * 0.05))}
        for idx, driver_id in enumerate(candidate_driver_ids)
    ]
    return {
        "order_id": order_id,
        "recommendations": ranked,
        "status": "recommendation_only",
        "human_override_required": True,
    }
