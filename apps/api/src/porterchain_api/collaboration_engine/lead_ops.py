"""Territory assignment + referral credit grants for CRM leads."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.crm_models import (
    CrmConversation,
    CrmLead,
    CrmLeadIdentity,
    CrmReferralCredit,
    CrmSalesTask,
)
from porterchain_api.collaboration_engine.crm_helpers import province_from_postal

logger = logging.getLogger(__name__)


def _territory_map(settings: Settings) -> dict[str, str]:
    raw = (settings.lead_territory_map_json or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("lead_territory_map_json_invalid")
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k).upper(): str(v) for k, v in data.items() if k and v}


def resolve_territory_assignee(lead: CrmLead, settings: Settings | None = None) -> str | None:
    """Map service_area / address.province / FSA → admin_user id."""
    settings = settings or get_settings()
    mapping = _territory_map(settings)
    if not mapping:
        return None
    keys: list[str] = []
    area = (lead.service_area or "").strip().upper()
    if area:
        keys.append(area)
        # Allow substring keys like GTA inside "GTA / Peel"
        for k in mapping:
            if k != "DEFAULT" and k in area:
                keys.append(k)
    addr = lead.address if isinstance(lead.address, dict) else {}
    province = str(addr.get("province") or addr.get("region") or "").strip().upper()
    if province:
        keys.append(province)
    postal = str(addr.get("postal") or addr.get("postal_code") or "").strip()
    if postal:
        prov = province_from_postal(postal)
        if prov:
            keys.append(prov.upper())
    for key in keys:
        if key in mapping:
            return mapping[key]
    return mapping.get("DEFAULT") or mapping.get("default")


def apply_territory_assignment(
    db: Session, lead: CrmLead, settings: Settings | None = None
) -> str | None:
    """Set lead.assigned_to when empty: territory map first, then round-robin pool."""
    if lead.assigned_to:
        return lead.assigned_to
    settings = settings or get_settings()
    assignee = resolve_territory_assignee(lead, settings)
    if not assignee:
        assignee = resolve_round_robin_assignee(settings)
    if assignee:
        lead.assigned_to = assignee
        db.flush()
    return assignee


def resolve_round_robin_assignee(settings: Settings | None = None) -> str | None:
    """Next assignee from LEAD_ROUND_ROBIN_JSON list (Redis counter; hash fallback)."""
    settings = settings or get_settings()
    raw = (settings.lead_round_robin_json or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("lead_round_robin_json_invalid")
        return None
    if not isinstance(parsed, list):
        return None
    pool = [str(x).strip() for x in parsed if str(x).strip()]
    if not pool:
        return None
    idx = 0
    try:
        from porterchain_shared.redis_client import get_redis_client

        client = get_redis_client()
        n = int(client.incr("porterchain:lead:rr:idx"))
        idx = (n - 1) % len(pool)
    except Exception:
        # Deterministic fallback without Redis — rotate by unix minute.
        from time import time

        idx = int(time() // 60) % len(pool)
    return pool[idx]


def sla_minutes_for_channel(channel: str | None, settings: Settings | None = None) -> int:
    """First-response SLA minutes from LEAD_SLA_MINUTES_JSON (per-channel + default)."""
    settings = settings or get_settings()
    default = 60
    raw = (settings.lead_sla_minutes_json or "").strip()
    mapping: dict[str, Any] = {}
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                mapping = parsed
        except json.JSONDecodeError:
            logger.warning("lead_sla_minutes_json_invalid")
    ch = (channel or "").strip().lower()
    for key in (ch, "default", "DEFAULT", "*"):
        if key in mapping:
            try:
                mins = int(mapping[key])
                return max(5, min(mins, 7 * 24 * 60))
            except (TypeError, ValueError):
                continue
    return default


def notify_unassigned_high_priority(db: Session, lead: CrmLead) -> CrmSalesTask | None:
    """Unassigned high/urgent → open follow-up task (staff inbox signal). Flush only."""
    pri = (lead.priority or "").strip().lower()
    if lead.assigned_to or pri not in ("high", "urgent"):
        return None
    existing = (
        db.query(CrmSalesTask)
        .filter(
            CrmSalesTask.entity_type == "lead",
            CrmSalesTask.entity_id == lead.id,
            CrmSalesTask.task_type == "follow_up",
            CrmSalesTask.status.in_(("open", "in_progress")),
        )
        .first()
    )
    if existing:
        return existing
    task = CrmSalesTask(
        title=f"Respond to {pri} lead: {lead.company_name}",
        description="Auto-created: unassigned high/urgent ingest.",
        task_type="follow_up",
        status="open",
        priority=pri,
        entity_type="lead",
        entity_id=lead.id,
        due_at=lead.sla_first_response_due_at,
        created_by="system",
    )
    db.add(task)
    db.flush()
    return task


def grant_referral_credit(
    db: Session,
    *,
    lead: CrmLead,
    company_id: str | None,
    settings: Settings | None = None,
) -> CrmReferralCredit | None:
    """Create pending credit when referred lead converts (idempotent per lead)."""
    settings = settings or get_settings()
    merchant_id = lead.referred_by_merchant_id
    if not merchant_id:
        return None
    existing = (
        db.query(CrmReferralCredit)
        .filter(CrmReferralCredit.lead_id == lead.id)
        .first()
    )
    if existing:
        return existing
    amount = int(settings.referral_credit_cents or 0)
    credit = CrmReferralCredit(
        referring_merchant_id=merchant_id,
        lead_id=lead.id,
        company_id=company_id,
        amount_cents=amount,
        status="pending",
        notes=f"Referral convert: {lead.company_name}",
        granted_at=datetime.now(UTC),
    )
    db.add(credit)
    db.flush()
    return credit


def list_referral_credits(
    db: Session,
    *,
    merchant_id: str | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    q = db.query(CrmReferralCredit)
    if merchant_id:
        q = q.filter(CrmReferralCredit.referring_merchant_id == merchant_id)
    if status:
        q = q.filter(CrmReferralCredit.status == status)
    rows = q.order_by(CrmReferralCredit.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "merchant_id": r.referring_merchant_id,
            "referring_merchant_id": r.referring_merchant_id,
            "lead_id": r.lead_id,
            "company_id": r.company_id,
            "amount_cents": r.amount_cents,
            "currency": "CAD",
            "status": r.status,
            "notes": r.notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "granted_at": r.granted_at.isoformat() if r.granted_at else None,
        }
        for r in rows
    ]


def list_referred_leads(
    db: Session,
    *,
    merchant_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = (
        db.query(CrmLead)
        .filter(CrmLead.referred_by_merchant_id == merchant_id)
        .order_by(CrmLead.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": lead.id,
            "company_name": lead.company_name,
            "primary_contact_name": lead.primary_contact_name,
            "email": lead.email,
            "status": lead.status,
            "decision_status": lead.decision_status,
            "channel": lead.channel,
            "lead_score": lead.lead_score,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
        }
        for lead in rows
    ]


def merchant_referral_overview(
    db: Session,
    *,
    merchant_id: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Share link + credit amount + credits + referred leads for merchant portal."""
    settings = settings or get_settings()
    website = (settings.website_url or "http://localhost:3000").rstrip("/")
    share_url = (
        f"{website}/sign-up?intent=quote&from=merchant_referral"
        f"&ref={merchant_id}"
    )
    return {
        "merchant_id": merchant_id,
        "share_url": share_url,
        "credit_cents": int(settings.referral_credit_cents or 0),
        "currency": "CAD",
        "credits": list_referral_credits(db, merchant_id=merchant_id, limit=100),
        "referred_leads": list_referred_leads(db, merchant_id=merchant_id),
    }


