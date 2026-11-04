"""Admin: Organisations, capability packs and operating profiles (doc 70)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, AdminRole
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.org_engine import packs, service
from porterchain_api.org_engine.models import Organisation

router = APIRouter(prefix="/v1/admin/orgs", tags=["admin-orgs"])

AdminDep = Annotated[AdminContext, Depends(get_admin_context)]
DbDep = Annotated[Session, Depends(get_db)]

_READ = {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.SALES, AdminRole.SALES_MANAGER, AdminRole.FINANCE,
         AdminRole.DISPATCHER, AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD}


def _read(ctx: AdminContext) -> None:
    if ctx.role not in _READ:
        raise HTTPException(status_code=403, detail="orgs_forbidden")


def _manage(ctx: AdminContext) -> None:
    if ctx.role not in (AdminRole.SUPER_ADMIN, AdminRole.ADMIN):
        raise HTTPException(status_code=403, detail="orgs_manage_forbidden")


def _org(db: Session, org_id: str) -> Organisation:
    org = db.get(Organisation, org_id) or db.scalar(select(Organisation).where(Organisation.public_id == org_id))
    if org is None:
        raise HTTPException(status_code=404, detail="org_not_found")
    return org


@router.get("/business-types")
def business_types(ctx: AdminDep) -> dict[str, Any]:
    _read(ctx)
    return {
        "business_types": [
            {"code": code, **{k: v for k, v in bt.items() if k != "profile"}, "profile": packs.default_profile(code),
             "documents": packs.documents_for(code)}
            for code, bt in packs.BUSINESS_TYPES.items()
        ],
        "capabilities": packs.CAPABILITIES,
        "subtype_capabilities": packs.SUBTYPE_CAPABILITIES,
    }


@router.get("")
def list_orgs(
    ctx: AdminDep,
    db: DbDep,
    business_type: str | None = None,
    needs_review: bool | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Organisations list with search, filters, paging, total and per-type counts (Types & packs page)."""
    _read(ctx)
    conds = []
    if business_type:
        conds.append(Organisation.business_type == business_type)
    if needs_review is not None:
        conds.append(Organisation.needs_review.is_(needs_review))
    if status:
        conds.append(Organisation.status == status)
    if q and q.strip():
        like = f"%{q.strip()}%"
        conds.append(or_(Organisation.display_name.ilike(like), Organisation.public_id.ilike(like),
                         Organisation.legal_name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(Organisation).where(*conds)) or 0
    page = (select(Organisation).where(*conds).order_by(Organisation.display_name)
            .offset(max(0, offset)).limit(max(1, min(limit, 500))))
    by_type = dict(db.execute(select(Organisation.business_type, func.count()).group_by(Organisation.business_type)).all())
    review = db.scalar(select(func.count()).select_from(Organisation).where(Organisation.needs_review.is_(True))) or 0
    return {
        "items": [service.org_out(db, o) for o in db.scalars(page)],
        "total": total,
        "counts": {"by_type": by_type, "needs_review": review, "all": sum(by_type.values())},
    }


class CreateOrg(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    business_type: str
    subtype: str | None = None
    legal_name: str | None = None


@router.post("", status_code=201)
def create_org(body: CreateOrg, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _manage(ctx)
    try:
        org = service.provision(db, display_name=body.display_name, business_type=body.business_type, subtype=body.subtype, legal_name=body.legal_name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return service.org_out(db, org)


@router.get("/{org_id}")
def get_org(org_id: str, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _read(ctx)
    return service.org_out(db, _org(db, org_id))


class TypeBody(BaseModel):
    business_type: str
    subtype: str | None = None
    reset_capabilities: bool = False


@router.put("/{org_id}/type")
def set_type(org_id: str, body: TypeBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    """Confirm or change the business type (the one-page review after backfill)."""
    _manage(ctx)
    org = _org(db, org_id)
    try:
        caps = packs.default_capabilities(body.business_type, body.subtype)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    org.business_type, org.subtype, org.needs_review = body.business_type, body.subtype, False
    org.role_flags = list(packs.business_type(body.business_type)["roles"])
    if body.reset_capabilities:
        current = service.capabilities(db, org.id)
        service.set_capabilities(db, org.id, {c: False for c in current if c not in caps} | {c: True for c in caps}, source="default")
        service.set_profile(db, org.id, packs.default_profile(body.business_type), actor=getattr(ctx.user, "id", None))
    db.commit()
    return service.org_out(db, org)


class CapsBody(BaseModel):
    capabilities: dict[str, bool]


@router.put("/{org_id}/capabilities")
def set_caps(org_id: str, body: CapsBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _manage(ctx)
    org = _org(db, org_id)
    try:
        service.set_capabilities(db, org.id, body.capabilities)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return service.org_out(db, org)


class ProfileBody(BaseModel):
    pickup_mode: str | None = None
    pickup_params: dict[str, Any] | None = None
    tracking_mode: str | None = None
    label_mode: str | None = None
    relabel_rule: dict[str, Any] | None = None
    barcode_formats: list[str] | None = None
    ref_schema: dict[str, str] | None = None


@router.put("/{org_id}/operating-profile")
def set_profile(org_id: str, body: ProfileBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _manage(ctx)
    org = _org(db, org_id)
    try:
        service.set_profile(db, org.id, body.model_dump(exclude_none=True), actor=getattr(ctx.user, "id", None))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return service.org_out(db, org)


class BackfillBody(BaseModel):
    dry_run: bool = True


@router.post("/backfill-from-merchants")
def backfill(body: BackfillBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    if ctx.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="super_admin_only")
    out = service.backfill_from_merchants(db, dry_run=body.dry_run)
    if body.dry_run:
        db.rollback()
    else:
        db.commit()
    return out
