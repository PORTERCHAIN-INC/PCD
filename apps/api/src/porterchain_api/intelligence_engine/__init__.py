"""Phase 2 intelligence boundary — strategies plug in here (ADR-010)."""

from __future__ import annotations

PHASE2_BOUNDARY = "intelligence_engine"


def phase2_intelligence_enabled(flags: dict[str, bool]) -> bool:
    return bool(flags.get("intelligence") or flags.get("ai_dispatch"))
