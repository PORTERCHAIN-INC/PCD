"""Lead desk — instant quote, fit score, reply draft, lost reason, speed dashboard.

Registered before `leads_360` so `/leads/speed` doesn't hit `/leads/{lead_id}`.
Nothing here sends a message: drafts and quotes only fill the admin composer.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.collaboration_engine.lead_pipeline import mark_lost, rescore_open_leads
from porterchain_api.config import Settings, get_settings
from porterchain_api.domain.crm_states import LOST_REASONS
from porterchain_api.lead_desk.draft import build_draft
from porterchain_api.lead_desk.fit_score import fit_score
from porterchain_api.lead_desk.quote import QuoteUnavailable, lead_quote
from porterchain_api.lead_desk.speed import speed_dashboard, weekly_summary
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Depends,
    get_admin_context,
    get_db,
    require_module,
    router,
)

_crm = CrmSalesService()


class LeadLostRequest(BaseModel):
    reason: str = Field(description="|".join(LOST_REASONS))
    note: str | None = Field(default=None, max_length=500)


def _lead_or_404(db: Session, lead_id: str):
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    return lead


@router.get("/leads/speed")
def get_lead_speed(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Median first reply, % answered < 5 min, quote→booking, repeat, win rate (7d / 30d)."""
    require_module(ctx, "crm_read")
    return speed_dashboard(db)


@router.get("/leads/weekly-summary")
def get_weekly_summary(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "crm_read")
    return {**weekly_summary(db), "lost_reason_options": list(LOST_REASONS)}


@router.get("/leads/{lead_id}/quote")
def get_lead_quote(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Instant price from PricingService for the lead's postal codes / parcels / vehicle."""
    require_module(ctx, "crm_read")
    lead = _lead_or_404(db, lead_id)
    try:
        return {
            "available": True,
            **lead_quote(db, lead, website_url=settings.website_url),
        }
    except QuoteUnavailable as exc:
        return {"available": False, "reason": str(exc)}


@router.get("/leads/{lead_id}/score")
def get_lead_score(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "crm_read")
    lead = _lead_or_404(db, lead_id)
    cf = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
    stored = cf.get("_score") if isinstance(cf.get("_score"), dict) else {}
    triage = cf.get("triage") if isinstance(cf.get("triage"), dict) else {}
    return {
        **fit_score(lead),
        # Learned from won/lost outcomes once >= 20 leads are closed; else null.
        "predicted_win_pct": stored.get("predictive"),
        "priors_n": stored.get("priors_n") or 0,
        "intent": triage.get("intent"),
    }


@router.get("/leads/{lead_id}/draft")
def get_lead_draft(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    channel: Annotated[str, Query(pattern="^(email|whatsapp)$")] = "email",
    with_quote: bool = True,
) -> dict:
    """Template draft (optional AI polish). Fills the composer; never sends."""
    require_module(ctx, "crm_read")
    lead = _lead_or_404(db, lead_id)
    quote = None
    if with_quote:
        try:
            quote = lead_quote(db, lead, website_url=settings.website_url)
        except QuoteUnavailable:
            quote = None
    sender = (
        getattr(ctx.user, "name", None) or "PorterChain Sales"
    ).strip() or "PorterChain Sales"
    return {
        **build_draft(lead, channel=channel, quote=quote, sender=sender),
        "quote": quote,
    }


@router.post("/leads/rescore")
def rescore_leads(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Recompute fit scores on open leads (local, deterministic; sends nothing)."""
    require_module(ctx, "crm")
    n = rescore_open_leads(db)
    return {"rescored": n}


@router.post("/leads/{lead_id}/lost")
def mark_lead_lost(
    lead_id: str,
    body: LeadLostRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "crm")
    lead = _lead_or_404(db, lead_id)
    try:
        lead = mark_lost(db, lead, body.reason, actor_id=ctx.user.id, note=body.note)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"id": lead.id, "status": lead.status, "lost_reason": lead.lost_reason}
