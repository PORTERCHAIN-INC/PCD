"""Admin Customers API — /v1/admin/customers/* (Partners retail 360)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.customer_admin_service import CustomerAdminService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.platform.pagination import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT

router = APIRouter(prefix="/v1/admin/customers", tags=["customers"])
_svc = CustomerAdminService()

Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _guard(ctx: AdminContext, module: str) -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("")
def list_customers(
    ctx: Ctx,
    db: Session = Depends(get_db),
    search: str | None = None,
    clerk_linked: bool | None = None,
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    _guard(ctx, "customers_read")
    return _svc.list_customers(db, search=search, clerk_linked=clerk_linked, limit=limit)


@router.get("/{customer_id}")
def customer_detail(customer_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "customers_read")
    try:
        return _svc.detail(db, customer_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="customer_not_found") from None


@router.get("/{customer_id}/orders")
def customer_orders(
    customer_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    _guard(ctx, "customers_read")
    try:
        return _svc.orders(db, customer_id, limit=limit)
    except LookupError:
        raise HTTPException(status_code=404, detail="customer_not_found") from None
