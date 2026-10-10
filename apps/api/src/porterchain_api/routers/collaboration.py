"""Activities & tasks for merchants/drivers — thin CRM slice (masterrule §21)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.schemas_crm import ActivityCreate, ActivityOut, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/v1/admin/collaboration", tags=["collaboration"])

_crm = CrmSalesService()
Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _guard(ctx: AdminContext, module: str) -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _guard_any(ctx: AdminContext, *modules: str) -> None:
    last: Exception | None = None
    for module in modules:
        try:
            require_module(ctx, module)
            return
        except PermissionError as exc:
            last = exc
    raise HTTPException(status_code=403, detail=str(last) if last else "forbidden")


@router.get("/activities", response_model=list[ActivityOut])
def list_activities(
    ctx: Ctx,
    db: Session = Depends(get_db),
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(100, le=500),
) -> list[ActivityOut]:
    _guard_any(ctx, "merchants_read", "crm_read")
    rows = _crm.list_activities(db, entity_type=entity_type, entity_id=entity_id, limit=limit)
    return [ActivityOut(**_crm.activity_dict(a)) for a in rows]


@router.post("/activities", response_model=ActivityOut)
def create_activity(body: ActivityCreate, ctx: Ctx, db: Session = Depends(get_db)) -> ActivityOut:
    _guard_any(ctx, "merchants", "crm")
    activity = _crm.log_activity(
        db,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        activity_type=body.activity_type,
        subject=body.subject,
        body=body.body,
        metadata=body.metadata,
        actor_id=ctx.user.id if ctx.user else None,
        occurred_at=body.occurred_at,
    )
    return ActivityOut(**_crm.activity_dict(activity))


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = None,
    assigned_to: str | None = None,
    entity_id: str | None = None,
) -> list[TaskOut]:
    _guard_any(ctx, "merchants_read", "crm_read")
    rows = _crm.list_tasks(db, status=status, assigned_to=assigned_to, entity_id=entity_id)
    return [TaskOut.model_validate(t) for t in rows]


@router.post("/tasks", response_model=TaskOut)
def create_task(body: TaskCreate, ctx: Ctx, db: Session = Depends(get_db)) -> TaskOut:
    _guard_any(ctx, "merchants", "crm")
    task = _crm.create_task(db, ctx, body.model_dump())
    return TaskOut.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: TaskUpdate, ctx: Ctx, db: Session = Depends(get_db)) -> TaskOut:
    _guard_any(ctx, "merchants", "crm")
    try:
        task = _crm.update_task(db, task_id, body.model_dump(exclude_unset=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="task_not_found") from exc
    return TaskOut.model_validate(task)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> None:
    _guard_any(ctx, "merchants", "crm")
    if not _crm.get_task(db, task_id):
        raise HTTPException(status_code=404, detail="task_not_found")
    try:
        _crm.delete_task(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="task_not_found") from exc
