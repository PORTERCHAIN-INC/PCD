"""Batch assign recommendation — Phase 2 scaffold (§4.2.1).

FROZEN: do not grow this into a real VRP. Day-plan sequencing lives in
``dispatch_engine.sequencer``. This stub stays recommendation-only round-robin.
"""

from __future__ import annotations

from typing import Any

# Jeff Dean freeze — never expand beyond round-robin theater.
_SOLVER_FROZEN = "round_robin_stub_frozen"


def recommend_batch_assignment(
    order_ids: list[str],
    driver_ids: list[str],
    *,
    flags: dict[str, bool],
) -> dict[str, Any]:
    """Admin-only batch recommendation; does not mutate orders."""
    from porterchain_api.intelligence_engine import phase2_intelligence_enabled

    if not phase2_intelligence_enabled(flags):
        return {"assignments": [], "status": "phase2_disabled"}

    assignments: list[dict[str, str]] = []
    for idx, order_id in enumerate(order_ids):
        if not driver_ids:
            break
        assignments.append({"order_id": order_id, "driver_id": driver_ids[idx % len(driver_ids)]})

    return {
        "assignments": assignments,
        "status": "recommendation_only",
        "solver": _SOLVER_FROZEN,
        "human_override_required": True,
        "note": (
            "Frozen stub — use Optimize / day plan for stop order. "
            "Scoring suggestions are also not commit SoT."
        ),
    }
