"""Admin Customers 360 + customer care queues (privacy jobs, reorder nudges).

/v1/admin/customers/{id}/360|timeline|notes|credit|refund|booking-link-draft
/v1/admin/customer-care/privacy-jobs[/{id}/approve|reject]
/v1/admin/customer-care/nudges[/draft|/decide]
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.customer_fast import admin360, privacy
from porterchain_api.db import get_db

router = APIRouter(prefix="/v1/admin", tags=["customers"])
Ctx = Annotated[AdminContext, Depends(get_admin_context)]
PRIVACY_ROLES = {"super_admin", "admin", "compliance"}


def _guard(ctx: AdminContext, module: str) -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _actor(ctx: AdminContext) -> str:
    user = ctx.user
    return str(getattr(user, "email", None) or getattr(user, "display_name", None) or getattr(user, "id", "staff"))


def _call(fn, *args, **kwargs) -> Any:
    try:
        return fn(*args, **kwargs)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class NoteBody(BaseModel):
    body: str = Field(min_length=2, max_length=2000)


class CreditBody(BaseModel):
    amount_cents: int = Field(ge=-50_000, le=50_000)
    reason: str = Field(min_length=3, max_length=500)
    order_id: str | None = None


class RefundBody(BaseModel):
    tracking_number: str = Field(min_length=3, max_length=64)
    amount_cents: int | None = Field(default=None, gt=0)
    reason: str = Field(min_length=3, max_length=500)


class ReviewBody(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class DecideBody(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=200)
    approve: bool


@router.get("/customers/{customer_id}/360")
def get_360(customer_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict:
    _guard(ctx, "customers_read")
    return _call(admin360.overview, db, settings, customer_id)


@router.get("/customers/{customer_id}/timeline")
def get_timeline(customer_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "customers_read")
    return _call(admin360.timeline, db, customer_id)


@router.post("/customers/{customer_id}/notes")
def post_note(customer_id: str, body: NoteBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "customers")
    return _call(admin360.add_note, db, customer_id, author=_actor(ctx), body=body.body)


@router.post("/customers/{customer_id}/credit")
def post_credit(customer_id: str, body: CreditBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "customers")
    return _call(admin360.add_credit, db, customer_id, amount_cents=body.amount_cents, reason=body.reason,
                 actor=_actor(ctx), order_id=body.order_id)


@router.post("/customers/{customer_id}/refund")
def post_refund(customer_id: str, body: RefundBody, ctx: Ctx, db: Session = Depends(get_db),
                settings: Settings = Depends(get_settings)) -> dict:
    _guard(ctx, "finance")
    return _call(admin360.refund_order, db, settings, customer_id, tracking_number=body.tracking_number,
                 amount_cents=body.amount_cents, reason=body.reason, actor=_actor(ctx))


@router.post("/customers/{customer_id}/booking-link-draft")
def post_booking_link_draft(customer_id: str, ctx: Ctx, db: Session = Depends(get_db),
                            settings: Settings = Depends(get_settings)) -> dict:
    """Returns a draft email (to / subject / body / link). Never sends."""
    _guard(ctx, "customers")
    return _call(admin360.booking_link_draft, db, settings, customer_id)


@router.get("/customer-care/privacy-jobs")
def get_privacy_jobs(ctx: Ctx, status: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "customers_read")
    return privacy.list_jobs(db, status)


def _privacy_guard(ctx: AdminContext) -> None:
    _guard(ctx, "customers")
    if str(getattr(ctx.role, "value", ctx.role)).lower() not in PRIVACY_ROLES:
        raise HTTPException(status_code=403, detail="privacy_review_requires_admin_or_compliance")


@router.post("/customer-care/privacy-jobs/{job_id}/approve")
def post_privacy_approve(job_id: str, body: ReviewBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _privacy_guard(ctx)
    return _call(privacy.approve_and_execute, db, job_id, reviewer=_actor(ctx), note=body.note)


@router.post("/customer-care/privacy-jobs/{job_id}/reject")
def post_privacy_reject(job_id: str, body: ReviewBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _privacy_guard(ctx)
    return _call(privacy.reject, db, job_id, reviewer=_actor(ctx), note=body.note or "")


@router.get("/customer-care/nudges")
def get_nudges(ctx: Ctx, status: str = "draft", db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "customers_read")
    return admin360.list_nudges(db, status)


@router.post("/customer-care/nudges/draft")
def post_nudges_draft(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "customers")
    return admin360.draft_nudges(db)


@router.post("/customer-care/nudges/decide")
def post_nudges_decide(body: DecideBody, ctx: Ctx, db: Session = Depends(get_db),
                       settings: Settings = Depends(get_settings)) -> dict:
    _guard(ctx, "customers")
    return _call(admin360.decide_nudges, db, settings, body.ids, approve=body.approve, actor=_actor(ctx))
