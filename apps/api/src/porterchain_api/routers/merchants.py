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
from porterchain_api.merchant_engine.contacts_service import MerchantContactsService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.platform.pagination import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT
from porterchain_api.schemas_admin import (
    MerchantActivateUsersRequest,
    MerchantCompleteOnboardingRequest,
    MerchantCreateRequest,
    MerchantInviteRequest,
    MerchantInviteResponse,
    MerchantUpdateRequest,
)
from porterchain_api.schemas_crm import ActivityOut, ContactOut, ContractOut, InvoiceOut, TaskOut

router = APIRouter(prefix="/v1/admin/merchants", tags=["merchants"])

_m360 = Merchant360Service()
_merchants = AdminMerchantService()
_contacts = MerchantContactsService()
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


@router.get("")
def list_merchants(
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = None,
    payment_terms: str | None = None,
    search: str | None = None,
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
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


@router.get("/unprovisioned-signups")
def merchant_unprovisioned_signups(
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[dict]:
    _guard(ctx, "merchants_read")
    return _m360.unprovisioned_signups(db, settings)


@router.post("", status_code=201)
def create_merchant(
    body: MerchantCreateRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx, "merchants")
    try:
        merchant = _merchants.create_merchant(
            db,
            ctx,
            settings,
            email=body.email,
            company_name=body.company_name,
            auto_activate=body.auto_activate,
            send_invite=body.send_invite,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "clerk_not_configured":
            raise HTTPException(status_code=503, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="merchant_create_failed") from exc
    detail = _m360.detail(db, merchant.id) or {}
    onboarding = _m360.onboarding(db, merchant.id)
    return {**detail, "onboarding": onboarding}


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
            parent_merchant_id=body.parent_merchant_id,
            support_tier=body.support_tier,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="merchant_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _m360.detail(db, merchant_id) or {}


@router.get("/{merchant_id}/subsidiaries")
def merchant_subsidiaries(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "merchants_read")
    if not _merchants.get_merchant(db, merchant_id):
        raise HTTPException(status_code=404, detail="merchant_not_found")
    rows = _merchants.list_subsidiaries(db, merchant_id)
    return [
        {
            "merchant_id": m.id,
            "company_name": m.company_name,
            "status": m.status,
            "payment_terms": m.payment_terms,
            "parent_merchant_id": m.parent_merchant_id,
        }
        for m in rows
    ]


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


@router.get("/{merchant_id}/onboarding")
def merchant_onboarding(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "merchants_read")
    try:
        return _m360.onboarding(db, merchant_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="merchant_not_found") from None


@router.post("/{merchant_id}/invite-owner", response_model=MerchantInviteResponse, status_code=201)
def invite_merchant_owner(
    merchant_id: str,
    body: MerchantInviteRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantInviteResponse:
    _guard(ctx, "merchants")
    try:
        user = _merchants.invite_owner(db, ctx, settings, merchant_id, email=body.email)
    except LookupError:
        raise HTTPException(status_code=404, detail="merchant_not_found") from None
    except ValueError as exc:
        detail = str(exc)
        if detail == "clerk_not_configured":
            raise HTTPException(status_code=503, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    return MerchantInviteResponse(
        merchant_user_id=user.id,
        email=user.email,
        role=user.role,
        invitation_status="invited",
        clerk_user_id=user.clerk_user_id if user.clerk_user_id.startswith("user_") else None,
    )


@router.post("/{merchant_id}/team/invite", response_model=MerchantInviteResponse, status_code=201)
def invite_merchant_team_member(
    merchant_id: str,
    body: MerchantInviteRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantInviteResponse:
    _guard(ctx, "merchants")
    try:
        user = _merchants.invite_team_member(
            db, ctx, settings, merchant_id, email=body.email, role=body.role or "merchant_ops"
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="merchant_not_found") from None
    except ValueError as exc:
        detail = str(exc)
        if detail == "clerk_not_configured":
            raise HTTPException(status_code=503, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    return MerchantInviteResponse(
        merchant_user_id=user.id,
        email=user.email,
        role=user.role,
        invitation_status="invited",
        clerk_user_id=user.clerk_user_id if user.clerk_user_id.startswith("user_") else None,
    )


@router.post("/{merchant_id}/activate-users")
def activate_merchant_users(
    merchant_id: str,
    body: MerchantActivateUsersRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    _guard(ctx, "merchants")
    try:
        users = _merchants.activate_merchant_users(db, ctx, merchant_id, email=body.email)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"activated": len(users), "emails": [u.email for u in users]}


@router.post("/{merchant_id}/complete-onboarding")
def complete_merchant_onboarding(
    merchant_id: str,
    body: MerchantCompleteOnboardingRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx, "merchants")
    try:
        merchant = _merchants.complete_onboarding(
            db, ctx, settings, merchant_id, email=body.email
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="merchant_not_found") from None
    except ValueError as exc:
        detail = str(exc)
        if detail == "clerk_not_configured":
            raise HTTPException(status_code=503, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    onboarding = _m360.onboarding(db, merchant_id)
    return {"merchant_id": merchant.id, "status": merchant.status, "onboarding": onboarding}


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
    _contacts.sync_for_merchant(db, merchant_id)
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
    """Ops invoices for this merchant (AR SSOT) — not CRM sales invoices."""
    _guard(ctx, "merchants_read")
    from datetime import date as date_cls

    from porterchain_api.billing_engine.merchant_service import invoice_status
    from porterchain_api.merchant_models import Merchant
    from porterchain_api.models import Invoice, Order, Payment

    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="merchant_not_found")
    rows = (
        db.query(Invoice, Order)
        .join(Order, Invoice.order_id == Order.id)
        .filter(Order.merchant_id == merchant_id)
        .order_by(Invoice.created_at.desc())
        .limit(200)
        .all()
    )
    out: list[InvoiceOut] = []
    for inv, order in rows:
        payment = (
            db.query(Payment)
            .filter(Payment.order_id == order.id)
            .order_by(Payment.created_at.desc())
            .first()
        )
        status = invoice_status(inv, order, payment, terms=merchant.payment_terms or order.payment_terms)
        due = inv.due_at.date() if inv.due_at else None
        paid_at = payment.created_at if payment and payment.status == "SUCCEEDED" else None
        out.append(
            InvoiceOut(
                id=inv.id,
                invoice_number=inv.invoice_number,
                company_id=None,
                deal_id=None,
                contract_id=None,
                status=status,
                amount_cents=inv.amount_cents,
                tax_cents=inv.tax_cents,
                total_cents=inv.amount_cents,
                currency=inv.currency,
                net_terms=merchant.payment_terms or order.payment_terms or "NET_30",
                line_items=[
                    {
                        "label": order.order_number or order.tracking_number or "Delivery",
                        "quantity": 1,
                        "unit_price_cents": inv.amount_cents,
                        "amount_cents": inv.amount_cents,
                    }
                ],
                notes=None,
                issue_date=inv.created_at.date() if inv.created_at else date_cls.today(),
                due_date=due,
                paid_at=paid_at,
                created_at=inv.created_at,
                updated_at=inv.created_at,
            )
        )
    return out


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
