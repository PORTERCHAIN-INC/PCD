"""Admin CRM lead 360 / calendar / merge — thin routes on shared admin router."""

from datetime import datetime
from typing import Annotated

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field
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
from porterchain_api.schemas_crm import Lead360Response, LeadOut, TaskOut

_crm = CrmSalesService()


@router.get("/leads/{lead_id}/assist")
def lead_assist(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """NVIDIA NIM / heuristic sales assist — never auto-sends."""
    require_module(ctx, "crm_read")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    from porterchain_api.intelligence_engine.lead_assist import build_lead_assist

    return build_lead_assist(
        db,
        lead,
        # phase2_intelligence_enabled() reads "intelligence"; the old key name
        # meant the NIM path could never run even with the flag on.
        flags={"intelligence": bool(settings.phase2_intelligence)},
        actor_id=ctx.user.id,
    )


@router.get("/leads/calendar", response_model=list[TaskOut])
def list_lead_calendar_tasks(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    due_after: datetime | None = None,
    due_before: datetime | None = None,
    limit: int = Query(200, le=500),
) -> list[TaskOut]:
    """Week/range view of call + meeting tasks linked to CRM leads."""
    require_module(ctx, "crm_read")
    rows = _crm.list_tasks(
        db,
        entity_type="lead",
        task_types=["call", "meeting"],
        due_after=due_after,
        due_before=due_before,
        limit=limit,
    )
    return [TaskOut.model_validate(t) for t in rows]


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> LeadOut:
    require_module(ctx, "crm_read")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    return LeadOut.model_validate(lead)


@router.get("/leads/{lead_id}/360", response_model=Lead360Response)
def get_lead_360(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> Lead360Response:
    """Lead 360 composition — CrmLead hub + visitor + retail + commerce panels."""
    require_module(ctx, "crm_read")
    from porterchain_api.collaboration_engine.lead360_service import Lead360Service

    payload = Lead360Service().get(db, lead_id)
    if not payload:
        raise HTTPException(status_code=404, detail="lead_not_found")
    return Lead360Response(
        lead=LeadOut.model_validate(payload["lead"]),
        retail_lead=payload["retail_lead"],
        identities=payload["identities"],
        conversations=payload["conversations"],
        tasks=[TaskOut.model_validate(t) for t in payload["tasks"]],
        nurture=payload["nurture"],
        activities=payload["activities"],
        visitor=payload["visitor"],
        quotes=payload["quotes"],
        drafts=payload["drafts"],
        abandoned_checkouts=payload["abandoned_checkouts"],
        referral=payload["referral"],
        sla=payload["sla"],
        assignee=payload["assignee"],
        consent=payload["consent"],
        score=payload["score"],
        merge_candidate_of=payload["merge_candidate_of"],
        urgent_unassigned_tasks=payload["urgent_unassigned_tasks"],
        linked_merchant_id=payload["linked_merchant_id"],
        linked_customer_id=payload["linked_customer_id"],
        linked_driver_id=payload["linked_driver_id"],
        last_capi=payload["last_capi"],
    )


class MergeResolveRequest(BaseModel):
    action: str = Field(description="accept | reject")


@router.post("/leads/{lead_id}/merge", response_model=LeadOut)
def resolve_lead_merge(
    lead_id: str,
    body: MergeResolveRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> LeadOut:
    """Accept (fold into merge_candidate_of) or reject soft-duplicate queue item."""
    require_module(ctx, "crm")
    from porterchain_api.collaboration_engine.lead_ops import resolve_merge_candidate

    try:
        lead = resolve_merge_candidate(
            db,
            lead_id=lead_id,
            action=body.action,
            actor_id=ctx.user.id if ctx.user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return LeadOut.model_validate(lead)
