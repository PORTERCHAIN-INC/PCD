"""Unified lead inbox — reply (email / WhatsApp), log a call, bulk edit, CSV export.

Registered before `leads_360` so `/leads/export.csv` etc. don't hit `/leads/{lead_id}`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.collaboration_engine.lead_inbox import (
    leads_by_ids,
    CALL_OUTCOMES,
    ReplyError,
    bulk_update,
    leads_to_csv,
    log_call,
    reply_channels,
    send_lead_reply,
)
from porterchain_api.config import Settings, get_settings
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Depends,
    get_admin_context,
    get_db,
    require_module,
    router,
)

_crm = CrmSalesService()
EXPORT_MAX_ROWS = 5000


class LeadReplyRequest(BaseModel):
    channel: str = Field(description="email | whatsapp")
    body: str = Field(min_length=1, max_length=10_000)
    subject: str | None = Field(default=None, max_length=200)
    #: Attach the lead's instant quote (recomputed server-side) → lead moves to Quoted.
    attach_quote: bool = False


class LeadLogCallRequest(BaseModel):
    direction: str = Field(description="inbound | outbound")
    outcome: str
    notes: str | None = Field(default=None, max_length=4000)
    duration_minutes: int | None = Field(default=None, ge=0, le=600)
    follow_up_at: datetime | None = None


class LeadBulkRequest(BaseModel):
    lead_ids: list[str] = Field(min_length=1, max_length=500)
    assigned_to: str | None = Field(default=None, max_length=36)
    unassign: bool = False
    status: str | None = None
    priority: str | None = None


def _raise(exc: ReplyError) -> None:
    raise HTTPException(status_code=exc.status, detail=exc.code) from exc


def _lead_or_404(db: Session, lead_id: str):
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    return lead


@router.get("/leads/reply-channels")
def get_reply_channels(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    settings: Settings = Depends(get_settings),
) -> dict:
    """Which reply channels are configured (drives the composer's disabled state)."""
    require_module(ctx, "crm_read")
    return {**reply_channels(settings), "call_outcomes": list(CALL_OUTCOMES)}


@router.get("/leads/export.csv")
def export_leads_csv(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    priority: str | None = None,
    channel: str | None = None,
    intent_type: str | None = None,
    assigned_to: str | None = None,
    unassigned: bool | None = None,
    sla_breached: bool | None = None,
    awaiting_reply: bool | None = None,
    view: str | None = None,
    search: str | None = None,
    include_archived: bool = False,
    ids: Annotated[list[str] | None, Query()] = None,
) -> Response:
    """CSV of the current filter (or selected ids). Contains PII → needs `crm`."""
    require_module(ctx, "crm")
    if ids:
        rows = leads_by_ids(db, ids[:EXPORT_MAX_ROWS])
    else:
        rows = _crm.list_leads(
            db,
            status=status,
            priority=priority,
            channel=channel,
            intent_type=intent_type,
            assigned_to=assigned_to,
            unassigned=unassigned,
            sla_breached=sla_breached,
            awaiting_reply=awaiting_reply,
            view=view,
            search=search,
            include_archived=include_archived,
            sort="created_at",
            limit=EXPORT_MAX_ROWS,
            offset=0,
        )
    from porterchain_api.collaboration_engine.crm_helpers import _now

    stamp = _now().strftime("%Y%m%d-%H%M")
    return Response(
        content=leads_to_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="porterchain-leads-{stamp}.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/leads/bulk")
def bulk_update_leads(
    body: LeadBulkRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "crm")
    try:
        return bulk_update(
            db,
            body.lead_ids,
            assigned_to=body.assigned_to,
            unassign=body.unassign,
            status=body.status,
            priority=body.priority,
        )
    except ReplyError as exc:
        _raise(exc)
        raise  # pragma: no cover


@router.get("/leads/{lead_id}/reply-channels")
def get_lead_reply_channels(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "crm_read")
    lead = _lead_or_404(db, lead_id)
    return {**reply_channels(settings, lead), "call_outcomes": list(CALL_OUTCOMES)}


@router.post("/leads/{lead_id}/reply")
def reply_to_lead(
    lead_id: str,
    body: LeadReplyRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Send a one-to-one reply. Only ever triggered by a staff click."""
    require_module(ctx, "crm")
    lead = _lead_or_404(db, lead_id)
    quote = None
    if body.attach_quote:
        from porterchain_api.lead_desk.quote import QuoteUnavailable, lead_quote

        try:
            quote = lead_quote(db, lead, website_url=settings.website_url)
        except QuoteUnavailable as exc:
            raise HTTPException(status_code=409, detail=f"quote_unavailable:{exc}") from exc
    try:
        return send_lead_reply(
            db,
            settings,
            lead,
            channel=body.channel,
            body=body.body,
            subject=body.subject,
            actor_id=ctx.user.id,
            quote=quote,
        )
    except ReplyError as exc:
        db.rollback()
        _raise(exc)
        raise  # pragma: no cover


@router.post("/leads/{lead_id}/log-call")
def log_lead_call(
    lead_id: str,
    body: LeadLogCallRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "crm")
    lead = _lead_or_404(db, lead_id)
    try:
        return log_call(
            db,
            lead,
            direction=body.direction,
            outcome=body.outcome,
            notes=body.notes,
            duration_minutes=body.duration_minutes,
            actor_id=ctx.user.id,
            follow_up_at=body.follow_up_at,
        )
    except ReplyError as exc:
        db.rollback()
        _raise(exc)
        raise  # pragma: no cover
