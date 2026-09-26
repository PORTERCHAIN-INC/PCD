"""Admin outbound lead dial / agent routes — split from leads.py (D2 §0.3.9)."""

from __future__ import annotations

from typing import Annotated

from fastapi import HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.config import Settings, get_settings
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Depends,
    get_admin_context,
    get_db,
    require_module,
    router,
)
from porterchain_api.schemas_crm import LeadOut

_crm = CrmSalesService()


@router.get("/leads/today")
def leads_today_queues(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Outbound dial packs: ready / followups / interested (full lists, no pagination)."""
    require_module(ctx, "crm_read")
    from porterchain_api.collaboration_engine.lead_dial import today_queues

    return today_queues(db)


@router.get("/leads/agent")
def leads_agent_activity(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    lane_limit: int = Query(40, ge=5, le=100),
) -> dict:
    """Zero-human lead agent board — welcomed / enrich / awaiting / blocked."""
    require_module(ctx, "crm_read")
    from porterchain_api.collaboration_engine.lead_agent_activity import lead_agent_activity

    return lead_agent_activity(db, lane_limit=lane_limit)


class CallDispositionRequest(BaseModel):
    outcome: str
    notes: str | None = None
    loss_reason: str | None = None
    next_action: str | None = None
    follow_up_at: str | None = None
    queue: str = "ready"
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    consent_marketing: bool | None = None


@router.post("/leads/{lead_id}/call-disposition")
def call_disposition(
    lead_id: str,
    body: CallDispositionRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Log outbound call outcome + optional contact capture; return next lead id."""
    require_module(ctx, "crm")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    from datetime import datetime

    from porterchain_api.collaboration_engine.lead_dial import apply_call_disposition

    due = None
    if body.follow_up_at:
        try:
            due = datetime.fromisoformat(body.follow_up_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid_follow_up_at") from exc
    try:
        result = apply_call_disposition(
            db,
            _crm,
            lead=lead,
            outcome=body.outcome,
            notes=body.notes,
            loss_reason=body.loss_reason,
            next_action=body.next_action,
            follow_up_at=due,
            actor_id=ctx.user.id,
            queue=body.queue,
            contact_name=body.contact_name,
            email=body.email,
            phone=body.phone,
            consent_marketing=body.consent_marketing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "lead": LeadOut.model_validate(result["lead"]).model_dump(mode="json"),
        "outcome": result["outcome"],
        "status": result["status"],
        "task_id": result.get("task_id"),
        "next_lead_id": result.get("next_lead_id"),
    }


@router.get("/leads/{lead_id}/dial-scripts")
def lead_dial_scripts(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "crm_read")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    from porterchain_api.collaboration_engine.dial_scripts import outbound_call_scripts

    city = None
    if isinstance(lead.address, dict):
        city = lead.address.get("city") or lead.service_area
    else:
        city = lead.service_area
    return outbound_call_scripts(company_name=lead.company_name, city=city)


class LeadSendEmailRequest(BaseModel):
    template_key: str = "lead_outbound_followup"


@router.post("/leads/{lead_id}/send-email")
def send_lead_email(
    lead_id: str,
    body: LeadSendEmailRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Template email from lead — requires email + marketing consent + not suppressed."""
    require_module(ctx, "crm")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    from porterchain_api.collaboration_engine.lead_outbound_email import enqueue_lead_template_email

    try:
        return enqueue_lead_template_email(
            db,
            _crm,
            lead=lead,
            template_key=body.template_key,
            actor_id=ctx.user.id,
            website_url=getattr(settings, "website_url", None) or "https://porterchain.com",
            jwt_secret=settings.jwt_secret or settings.public_ingest_api_key or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


class LeadWelcomeRequest(BaseModel):
    force: bool = False
    dry_run: bool = False


@router.post("/leads/{lead_id}/welcome")
def welcome_lead(
    lead_id: str,
    body: LeadWelcomeRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Zero-human agent welcome (email / WA when configured). Staff can force re-run."""
    require_module(ctx, "crm")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    from porterchain_api.collaboration_engine.lead_agent import staff_welcome_lead

    return staff_welcome_lead(
        db,
        lead,
        website_url=getattr(settings, "website_url", "") or "",
        force=body.force,
        dry_run=body.dry_run,
    )


@router.get("/leads/{lead_id}/nba")
def lead_nba(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Next-best-action + agent status for Dial / Lead360."""
    require_module(ctx, "crm_read")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    from porterchain_api.collaboration_engine.lead_nba import lead_next_best_action

    nba = lead_next_best_action(db, lead)
    agent_cf = {}
    if isinstance(lead.custom_fields, dict):
        raw = lead.custom_fields.get("lead_agent")
        if isinstance(raw, dict):
            agent_cf = raw
    return {"nba": nba, "agent": agent_cf}