def resolve_merge_candidate(
    db: Session,
    *,
    lead_id: str,
    action: str,
    actor_id: str | None = None,
) -> CrmLead:
    """Accept (fold into target) or reject (clear link) a soft merge candidate."""
    from porterchain_api.collaboration_engine.crm_activity import CrmActivityMixin
    from porterchain_api.domain.crm_states import LeadStatus

    lead = db.get(CrmLead, lead_id)
    if not lead:
        raise LookupError("lead_not_found")
    target_id = lead.merge_candidate_of
    if not target_id:
        raise ValueError("not_a_merge_candidate")
    action = (action or "").strip().lower()
    if action not in ("accept", "reject"):
        raise ValueError("invalid_merge_action")

    if action == "reject":
        lead.merge_candidate_of = None
        db.flush()
        CrmActivityMixin().log_activity(
            db,
            entity_type="lead",
            entity_id=lead.id,
            activity_type="system",
            subject="Merge candidate rejected",
            actor_id=actor_id,
            metadata={"target_id": target_id, "action": "reject"},
            commit=False,
        )
        db.commit()
        db.refresh(lead)
        return lead

    target = db.get(CrmLead, target_id)
    if not target:
        lead.merge_candidate_of = None
        db.flush()
        raise LookupError("merge_target_not_found")

    # Fold identities onto target.
    for ident in (
        db.query(CrmLeadIdentity).filter(CrmLeadIdentity.lead_id == lead.id).all()
    ):
        exists = (
            db.query(CrmLeadIdentity)
            .filter(
                CrmLeadIdentity.kind == ident.kind,
                CrmLeadIdentity.value_normalized == ident.value_normalized,
            )
            .first()
        )
        if exists:
            if exists.lead_id != target.id:
                # Collision with another lead — keep as-is on source; skip move.
                continue
            continue
        ident.lead_id = target.id
        db.flush()

    # Move open conversations.
    for convo in (
        db.query(CrmConversation).filter(CrmConversation.lead_id == lead.id).all()
    ):
        convo.lead_id = target.id

    # Enrich target without wiping richer fields.
    if lead.email and not target.email:
        target.email = lead.email
    if lead.phone and not target.phone:
        target.phone = lead.phone
    if lead.primary_contact_name and not target.primary_contact_name:
        target.primary_contact_name = lead.primary_contact_name
    if lead.internal_notes:
        notes = (target.internal_notes or "").strip()
        extra = lead.internal_notes.strip()
        target.internal_notes = f"{notes}\n[Merged] {extra}".strip() if notes else f"[Merged] {extra}"
    cf = dict(target.custom_fields or {})
    cf.update({k: v for k, v in (lead.custom_fields or {}).items() if v not in (None, "")})
    target.custom_fields = cf
    consent = dict(target.consent or {})
    consent.update({k: v for k, v in (lead.consent or {}).items() if v})
    target.consent = consent

    lead.merge_candidate_of = None
    lead.status = LeadStatus.UNQUALIFIED.value
    tags = list(lead.tags or [])
    if "merged_away" not in tags:
        tags.append("merged_away")
    lead.tags = tags
    lead.internal_notes = (
        f"{(lead.internal_notes or '').strip()}\n[Merged into {target.id}]".strip()
    )

    db.flush()
    CrmActivityMixin().log_activity(
        db,
        entity_type="lead",
        entity_id=target.id,
        activity_type="system",
        subject=f"Merged lead {lead.id} into this record",
        actor_id=actor_id,
        metadata={"source_lead_id": lead.id, "action": "accept"},
        commit=False,
    )
    CrmActivityMixin().log_activity(
        db,
        entity_type="lead",
        entity_id=lead.id,
        activity_type="system",
        subject=f"Merged into {target.id}",
        actor_id=actor_id,
        metadata={"target_id": target.id, "action": "accept"},
        commit=False,
    )
    db.commit()
    db.refresh(target)
    return target


