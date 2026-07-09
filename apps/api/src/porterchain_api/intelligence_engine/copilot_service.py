"""LLM admin copilot — read-only assist (§4.2.8). Not on pay path."""

from __future__ import annotations

from typing import Any


def suggest_ops_action(
    context: str,
    *,
    flags: dict[str, bool],
) -> dict[str, Any]:
    """Return templated suggestions until LLM wired behind feature flag."""
    from porterchain_api.intelligence_engine import phase2_intelligence_enabled

    if not phase2_intelligence_enabled(flags):
        return {"suggestions": [], "status": "phase2_disabled"}

    return {
        "suggestions": [
            {
                "action": "review_live_map",
                "rationale": "Verify active drivers near exception zone before reassign.",
                "auto_apply": False,
            }
        ],
        "status": "stub",
        "context_preview": context[:200],
    }
