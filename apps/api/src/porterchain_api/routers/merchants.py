"""Merchant 360 admin API — /v1/admin/merchants/*

All merchant business logic lives in Porterchain (per masterrule.md). Reads the
Porterchain order mirror + CRM data; never calls Fleetbase directly.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
from porterchain_api.admin_engine.merchant360_service import Merchant360Service
from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.schemas_admin import MerchantUpdateRequest
from porterchain_api.schemas_crm import ActivityOut, ContactOut, ContractOut, InvoiceOut, TaskOut

router = APIRouter(prefix="/v1/admin/merchants", tags=["merchants"])

_m360 = Merchant360Service()
_merchants = AdminMerchantService()
_crm = CrmSalesService()

Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _guard(ctx: AdminContext, module: str) -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _company_id(db: Session, merchant_id: str) -> str | None:
    company = _m360._linked_company(db, merchant_id)
    return company.id if company else None


# --------------------------------------------------------------------------- #
# List / facets / stats
# --------------------------------------------------------------------------- #
@router.get("")
def list_merchants(
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = None,
    payment_terms: str | None = None,
    search: str | None = None,
    limit: int = Query(500, le=10000),
) -> list[dict]:
    _guard(ctx, "merchants_read")
    return _m360.list_merchants(db, status=status, payment_terms=payment_terms, search=search, limit=limit)


@router.get("/facets")
def merchant_facets(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "merchants_read")
    return _m360.facets(db)


@router.get("/stats")
def merchant_stats(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "merchants_read")
    return _m360.stats(db)


# --------------------------------------------------------------------------- #
# Detail + lifecycle
# --------------------------------------------------------------------------- #
@router.get("/{merchant_id}")
def merchant_detail(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "merchants_read")
    detail = _m360.detail(db, merchant_id)
    if not detail:
        raise HTTPException(status_code=404, detail="merchant_not_found")
    return detail


@router.post("/{merchant_id}/approve")
def approve_merchant(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "merchants")
    try:
        _merchants.approve_merchant(db, ctx, merchant_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="merchant_not_found") from None
    return _m360.detail(db, merchant_id) or {}


@router.post("/{merchant_id}/suspend")
def suspend_merchant(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "merchants")
    try:
        _merchants.suspend_merchant(db, ctx, merchant_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="merchant_not_found") from None
    return _m360.detail(db, merchant_id) or {}


@router.patch("/{merchant_id}")
def update_merchant(
    merchant_id: str, body: MerchantUpdateRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    _guard(ctx, "merchants")
    try:
        _merchants.update_merchant_terms(
            db, ctx, merchant_id,
            payment_terms=body.payment_terms,
            pricing_config=body.pricing_config,
            credit_limit_cents=body.credit_limit_cents,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="merchant_not_found") from None
    return _m360.detail(db, merchant_id) or {}


# --------------------------------------------------------------------------- #
# 360 sub-resources
# --------------------------------------------------------------------------- #
@router.get("/{merchant_id}/orders")
def merchant_orders(
    merchant_id: str, ctx: Ctx, db: Session = Depends(get_db), state: str | None = None
) -> list[dict]:
    _guard(ctx, "merchants_read")
    return _m360.orders(db, merchant_id, state=state)


@router.get("/{merchant_id}/locations")
def merchant_locations(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "merchants_read")
    return _m360.locations(db, merchant_id)


@router.get("/{merchant_id}/team")
def merchant_team(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "merchants_read")
    return _m360.team(db, merchant_id)


@router.get("/{merchant_id}/api")
def merchant_api(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "merchants_read")
    return _m360.api_keys(db, merchant_id)


@router.get("/{merchant_id}/analytics")
def merchant_analytics(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "merchants_read")
    return _m360.analytics(db, merchant_id)


@router.get("/{merchant_id}/timeline")
def merchant_timeline(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "merchants_read")
    return _m360.timeline(db, merchant_id, _company_id(db, merchant_id))


@router.get("/{merchant_id}/contacts", response_model=list[ContactOut])
def merchant_contacts(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[ContactOut]:
    _guard(ctx, "merchants_read")
    cid = _company_id(db, merchant_id)
    rows = _crm.list_contacts(db, company_id=cid) if cid else []
    return [ContactOut.model_validate(c) for c in rows]


@router.get("/{merchant_id}/contracts", response_model=list[ContractOut])
def merchant_contracts(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[ContractOut]:
    _guard(ctx, "merchants_read")
    cid = _company_id(db, merchant_id)
    rows = _crm.list_contracts(db, company_id=cid) if cid else []
    return [ContractOut.model_validate(c) for c in rows]


@router.get("/{merchant_id}/invoices", response_model=list[InvoiceOut])
def merchant_invoices(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[InvoiceOut]:
    _guard(ctx, "merchants_read")
    cid = _company_id(db, merchant_id)
    rows = _crm.list_invoices(db, company_id=cid) if cid else []
    return [InvoiceOut.model_validate(i) for i in rows]


@router.get("/{merchant_id}/activities", response_model=list[ActivityOut])
def merchant_activities(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[ActivityOut]:
    _guard(ctx, "merchants_read")
    cid = _company_id(db, merchant_id)
    rows = _crm.list_activities(db, entity_id=cid) if cid else _crm.list_activities(db, entity_id=merchant_id)
    return [ActivityOut(**_crm.activity_dict(a)) for a in rows]


@router.get("/{merchant_id}/tasks", response_model=list[TaskOut])
def merchant_tasks(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[TaskOut]:
    _guard(ctx, "merchants_read")
    cid = _company_id(db, merchant_id)
    rows = _crm.list_tasks(db, entity_id=cid) if cid else []
    return [TaskOut.model_validate(t) for t in rows]