def lead_ingest_config_status(settings: Settings) -> dict[str, bool]:
    """Boolean readiness for lead webhook / CAPI / territory keys (never values)."""
    return {
        "public_ingest": bool((settings.public_ingest_api_key or "").strip()),
        "meta_webhooks": bool(
            (settings.meta_app_secret or "").strip()
            and (settings.meta_webhook_verify_token or "").strip()
        ),
        "google_webhooks": bool((settings.google_lead_webhook_secret or "").strip()),
        "social_webhooks": bool((settings.social_lead_webhook_secret or "").strip()),
        "meta_capi": bool(
            (settings.meta_capi_access_token or "").strip()
            and (settings.meta_pixel_id or "").strip()
        ),
        "linkedin_capi": bool(
            (settings.linkedin_capi_token or "").strip()
            and (settings.linkedin_conversion_urn or "").strip()
        ),
        "territory_map": bool((settings.lead_territory_map_json or "").strip()),
        "round_robin": bool((settings.lead_round_robin_json or "").strip()),
        "referral_credits": int(settings.referral_credit_cents or 0) > 0,
        "sla_minutes_map": bool((settings.lead_sla_minutes_json or "").strip()),
    }


__all__ = [
    "apply_territory_assignment",
    "grant_referral_credit",
    "lead_ingest_config_status",
    "list_referral_credits",
    "list_referred_leads",
    "merchant_referral_overview",
    "notify_unassigned_high_priority",
    "resolve_merge_candidate",
    "resolve_round_robin_assignee",
    "resolve_territory_assignee",
    "sla_minutes_for_channel",
]
