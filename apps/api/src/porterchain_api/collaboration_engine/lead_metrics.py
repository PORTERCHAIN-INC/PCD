"""Lead funnel / SLA / identity / CAPI coverage metrics (Leaf 4 observability)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmLead, CrmLeadIdentity, CrmLeadIngestEvent
from porterchain_api.domain.crm_states import LeadIdentityKind, LeadStatus


def lead_channel_metrics(db: Session, *, days: int = 30) -> dict[str, Any]:
    """Fan-in funnel + SLA + identity coverage for the sales workbench."""
    days = max(1, min(int(days), 365))
    since = datetime.now(UTC) - timedelta(days=days)
    now = datetime.now(UTC)

    ingest_total = (
        db.query(func.count(CrmLeadIngestEvent.id))
        .filter(CrmLeadIngestEvent.created_at >= since)
        .scalar()
        or 0
    )
    ingest_by_channel = (
        db.query(CrmLeadIngestEvent.channel, func.count(CrmLeadIngestEvent.id))
        .filter(CrmLeadIngestEvent.created_at >= since)
        .group_by(CrmLeadIngestEvent.channel)
        .all()
    )

    lead_total = (
        db.query(func.count(CrmLead.id)).filter(CrmLead.created_at >= since).scalar() or 0
    )

    by_channel_status = (
        db.query(CrmLead.channel, CrmLead.status, func.count(CrmLead.id))
        .filter(CrmLead.created_at >= since)
        .group_by(CrmLead.channel, CrmLead.status)
        .all()
    )
    funnel: dict[str, dict[str, int]] = {}
    for channel, status, count in by_channel_status:
        ch = (channel or "unknown").strip() or "unknown"
        funnel.setdefault(ch, {})
        funnel[ch][status or "unknown"] = int(count)

    by_channel_decision = (
        db.query(CrmLead.channel, CrmLead.decision_status, func.count(CrmLead.id))
        .filter(CrmLead.created_at >= since)
        .group_by(CrmLead.channel, CrmLead.decision_status)
        .all()
    )
    decision_funnel: dict[str, dict[str, int]] = {}
    for channel, decision, count in by_channel_decision:
        ch = (channel or "unknown").strip() or "unknown"
        decision_funnel.setdefault(ch, {})
        decision_funnel[ch][decision or "unknown"] = int(count)

    converted = (
        db.query(func.count(CrmLead.id))
        .filter(CrmLead.created_at >= since, CrmLead.status == LeadStatus.CONVERTED.value)
        .scalar()
        or 0
    )
    merge_candidates = (
        db.query(func.count(CrmLead.id))
        .filter(CrmLead.merge_candidate_of.isnot(None), CrmLead.created_at >= since)
        .scalar()
        or 0
    )
    soft_dup_rate = round(100.0 * merge_candidates / max(1, lead_total), 1)

    sla_breached = (
        db.query(func.count(CrmLead.id))
        .filter(
            CrmLead.sla_first_response_due_at.isnot(None),
            CrmLead.sla_first_response_due_at < now,
            CrmLead.status == LeadStatus.NEW.value,
        )
        .scalar()
        or 0
    )
    sla_open = (
        db.query(func.count(CrmLead.id))
        .filter(
            CrmLead.sla_first_response_due_at.isnot(None),
            CrmLead.status == LeadStatus.NEW.value,
        )
        .scalar()
        or 0
    )

    touched = (
        db.query(CrmLead.created_at, CrmLead.last_touch_at, CrmLead.channel)
        .filter(
            CrmLead.created_at >= since,
            CrmLead.last_touch_at.isnot(None),
            CrmLead.last_touch_at > CrmLead.created_at,
        )
        .all()
    )
    deltas_by_channel: dict[str, list[float]] = {}
    all_deltas: list[float] = []
    for created, touched_at, channel in touched:
        if not created or not touched_at:
            continue
        mins = (touched_at - created).total_seconds() / 60.0
        if mins < 0:
            continue
        ch = (channel or "unknown").strip() or "unknown"
        deltas_by_channel.setdefault(ch, []).append(mins)
        all_deltas.append(mins)

    def _median(vals: list[float]) -> float | None:
        if not vals:
            return None
        s = sorted(vals)
        mid = len(s) // 2
        if len(s) % 2:
            return round(s[mid], 1)
        return round((s[mid - 1] + s[mid]) / 2.0, 1)

    meta_leads = (
        db.query(func.count(func.distinct(CrmLeadIdentity.lead_id)))
        .filter(CrmLeadIdentity.kind == LeadIdentityKind.META_LEAD_ID.value)
        .scalar()
        or 0
    )
    facebookish = (
        db.query(func.count(CrmLead.id))
        .filter(
            CrmLead.created_at >= since,
            CrmLead.channel.in_(("facebook", "instagram", "whatsapp")),
        )
        .scalar()
        or 0
    )

    assist_total = 0
    assist_accept = 0
    assist_reject = 0
    merge_accept = 0
    merge_reject = 0
    try:
        from porterchain_api.crm_models import CrmActivity
        from porterchain_api.intelligence_engine.usage_models import AiUsageLog

        assist_total = (
            db.query(func.count(AiUsageLog.id))
            .filter(
                AiUsageLog.feature == "lead_assist",
                AiUsageLog.created_at >= since,
            )
            .scalar()
            or 0
        )
        # Activity metadata JSON — Postgres JSON operators via cast text search fallback.
        acts = (
            db.query(CrmActivity)
            .filter(
                CrmActivity.created_at >= since,
                CrmActivity.entity_type == "lead",
            )
            .limit(5000)
            .all()
        )
        for a in acts:
            meta = a.metadata_json or {}
            if meta.get("from_assist"):
                if meta.get("assist_decision") == "accept":
                    assist_accept += 1
                elif meta.get("assist_decision") == "reject":
                    assist_reject += 1
            if meta.get("action") == "accept" and meta.get("source_lead_id"):
                merge_accept += 1
            if meta.get("action") == "reject" and meta.get("target_id") and not meta.get("source_lead_id"):
                # reject stores target_id only
                if (a.subject or "").startswith("Merge candidate rejected"):
                    merge_reject += 1
    except Exception:
        assist_total = 0

    return {
        "window_days": days,
        "ingest": {
            "total": int(ingest_total),
            "by_channel": {(c or "unknown"): int(n) for c, n in ingest_by_channel if n},
        },
        "leads": {
            "total": int(lead_total),
            "converted": int(converted),
            "conversion_rate": round(100.0 * converted / max(1, lead_total), 1),
            "merge_candidates": int(merge_candidates),
            "soft_duplicate_rate_pct": soft_dup_rate,
            "merge_accept": int(merge_accept),
            "merge_reject": int(merge_reject),
            "funnel_by_channel": funnel,
            "decision_funnel_by_channel": decision_funnel,
        },
        "sla": {
            "open_new_with_due": int(sla_open),
            "breached_new": int(sla_breached),
            "median_first_touch_minutes": _median(all_deltas),
            "median_first_touch_by_channel": {
                ch: _median(vals) for ch, vals in deltas_by_channel.items()
            },
        },
        "capi": {
            "meta_lead_id_leads": int(meta_leads),
            "meta_family_leads_window": int(facebookish),
            "meta_lead_id_coverage_pct": (
                round(100.0 * meta_leads / max(1, facebookish), 1) if facebookish else None
            ),
        },
        "assist": {
            "nim_calls": int(assist_total),
            "accepted": int(assist_accept),
            "rejected": int(assist_reject),
            "accept_rate_pct": (
                round(100.0 * assist_accept / max(1, assist_accept + assist_reject), 1)
                if (assist_accept + assist_reject)
                else None
            ),
        },
    }


__all__ = ["lead_channel_metrics"]
