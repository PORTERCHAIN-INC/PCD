"""Admin CRM leads — list, detail, status updates, appointment calendar."""

from datetime import datetime
from typing import Annotated

from fastapi import HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Depends,
    _perm,
    get_admin_context,
    get_db,
    require_module,
    router,
)
from porterchain_api.schemas_crm import LeadOut, LeadUpdate, TaskOut

_crm = CrmSalesService()


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    priority: str | None = None,
    source: str | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list[LeadOut]:
    require_module(ctx, "crm_read")
    rows = _crm.list_leads(
        db,
        status=status,
        priority=priority,
        source=source,
        search=search,
        limit=min(limit, 500),
    )
    return [LeadOut.model_validate(row) for row in rows]


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


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: str,
    body: LeadUpdate,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> LeadOut:
    require_module(ctx, "crm")
    data = body.model_dump(exclude_unset=True)
    if not data:
        lead = _crm.get_lead(db, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="lead_not_found")
        return LeadOut.model_validate(lead)
    try:
        lead = _crm.update_lead(db, lead_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="lead_not_found") from exc
    return LeadOut.model_validate(lead)


@router.delete("/leads/{lead_id}", status_code=204)
def delete_lead(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> None:
    """Hard-delete a CRM lead. Super_admin only (SpiceDB system_all)."""
    try:
        require_module(ctx, "system:all")
    except PermissionError as exc:
        _perm(exc)
    try:
        _crm.delete_lead(db, lead_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="lead_not_found") from exc
