"""First-party visitor / guide intent scoring (domain — no engine imports)."""

from __future__ import annotations

from typing import Any, Protocol


class _LeadLike(Protocol):
    custom_fields: Any


class _VisitorLike(Protocol):
    intent_score: Any
    quote_generated: Any


def behavioral_score_boost(lead: _LeadLike, visitor: _VisitorLike | None = None) -> int:
    """Extra CRM points from guide/visitor signals (capped by caller)."""
    boost = 0
    fields = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
    intent = str(fields.get("intent") or "").lower()
    if intent in {"quote", "call", "meeting", "demo", "book"}:
        boost += 15
    elif intent:
        boost += 5
    transcript = fields.get("transcript")
    if isinstance(transcript, list):
        if len(transcript) >= 6:
            boost += 12
        elif len(transcript) >= 2:
            boost += 6
    if fields.get("appointment") or fields.get("appointment_id"):
        boost += 15
    if fields.get("form") == "capacity_guide":
        boost += 5
    if visitor is not None:
        boost += min(int(getattr(visitor, "intent_score", 0) or 0) // 4, 20)
        if getattr(visitor, "quote_generated", False):
            boost += 10
    return boost


def compute_intent_score(
    *,
    signals: dict[str, Any] | None,
    quote_generated: bool,
    touch_count: int,
    has_utm: bool,
) -> int:
    """First-party intent score 0–100 (no fingerprinting)."""
    score = 0
    sig = signals or {}
    page_views = sig.get("page_view_count") if isinstance(sig.get("page_view_count"), int) else 0
    paths = sig.get("paths") if isinstance(sig.get("paths"), list) else []
    intent = str(sig.get("intent") or "").lower()
    guide_stage = str(sig.get("guide_stage") or "").lower()
    from_page = str(sig.get("from_page") or sig.get("source_page") or "").lower()

    if page_views >= 8:
        score += 15
    elif page_views >= 3:
        score += 10
    elif page_views >= 1:
        score += 5

    if len(paths) >= 5:
        score += 10
    elif len(paths) >= 2:
        score += 5

    if has_utm:
        score += 8
    if touch_count >= 3:
        score += 5

    high_intent = {"quote", "call", "meeting", "demo", "book"}
    if intent in high_intent:
        score += 25
    elif intent:
        score += 10

    stage_points = {
        "discover": 5,
        "qualify": 12,
        "capture": 20,
        "book": 28,
        "handoff": 22,
    }
    score += stage_points.get(guide_stage, 0)

    commercial_paths = (
        "business",
        "sign-up",
        "pricing",
        "how-it-works",
        "solutions",
        "customers",
        "vehicle-partner",
    )
    if any(any(token in str(p).lower() for token in commercial_paths) for p in paths):
        score += 10
    if any(token in from_page for token in ("business", "quote", "hero", "cta", "nav")):
        score += 5

    if quote_generated:
        score += 30

    return min(score, 100)
