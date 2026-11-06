"""Admin Customers API — /v1/admin/customers/* (Partners retail 360)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.customer_admin_service import CustomerAdminService
from porterchain_api.admin_engine.customer_booking_admin_service import CustomerBookingAdminService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.platform.pagination import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT
from porterchain_api.schemas_admin import (
    AdminConvertCustomerToMerchantRequest,
    AdminConvertCustomerToMerchantResponse,
    AdminCreateCustomerBookingDraftRequest,
    AdminCreateCustomerBookingDraftResponse,
    AdminCreateCustomerRequest,
    AdminCreateCustomerResponse,
    AdminCustomerInviteResponse,
    BookingDraftPaymentLinkResponse,
)

router = APIRouter(prefix="/v1/admin/customers", tags=["customers"])
_svc = CustomerAdminService()
_booking = CustomerBookingAdminService()

Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _guard(ctx: AdminContext, module: str) -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/stats")
def customer_stats(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "customers_read")
    return _svc.stats(db)


@router.get("")
def list_customers(
    ctx: Ctx,
    db: Session = Depends(get_db),
    search: str | None = None,
    identity_linked: bool | None = None,
    privacy_status: str | None = None,
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    _guard(ctx, "customers_read")
    return _svc.list_customers(
        db,
        search=search,
        identity_linked=identity_linked,
        privacy_status=privacy_status,
        limit=limit,
    )


@router.post("", response_model=AdminCreateCustomerResponse)
def create_customer(
    body: AdminCreateCustomerRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminCreateCustomerResponse:
    """Create a retail customer for phone-book / care. Optional Platform Keycloak invite."""
    _guard(ctx, "customers")
    try:
        result = _svc.create_customer(
            db,
            ctx,
            settings,
            email=body.email,
            phone=body.phone,
            full_name=body.full_name,
            send_invite=body.send_invite,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "customer_email_exists":
            raise HTTPException(status_code=409, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    return AdminCreateCustomerResponse(
        id=result["id"],
        email=result["email"],
        phone=result.get("phone"),
        customer_reference=result.get("customer_reference"),
        display_name=result["display_name"],
        auth_subject=result.get("auth_subject"),
        identity_linked=bool(result.get("identity_linked")),
        identity_status=result.get("identity_status") or "orphan",
        identity_action=result.get("identity_action"),
        created=bool(result.get("created", True)),
        created_at=result.get("created_at"),
    )


@router.get("/{customer_id}")
def customer_detail(customer_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "customers_read")
    try:
        return _svc.detail(db, customer_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="customer_not_found") from None


@router.post("/{customer_id}/invite", response_model=AdminCustomerInviteResponse)
def invite_customer(
    customer_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminCustomerInviteResponse:
    """Send or re-send Platform Keycloak invite for an orphan retail customer."""
    _guard(ctx, "customers")
    try:
        result = _svc.send_invite(db, ctx, settings, customer_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="customer_not_found") from None
    except ValueError as exc:
        detail = str(exc)
        if detail == "customer_already_idp_linked":
            raise HTTPException(status_code=409, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    return AdminCustomerInviteResponse(
        id=result["id"],
        email=result["email"],
        auth_subject=result.get("auth_subject"),
        identity_linked=bool(result.get("identity_linked")),
        identity_status=result.get("identity_status") or "orphan",
        identity_action=result.get("identity_action"),
    )


@router.get("/{customer_id}/orders")
def customer_orders(
    customer_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    state: str | None = None,
) -> list[dict]:
    _guard(ctx, "customers_read")
    try:
        return _svc.orders(db, customer_id, limit=limit, state=state)
    except LookupError:
        raise HTTPException(status_code=404, detail="customer_not_found") from None


@router.get("/{customer_id}/invoices")
def customer_invoices(
    customer_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    _guard(ctx, "customers_read")
    try:
        return _svc.invoices(db, customer_id, limit=limit)
    except LookupError:
        raise HTTPException(status_code=404, detail="customer_not_found") from None


@router.get("/{customer_id}/payments")
def customer_payments(
    customer_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    _guard(ctx, "customers_read")
    try:
        return _svc.payments(db, customer_id, limit=limit)
    except LookupError:
        raise HTTPException(status_code=404, detail="customer_not_found") from None



@router.post(
    "/{customer_id}/convert-to-merchant",
    response_model=AdminConvertCustomerToMerchantResponse,
)
def convert_customer_to_merchant(
    customer_id: str,
    body: AdminConvertCustomerToMerchantRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminConvertCustomerToMerchantResponse:
    """Convert a retail customer into a merchant. Historical orders remap to the merchant."""
    _guard(ctx, "customers")
    from porterchain_api.admin_engine.merchant_lifecycle import convert_from_customer
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService

    svc = AdminMerchantService()
    try:
        result = convert_from_customer(
            svc,
            db,
            ctx,
            settings,
            customer_id,
            company_name=body.company_name,
            auto_activate=body.auto_activate,
            send_invite=body.send_invite,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="customer_not_found") from None
    except ValueError as exc:
        detail = str(exc)
        code = 409 if detail in {
            "merchant_email_exists",
            "merchant_user_email_exists",
            "email_seat_taken",
        } else 400
        raise HTTPException(status_code=code, detail=detail) from exc
    return AdminConvertCustomerToMerchantResponse(
        customer_id=result["customer_id"],
        merchant_id=result["merchant_id"],
        status=result["status"],
        company_name=result.get("company_name"),
        idempotent=bool(result.get("idempotent")),
    )


@router.get("/{customer_id}/care")
def customer_care(
    customer_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    _guard(ctx, "customers_read")
    try:
        return _svc.care(db, customer_id, limit=limit)
    except LookupError:
        raise HTTPException(status_code=404, detail="customer_not_found") from None


@router.post(
    "/{customer_id}/booking-drafts",
    response_model=AdminCreateCustomerBookingDraftResponse,
)
def create_customer_booking_draft(
    customer_id: str,
    body: AdminCreateCustomerBookingDraftRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminCreateCustomerBookingDraftResponse:
    """Phone-book retail quote + draft for an existing customer. Optional Stripe payment link (no cash)."""
    _guard(ctx, "customers")
    try:
        result = _booking.create_for_customer(
            db,
            settings,
            ctx,
            customer_id,
            pickup=body.pickup.model_dump(),
            dropoff=body.dropoff.model_dump(),
            vehicle_class=body.vehicle_class,
            package_type=body.package_type,
            weight_kg=body.weight_kg,
            dimensions=body.dimensions,
            declared_value_cents=body.declared_value_cents,
            special_instructions=body.special_instructions,
            scheduled_at=body.scheduled_at,
            schedule_mode=body.schedule_mode,
            send_payment_link=body.send_payment_link,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="customer_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AdminCreateCustomerBookingDraftResponse(**result)


@router.post(
    "/{customer_id}/booking-drafts/{draft_id}/send-payment-link",
    response_model=BookingDraftPaymentLinkResponse,
)
def send_customer_draft_payment_link(
    customer_id: str,
    draft_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingDraftPaymentLinkResponse:
    """Send Stripe Checkout link for a customer-owned booking draft (no cash)."""
    _guard(ctx, "customers")
    try:
        result = _booking.send_payment_link_for_customer(
            db,
            settings,
            ctx,
            customer_id=customer_id,
            draft_id=draft_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="draft_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BookingDraftPaymentLinkResponse(**result)
