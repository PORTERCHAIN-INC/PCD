"""ESP engagement → lead score (open / click webhooks)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmLead

logger = logging.getLogger(__name__)

EngagementKind = Literal["open", "click"]

_SCORE_DELTA = {"open": 2, "click": 5}
_MAX_ENGAGEMENT_BOOST = 15


def apply_email_engagement(
    db: Session,
    lead: CrmLead,
    *,
    kind: EngagementKind,
    campaign: str | None = None,
    actor: str = "esp",
) -> dict[str, Any]:
    """Record nurture/ESP open|click and bump lead_score (capped)."""
    if kind not in _SCORE_DELTA:
        raise ValueError("invalid_engagement_kind")

    fields = dict(lead.custom_fields) if isinstance(lead.custom_fields, dict) else {}
    eng = dict(fields.get("_engagement") or {}) if isinstance(fields.get("_engagement"), dict) else {}
    opens = int(eng.get("opens") or 0)
    clicks = int(eng.get("clicks") or 0)
    boost = int(eng.get("score_boost") or 0)
    delta = _SCORE_DELTA[kind]
    if boost + delta > _MAX_ENGAGEMENT_BOOST:
        delta = max(0, _MAX_ENGAGEMENT_BOOST - boost)

    if kind == "open":
        opens += 1
    else:
        clicks += 1
    boost += delta
    eng.update(
        {
            "opens": opens,
            "clicks": clicks,
            "score_boost": boost,
            "last_kind": kind,
            "last_at": datetime.now(UTC).isoformat(),
            "last_campaign": (campaign or "")[:120] or None,
            "actor": actor,
        }
    )
    fields["_engagement"] = eng
    lead.custom_fields = fields
    lead.last_touch_at = datetime.now(UTC)
    if delta:
        lead.lead_score = min(100, int(lead.lead_score or 0) + delta)

    try:
        from porterchain_api.platform.lead_events import LEAD_ENGAGEMENT, emit_lead_event

        emit_lead_event(
            db,
            event_type=LEAD_ENGAGEMENT,
            lead_id=lead.id,
            actor_type="system",
            actor_id=actor,
            payload={"kind": kind, "campaign": campaign, "delta": delta, "score": lead.lead_score},
        )
    except Exception:
        logger.exception("lead_engagement_event_failed lead=%s", lead.id)

    db.flush()
    return {
        "lead_id": lead.id,
        "kind": kind,
        "delta": delta,
        "lead_score": lead.lead_score,
        "engagement": eng,
    }


def record_email_engagement(
    db: Session,
    lead: CrmLead,
    *,
    kind: EngagementKind,
    campaign: str | None = None,
    actor: str = "esp",
) -> dict[str, Any]:
    """Apply engagement scoring and commit (public router UoW)."""
    out = apply_email_engagement(db, lead, kind=kind, campaign=campaign, actor=actor)
    db.commit()
    return out


__all__ = ["apply_email_engagement", "record_email_engagement"]
