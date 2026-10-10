"""Pipeline writes: New → Replied → Quoted → Won / Lost (status moves automatically)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmLead
from porterchain_api.domain.crm_states import LOST_REASONS, LeadStatus

_RANK = {"new": 0, "replied": 1, "quoted": 2, "won": 3}


def _now() -> datetime:
    return datetime.now(UTC)


def stamp_status_change(
    lead: CrmLead, new_status: str, *, at: datetime | None = None
) -> None:
    """Keep stage timestamps in step with any status write."""
    now = at or _now()
    if new_status != lead.status:
        lead.legacy_status = (
            None  # the pre-migration value no longer describes this lead
        )
    if new_status == LeadStatus.QUOTED.value and lead.quoted_at is None:
        lead.quoted_at = now
    elif new_status == LeadStatus.WON.value and lead.won_at is None:
        lead.won_at = now
    elif new_status == LeadStatus.LOST.value and lead.lost_at is None:
        lead.lost_at = now


def advance(lead: CrmLead, target: str, *, at: datetime | None = None) -> bool:
    """Move forward only (never downgrades Won/Quoted; Lost/archived re-open on activity)."""
    cur = (lead.status or "new").strip()
    if cur == target:
        return False
    if cur in _RANK and _RANK[cur] >= _RANK.get(target, -1):
        return False
    stamp_status_change(lead, target, at=at)
    lead.status = target
    if target != LeadStatus.LOST.value:
        lead.lost_reason = None
    return True


def mark_quoted(lead: CrmLead, quote: dict[str, Any] | None) -> None:
    advance(lead, LeadStatus.QUOTED.value)
    if quote:
        cf = dict(lead.custom_fields or {})
        cf["last_quote"] = {
            k: quote.get(k)
            for k in (
                "amount_cents",
                "vehicle_class",
                "pickup_fsa",
                "dropoff_fsa",
                "basis",
                "booking_url",
            )
        }
        cf["last_quote"]["sent_at"] = _now().isoformat()
        lead.custom_fields = cf


def mark_won(lead: CrmLead, *, order_id: str | None = None) -> None:
    advance(lead, LeadStatus.WON.value)
    if order_id and not lead.order_id:
        lead.order_id = order_id


def mark_lost(
    db: Session,
    lead: CrmLead,
    reason: str,
    *,
    actor_id: str | None,
    note: str | None = None,
) -> CrmLead:
    r = (reason or "").strip().lower()
    if r not in LOST_REASONS:
        raise ValueError("invalid_lost_reason")
    stamp_status_change(lead, LeadStatus.LOST.value)
    lead.status = LeadStatus.LOST.value
    lead.lost_reason = r
    lead.awaiting_reply = False
    from porterchain_api.crm_models import CrmActivity

    db.add(
        CrmActivity(
            entity_type="lead",
            entity_id=lead.id,
            activity_type="status_change",
            subject=f"Lost: {r.replace('_', ' ')}",
            body=(note or "").strip()[:500] or None,
            actor_id=actor_id,
            metadata_json={"lost_reason": r},
        )
    )
    db.commit()
    db.refresh(lead)
    return lead


def apply_triage(lead: CrmLead, text: str) -> dict[str, Any]:
    """Label the inbound intent and fill missing pricing inputs (never overwrites)."""
    from porterchain_api.lead_desk.triage import triage

    t = triage(text)
    cf = dict(lead.custom_fields or {})
    cf["triage"] = {"intent": t["intent"], "urgent": t["urgent"], "at": _now().isoformat()}
    for key in ("pickup_fsa", "dropoff_fsa", "parcel_count"):
        if t[key] and not cf.get(key):
            cf[key] = t[key]
    if t["vehicle_class"] and not lead.preferred_vehicle:
        lead.preferred_vehicle = t["vehicle_class"]
    lead.custom_fields = cf
    if t["urgent"] and (lead.priority or "medium") in ("low", "medium"):
        lead.priority = "high"
    return t


def rescore_open_leads(db: Session, *, limit: int = 2000) -> int:
    """Recompute the stored fit score on open leads (scores from the old scorer
    or hand-entered values otherwise disagree with the lead page)."""
    from porterchain_api.collaboration_engine.crm_lead_write import CrmLeadWriteMixin

    rows = (
        db.query(CrmLead)
        .filter(CrmLead.status.notin_(("won", "lost", "archived")))
        .order_by(CrmLead.created_at.desc())
        .limit(limit)
        .all()
    )
    for lead in rows:
        lead.lead_score = CrmLeadWriteMixin.score_lead(lead, db=db)
    db.commit()
    return len(rows)


__all__ = [
    "advance",
    "apply_triage",
    "mark_lost",
    "mark_quoted",
    "mark_won",
    "rescore_open_leads",
    "stamp_status_change",
]
