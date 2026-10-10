"""Lead agent activity board — what the zero-human agent is doing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.lead_nba import _WELCOME_TAG, lead_next_best_action
from porterchain_api.crm_models import CrmLead
from porterchain_api.domain.crm_states import LeadStatus


def _agent_bag(lead: CrmLead) -> dict[str, Any]:
    if isinstance(lead.custom_fields, dict):
        raw = lead.custom_fields.get("lead_agent")
        if isinstance(raw, dict):
            return raw
    return {}


def _row(db: Session, lead: CrmLead, *, include_nba: bool = False) -> dict[str, Any]:
    bag = _agent_bag(lead)
    city = None
    if isinstance(lead.address, dict):
        city = lead.address.get("city")
    row: dict[str, Any] = {
        "id": lead.id,
        "company_name": lead.company_name,
        "email": lead.email,
        "phone": lead.phone,
        "source": lead.source,
        "channel": lead.channel,
        "status": lead.status,
        "priority": lead.priority,
        "city": city or lead.service_area,
        "tags": list(lead.tags or []),
        "marketing_consent": bool((lead.consent or {}).get("marketing")),
        "agent_status": bag.get("status"),
        "last_channel": bag.get("last_channel"),
        "last_send_at": bag.get("last_send_at"),
        "last_trigger": bag.get("last_trigger"),
        "blocks": bag.get("blocks") or [],
        "reason": bag.get("reason"),
        "welcomed": _WELCOME_TAG in (lead.tags or []),
        "needs_enrich": "needs_enrich" in (lead.tags or [])
        or bag.get("status") in ("needs_enrich", "enrich_failed"),
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
        "assigned": bool(lead.assigned_to),
    }
    if include_nba:
        row["nba"] = lead_next_best_action(db, lead)
    return row


_OPEN_STATUSES = (
    LeadStatus.NEW.value,
    LeadStatus.CONTACTED.value,
    LeadStatus.QUALIFIED.value,
    LeadStatus.NURTURING.value,
)
_INBOX_LIMIT = 200


def _notice(db: Session, lead: CrmLead, *, kind: str) -> dict[str, Any]:
    """Staff notice copy shown on Lead Agent Inbox."""
    priority = (lead.priority or "medium").strip().lower() or "medium"
    company = lead.company_name or lead.id
    if kind == "sla":
        subject = f"SLA breached {priority} lead: {company}"
        body = (
            f"Lead {lead.id} ({company}) is past first response at {priority} priority. "
            f"Source: {lead.source or '—'} / {lead.channel or '—'}."
        )
    else:
        subject = f"{company} — unassigned high lead"
        body = f"{company} is unassigned. Open the lead in Lead Agent."
    row = _row(db, lead)
    row["notice_kind"] = kind
    row["notice_subject"] = subject
    row["notice_body"] = body
    return row


def _internal_inbox(db: Session) -> dict[str, Any]:
    """Unassigned open leads plus the staff notices that no longer send email."""
    now = datetime.now(UTC)
    unassigned_q = db.query(CrmLead).filter(
        CrmLead.assigned_to.is_(None),
        CrmLead.status.in_(_OPEN_STATUSES),
    )
    unassigned = (
        unassigned_q.order_by(CrmLead.created_at.desc()).limit(_INBOX_LIMIT).all()
    )
    sla_rows = (
        db.query(CrmLead)
        .filter(
            CrmLead.status == LeadStatus.NEW.value,
            CrmLead.sla_first_response_due_at.isnot(None),
            CrmLead.sla_first_response_due_at < now,
        )
        .order_by(CrmLead.sla_first_response_due_at.asc())
        .limit(_INBOX_LIMIT)
        .all()
    )
    hot_unassigned = (
        db.query(CrmLead)
        .filter(
            CrmLead.assigned_to.is_(None),
            CrmLead.status.in_(_OPEN_STATUSES),
            CrmLead.priority.in_(("high", "urgent")),
        )
        .order_by(CrmLead.created_at.desc())
        .limit(_INBOX_LIMIT)
        .all()
    )
    sla_count = (
        db.query(func.count(CrmLead.id))
        .filter(
            CrmLead.status == LeadStatus.NEW.value,
            CrmLead.sla_first_response_due_at.isnot(None),
            CrmLead.sla_first_response_due_at < now,
        )
        .scalar()
        or 0
    )
    hot_count = (
        db.query(func.count(CrmLead.id))
        .filter(
            CrmLead.assigned_to.is_(None),
            CrmLead.status.in_(_OPEN_STATUSES),
            CrmLead.priority.in_(("high", "urgent")),
        )
        .scalar()
        or 0
    )
    notices = [_notice(db, lead, kind="sla") for lead in sla_rows]
    notices.extend(_notice(db, lead, kind="unassigned") for lead in hot_unassigned)
    return {
        "unassigned_count": unassigned_q.count(),
        "notices_count": int(sla_count) + int(hot_count),
        "unassigned": [_row(db, lead) for lead in unassigned],
        "notices": notices,
    }


def lead_agent_activity(db: Session, *, lane_limit: int = 40) -> dict[str, Any]:
    """Dashboard payload: config + counts + lanes of agent work."""
    from porterchain_api.collaboration_engine.lead_whatsapp_cloud import (
        whatsapp_cloud_configured,
    )
    from porterchain_api.config import get_settings

    settings = get_settings()
    auto = bool(getattr(settings, "lead_agent_auto_send", True))

    welcomed_q = db.query(CrmLead).filter(cast(CrmLead.tags, String).ilike(f"%{_WELCOME_TAG}%"))
    needs_enrich_q = db.query(CrmLead).filter(
        or_(
            cast(CrmLead.tags, String).ilike("%needs_enrich%"),
            cast(CrmLead.custom_fields, String).ilike("%needs_enrich%"),
            cast(CrmLead.custom_fields, String).ilike("%enrich_failed%"),
        ),
        CrmLead.status == LeadStatus.NEW.value,
    )
    # Consented inbound still waiting (email present, marketing, not welcomed)
    awaiting_q = db.query(CrmLead).filter(
        CrmLead.status == LeadStatus.NEW.value,
        CrmLead.email.isnot(None),
        CrmLead.email != "",
        cast(CrmLead.consent, String).ilike("%marketing%true%"),
        ~cast(CrmLead.tags, String).ilike(f"%{_WELCOME_TAG}%"),
    )
    blocked_q = db.query(CrmLead).filter(
        cast(CrmLead.custom_fields, String).ilike("%\"status\": \"blocked\"%"),
        CrmLead.status == LeadStatus.NEW.value,
    )

    welcomed = (
        welcomed_q.order_by(CrmLead.updated_at.desc()).limit(lane_limit).all()
    )
    needs_enrich = (
        needs_enrich_q.order_by(CrmLead.updated_at.desc()).limit(lane_limit).all()
    )
    awaiting = awaiting_q.order_by(CrmLead.created_at.asc()).limit(lane_limit).all()
    blocked = blocked_q.order_by(CrmLead.updated_at.desc()).limit(lane_limit).all()

    # Recent agent activity by custom_fields last_send_at presence
    recent = (
        db.query(CrmLead)
        .filter(cast(CrmLead.custom_fields, String).ilike("%lead_agent%"))
        .order_by(CrmLead.updated_at.desc())
        .limit(lane_limit)
        .all()
    )
    inbox = _internal_inbox(db)

    return {
        "config": {
            "auto_send_enabled": auto,
            "whatsapp_cloud_configured": whatsapp_cloud_configured(),
            "kill_switch_env": "LEAD_AGENT_AUTO_SEND",
            "internal_email": False,
        },
        "counts": {
            "welcomed": welcomed_q.count(),
            "needs_enrich": needs_enrich_q.count(),
            "awaiting_welcome": awaiting_q.count(),
            "blocked": blocked_q.count(),
            "new_total": db.query(func.count(CrmLead.id))
            .filter(CrmLead.status == LeadStatus.NEW.value)
            .scalar()
            or 0,
            "unassigned": inbox["unassigned_count"],
            "notices": inbox["notices_count"],
        },
        "inbox": {
            "unassigned": inbox["unassigned"],
            "notices": inbox["notices"],
        },
        "lanes": {
            "welcomed": [_row(db, r) for r in welcomed],
            "needs_enrich": [_row(db, r) for r in needs_enrich],
            "awaiting_welcome": [_row(db, r) for r in awaiting],
            "blocked": [_row(db, r) for r in blocked],
            "recent": [_row(db, r) for r in recent],
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }


__all__ = ["lead_agent_activity"]
