"""Merchant 360 admin API — /v1/admin/merchants/* (thin; engines own logic)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.merchant360_service import Merchant360Service
from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.merchant_engine.standing_order_service import MerchantStandingOrderService
from porterchain_api.merchant_engine.privacy import MerchantPrivacyService
from porterchain_api.admin_engine.merchant_org import (
    activate_users_payload, activate_webhook, after_admin_write, admin_merchant_context,
    complete_onboarding_payload,
    create_address, create_contact, create_linked_contract, create_recipient,
    create_with_onboarding, delete_address, delete_billing_contact,
    delete_contact, delete_recipient, generate_cycle_ar, list_activities,
    list_billing_contacts, list_contacts, list_contracts, list_tasks, merge_pricing_view,
    org_error_message, patch_billing_contact, preview_cycle_ar, pricing_view_for, raise_org_http,
    require_detail, reserve_owner_seat, reserve_team_seat, save_billing_contact, set_default_address, subsidiaries_payload, team_member_payload,
    timeline_for, update_address, update_contact, update_linked_contract, update_recipient,
)
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.platform.pagination import (
    DEFAULT_LIST_LIMIT,
    DEFAULT_PAGE_SIZE,
    MAX_EMBEDDED_LIST_LIMIT,
    MAX_LIST_LIMIT,
)
from porterchain_api.schemas_admin import (
    MerchantActivateUsersRequest,
    MerchantCloseRequest,
    MerchantCompleteOnboardingRequest,
    MerchantConvertRequest,
    MerchantCreateRequest,
    MerchantInviteRequest,
    MerchantInviteResponse,
    MerchantPricingRequest,
    MerchantPricingResponse,
    MerchantTeamRoleUpdate,
    MerchantUpdateRequest,
)
from porterchain_api.schemas_crm import (
    ActivityOut,
    ContractCreate,
    ContractOut,
    ContractUpdate,
    InvoiceOut,
    TaskOut,
)
from porterchain_api.schemas_merchant import (
    BillingContactPatchRequest,
    BillingContactRequest,
    MerchantContactCreateRequest,
    MerchantContactResponse,
    MerchantContactUpdateRequest,
    RecipientCreateRequest,
    RecipientResponse,
    RecipientUpdateRequest,
    SavedAddressCreateRequest,
    SavedAddressResponse,
    SavedAddressUpdateRequest,
)

router = APIRouter(prefix="/v1/admin/merchants", tags=["merchants"])

_m360 = Merchant360Service()
_merchants = AdminMerchantService()
_privacy = MerchantPrivacyService()
_standing_orders = MerchantStandingOrderService()
Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _invoke(ctx: AdminContext, module: str, fn, *args, org=False, copy=None, **kwargs):
    try:
        require_module(ctx, module)
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        if org:
            raise_org_http(exc)
            raise
        detail = str(exc) or "merchant_not_found"
        raise HTTPException(status_code=404, detail=copy(detail) if copy else detail) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        if str(exc) == "clerk_not_configured":
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if org:
            raise_org_http(exc)
            raise
        detail = str(exc)
        raise HTTPException(status_code=400, detail=copy(detail) if copy else detail) from exc


def _mutated(ctx: AdminContext, db: Session, merchant_id: str, fn, **kwargs) -> dict:
    return _invoke(
        ctx, "merchants", after_admin_write, db, ctx, merchant_id, fn, copy=org_error_message, **kwargs
    )


@router.get("")
def list_merchants(
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = None,
    payment_terms: str | None = None,
    search: str | None = None,
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    return _invoke(
        ctx, "merchants_read", _m360.list_merchants, db,
        status=status, payment_terms=payment_terms, search=search, limit=limit,
    )


@router.get("/facets")
def merchant_facets(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants_read", _m360.facets, db)


@router.get("/stats")
def merchant_stats(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants_read", _m360.stats, db)


@router.get("/unprovisioned-signups")
def merchant_unprovisioned_signups(
    ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> list[dict]:
    return _invoke(ctx, "merchants_read", _m360.unprovisioned_signups, db, settings)


@router.post("", status_code=201)
def create_merchant(
    body: MerchantCreateRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        return _invoke(
            ctx, "merchants", create_with_onboarding, db, ctx, settings,
            email=body.email, company_name=body.company_name, auto_activate=body.auto_activate,
            send_invite=body.send_invite,
            pricing_config=body.pricing.model_dump() if body.pricing else None,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="merchant_create_failed") from exc


@router.get("/{merchant_id}")
def merchant_detail(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants_read", require_detail, db, merchant_id)


@router.post("/{merchant_id}/approve")
def approve_merchant(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _mutated(ctx, db, merchant_id, _merchants.approve_merchant)


@router.post("/{merchant_id}/suspend")
def suspend_merchant(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _mutated(ctx, db, merchant_id, _merchants.suspend_merchant)


@router.post("/{merchant_id}/unsuspend")
def unsuspend_merchant(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _mutated(ctx, db, merchant_id, _merchants.unsuspend_merchant)


@router.post("/{merchant_id}/reopen")
def reopen_merchant(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _mutated(ctx, db, merchant_id, _merchants.reopen_merchant)


@router.post("/{merchant_id}/close")
def close_merchant(
    merchant_id: str, body: MerchantCloseRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    return _mutated(ctx, db, merchant_id, _merchants.close_merchant, reason=body.reason)


@router.post("/{merchant_id}/convert-to-customer")
def convert_merchant_to_customer(
    merchant_id: str, body: MerchantConvertRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    return _invoke(
        ctx,
        "merchants",
        _merchants.convert_to_customer,
        db,
        ctx,
        merchant_id,
        owner_email=body.owner_email,
        write_off_ar=body.write_off_ar,
    )


@router.get("/{merchant_id}/privacy")
def merchant_privacy(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    from porterchain_api.compliance_engine.privacy_service import privacy_error_message

    return _invoke(ctx, "merchants", _privacy.status_for_id, db, merchant_id, copy=privacy_error_message)


@router.post("/{merchant_id}/privacy/execute")
def execute_merchant_privacy(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    from porterchain_api.compliance_engine.privacy_service import privacy_error_message

    return _invoke(
        ctx, "merchants", _privacy.execute_for_id, db, merchant_id,
        actor_user_id=ctx.user.id, copy=privacy_error_message,
    )


@router.patch("/{merchant_id}")
def update_merchant(
    merchant_id: str, body: MerchantUpdateRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    return _mutated(ctx, db, merchant_id, _merchants.update_merchant_terms, **body.model_dump(exclude_unset=True))


@router.get("/{merchant_id}/pricing", response_model=MerchantPricingResponse)
def get_merchant_pricing(
    merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> MerchantPricingResponse:
    return MerchantPricingResponse(**_invoke(ctx, "merchants_read", pricing_view_for, db, merchant_id))


@router.put("/{merchant_id}/pricing", response_model=MerchantPricingResponse)
def set_merchant_pricing(
    merchant_id: str, body: MerchantPricingRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> MerchantPricingResponse:
    # Module gate is read; assert_money_editor (admin / super admin / finance) is the write gate.
    view = _invoke(
        ctx, "merchants_read", merge_pricing_view, db, ctx, merchant_id, body.model_dump(exclude_unset=True)
    )
    return MerchantPricingResponse(**view)


@router.get("/{merchant_id}/subsidiaries")
def merchant_subsidiaries(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    return _invoke(ctx, "merchants_read", subsidiaries_payload, db, merchant_id)


@router.get("/{merchant_id}/orders")
def merchant_orders(
    merchant_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    state: str | None = None,
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_EMBEDDED_LIST_LIMIT),
    offset: int = Query(0, ge=0),
) -> dict:
    return _invoke(ctx, "merchants_read", _m360.orders, db, merchant_id, state=state, limit=limit, offset=offset)


@router.get("/{merchant_id}/standing-orders")
def merchant_standing_orders(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    return _invoke(ctx, "merchants_read", _standing_orders.list_serialized, db, merchant_id)


@router.post("/{merchant_id}/standing-orders/{standing_order_id}/deactivate")
def deactivate_merchant_standing_order(
    merchant_id: str,
    standing_order_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    def _run() -> dict:
        mctx = admin_merchant_context(db, merchant_id, ctx)
        _standing_orders.deactivate(db, mctx, standing_order_id)
        return {"ok": True, "id": standing_order_id, "is_active": False}

    return _invoke(ctx, "merchants", _run, org=True)


@router.get("/{merchant_id}/statement")
def merchant_statement(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    def _run() -> dict:
        from porterchain_api.merchant_engine.billing_service import MerchantBillingService

        mctx = admin_merchant_context(db, merchant_id, ctx)
        return MerchantBillingService().statement_summary(db, mctx)

    return _invoke(ctx, "merchants_read", _run)


@router.get("/{merchant_id}/credit-notes")
def merchant_credit_notes(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    def _run() -> list[dict]:
        from porterchain_api.merchant_engine.billing_service import MerchantBillingService

        mctx = admin_merchant_context(db, merchant_id, ctx)
        return MerchantBillingService().list_credit_notes(db, mctx)

    return _invoke(ctx, "merchants_read", _run)


@router.get("/{merchant_id}/webhooks/{webhook_id}/deliveries")
def merchant_webhook_deliveries(
    merchant_id: str,
    webhook_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> list[dict]:
    def _run() -> list[dict]:
        from porterchain_api.merchant_engine.integrations_service import MerchantIntegrationsService

        mctx = admin_merchant_context(db, merchant_id, ctx)
        return MerchantIntegrationsService().webhook_history(db, mctx, webhook_id)

    return _invoke(ctx, "merchants_read", _run)


@router.post("/{merchant_id}/webhooks/deliveries/{delivery_id}/retry")
def merchant_webhook_delivery_retry(
    merchant_id: str,
    delivery_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    def _run() -> dict:
        from porterchain_api.merchant_engine.integrations_service import MerchantIntegrationsService

        mctx = admin_merchant_context(db, merchant_id, ctx)
        return MerchantIntegrationsService().retry_delivery(
            db, mctx, delivery_id, encryption_key=settings.jwt_secret
        )

    return _invoke(ctx, "merchants", _run, org=True)


@router.patch("/{merchant_id}/api-keys/{key_id}/rate-limit")
def merchant_api_key_rate_limit(
    merchant_id: str,
    key_id: str,
    body: dict,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    def _run() -> dict:
        from porterchain_api.merchant_engine.integrations_service import MerchantIntegrationsService

        from porterchain_api.admin_engine.merchant_org import write_staff_audit

        from porterchain_api.merchant_engine.api_key_limits import validate_rate_limit

        rpm = validate_rate_limit(body.get("rate_limit_per_minute"))
        svc = MerchantIntegrationsService()
        out = svc.update_api_key_rate_limit(db, admin_merchant_context(db, merchant_id, ctx), key_id, rate_limit_per_minute=rpm)
        payload = {"rate_limit_per_minute": rpm}
        write_staff_audit(db, ctx, merchant_id, action="api_key.rate_limit_changed", resource_type="api_key", resource_id=key_id, payload=payload)
        return out

    return _invoke(ctx, "merchants", _run, org=True, copy=org_error_message)


@router.get("/{merchant_id}/locations")
def merchant_locations(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants_read", _m360.locations, db, merchant_id)


@router.post("/{merchant_id}/addresses", response_model=SavedAddressResponse, status_code=201)
def create_merchant_address(
    merchant_id: str, body: SavedAddressCreateRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> SavedAddressResponse:
    return _invoke(ctx, "merchants", create_address, db, ctx, merchant_id, org=True, **body.model_dump())


@router.patch("/{merchant_id}/addresses/{address_id}", response_model=SavedAddressResponse)
def update_merchant_address(
    merchant_id: str,
    address_id: str,
    body: SavedAddressUpdateRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> SavedAddressResponse:
    return _invoke(ctx, "merchants", update_address, db, ctx, merchant_id, address_id, body, org=True)


@router.post("/{merchant_id}/addresses/{address_id}/default", response_model=SavedAddressResponse)
def set_merchant_default_address(
    merchant_id: str, address_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> SavedAddressResponse:
    return _invoke(ctx, "merchants", set_default_address, db, ctx, merchant_id, address_id, org=True)


@router.delete("/{merchant_id}/addresses/{address_id}", status_code=204)
def delete_merchant_address(
    merchant_id: str, address_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> None:
    _invoke(ctx, "merchants", delete_address, db, ctx, merchant_id, address_id, org=True)


@router.post("/{merchant_id}/recipients", response_model=RecipientResponse, status_code=201)
def create_merchant_recipient(
    merchant_id: str, body: RecipientCreateRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> RecipientResponse:
    return _invoke(ctx, "merchants", create_recipient, db, ctx, merchant_id, org=True, **body.model_dump())


@router.patch("/{merchant_id}/recipients/{recipient_id}", response_model=RecipientResponse)
def update_merchant_recipient(
    merchant_id: str,
    recipient_id: str,
    body: RecipientUpdateRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> RecipientResponse:
    return _invoke(ctx, "merchants", update_recipient, db, ctx, merchant_id, recipient_id, body, org=True)


@router.delete("/{merchant_id}/recipients/{recipient_id}", status_code=204)
def delete_merchant_recipient(
    merchant_id: str, recipient_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> None:
    _invoke(ctx, "merchants", delete_recipient, db, ctx, merchant_id, recipient_id, org=True)


@router.get("/{merchant_id}/billing-contacts")
def list_merchant_billing_contacts(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    return _invoke(ctx, "merchants_read", list_billing_contacts, db, ctx, merchant_id, org=True)


@router.post("/{merchant_id}/billing-contacts", status_code=201)
def create_merchant_billing_contact(
    merchant_id: str, body: BillingContactRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    return _invoke(ctx, "merchants", save_billing_contact, db, ctx, merchant_id, org=True, **body.model_dump())


@router.patch("/{merchant_id}/billing-contacts/{contact_id}")
def patch_merchant_billing_contact(
    merchant_id: str,
    contact_id: str,
    body: BillingContactPatchRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    return _invoke(
        ctx, "merchants", patch_billing_contact, db, ctx, merchant_id, contact_id,
        org=True, **body.model_dump(exclude_unset=True),
    )


@router.delete("/{merchant_id}/billing-contacts/{contact_id}", status_code=204)
def delete_merchant_billing_contact(
    merchant_id: str, contact_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> None:
    _invoke(ctx, "merchants", delete_billing_contact, db, ctx, merchant_id, contact_id, org=True)


@router.get("/{merchant_id}/team")
def merchant_team(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    return _invoke(ctx, "merchants_read", _m360.team, db, merchant_id)


@router.get("/{merchant_id}/onboarding")
def merchant_onboarding(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants_read", _m360.onboarding, db, merchant_id)


@router.post("/{merchant_id}/owner-seat", response_model=MerchantInviteResponse, status_code=201)
def add_merchant_owner_seat(
    merchant_id: str,
    body: MerchantInviteRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantInviteResponse:
    return MerchantInviteResponse(
        **_invoke(ctx, "merchants", reserve_owner_seat, db, ctx, settings, merchant_id, body.email)
    )


@router.post("/{merchant_id}/team/seats", response_model=MerchantInviteResponse, status_code=201)
def add_merchant_team_seat(
    merchant_id: str,
    body: MerchantInviteRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantInviteResponse:
    return MerchantInviteResponse(
        **_invoke(
            ctx, "merchants", reserve_team_seat, db, ctx, settings, merchant_id,
            body.email, body.role or "merchant_ops",
        )
    )


@router.patch("/{merchant_id}/team/{user_id}")
def update_merchant_team_role(
    merchant_id: str, user_id: str, body: MerchantTeamRoleUpdate, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    user = _invoke(
        ctx, "merchants", _merchants.update_team_member, db, ctx, merchant_id, user_id,
        role=body.role, is_active=body.is_active,
    )
    return team_member_payload(user)


@router.delete("/{merchant_id}/team/{user_id}", status_code=204)
def remove_merchant_team_member(
    merchant_id: str, user_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> None:
    _invoke(ctx, "merchants", _merchants.remove_team_member, db, ctx, merchant_id, user_id)


@router.post("/{merchant_id}/activate-users")
def activate_merchant_users(
    merchant_id: str, body: MerchantActivateUsersRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    return _invoke(ctx, "merchants", activate_users_payload, db, ctx, merchant_id, body.email)


@router.post("/{merchant_id}/complete-onboarding")
def complete_merchant_onboarding(
    merchant_id: str,
    body: MerchantCompleteOnboardingRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _invoke(
        ctx, "merchants", complete_onboarding_payload, db, ctx, settings, merchant_id, email=body.email
    )


@router.get("/{merchant_id}/api")
def merchant_api(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants_read", _m360.api_keys, db, merchant_id)


@router.get("/{merchant_id}/ar/preview")
def preview_merchant_ar(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants_read", preview_cycle_ar, db, merchant_id, org=True)


@router.post("/{merchant_id}/ar/generate")
def generate_merchant_ar(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants", generate_cycle_ar, db, ctx, merchant_id, org=True)


@router.get("/{merchant_id}/analytics")
def merchant_analytics(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants_read", _m360.analytics, db, merchant_id)


@router.get("/{merchant_id}/timeline")
def merchant_timeline(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    return _invoke(ctx, "merchants_read", timeline_for, db, merchant_id)


@router.get("/{merchant_id}/contacts", response_model=list[MerchantContactResponse])
def merchant_contacts(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[MerchantContactResponse]:
    rows = _invoke(ctx, "merchants_read", list_contacts, db, ctx, merchant_id, org=True)
    return [MerchantContactResponse(**row) for row in rows]


@router.post("/{merchant_id}/contacts", response_model=MerchantContactResponse, status_code=201)
def create_merchant_contact(
    merchant_id: str, body: MerchantContactCreateRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> MerchantContactResponse:
    return MerchantContactResponse(
        **_invoke(ctx, "merchants", create_contact, db, ctx, merchant_id, body.model_dump(), org=True)
    )


@router.patch("/{merchant_id}/contacts/{contact_id}", response_model=MerchantContactResponse)
def update_merchant_contact(
    merchant_id: str,
    contact_id: str,
    body: MerchantContactUpdateRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> MerchantContactResponse:
    return MerchantContactResponse(
        **_invoke(
            ctx, "merchants", update_contact, db, ctx, merchant_id, contact_id,
            body.model_dump(exclude_unset=True), org=True,
        )
    )


@router.delete("/{merchant_id}/contacts/{contact_id}", status_code=204)
def delete_merchant_contact(
    merchant_id: str, contact_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> None:
    _invoke(ctx, "merchants", delete_contact, db, ctx, merchant_id, contact_id, org=True)


@router.get("/{merchant_id}/contracts", response_model=list[ContractOut])
def merchant_contracts(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[ContractOut]:
    return [ContractOut.model_validate(c) for c in _invoke(ctx, "merchants_read", list_contracts, db, merchant_id)]


@router.post("/{merchant_id}/contracts", response_model=ContractOut, status_code=201)
def create_merchant_contract(
    merchant_id: str, body: ContractCreate, ctx: Ctx, db: Session = Depends(get_db)
) -> ContractOut:
    contract = _invoke(
        ctx, "merchants_read", create_linked_contract, db, ctx, merchant_id, body.model_dump(exclude_unset=True)
    )
    return ContractOut.model_validate(contract)


@router.patch("/{merchant_id}/contracts/{contract_id}", response_model=ContractOut)
def update_merchant_contract(
    merchant_id: str,
    contract_id: str,
    body: ContractUpdate,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> ContractOut:
    contract = _invoke(
        ctx,
        "merchants_read",
        update_linked_contract,
        db,
        merchant_id,
        contract_id,
        body.model_dump(exclude_unset=True),
        ctx,
        org=True,
        copy=org_error_message,
    )
    return ContractOut.model_validate(contract)


@router.get("/{merchant_id}/invoices", response_model=list[InvoiceOut])
def merchant_invoices(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[InvoiceOut]:
    return _invoke(ctx, "merchants_read", _merchants.list_ops_invoices, db, merchant_id)


@router.get("/{merchant_id}/activities", response_model=list[ActivityOut])
def merchant_activities(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[ActivityOut]:
    return [ActivityOut(**row) for row in _invoke(ctx, "merchants_read", list_activities, db, merchant_id)]


@router.get("/{merchant_id}/tasks", response_model=list[TaskOut])
def merchant_tasks(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[TaskOut]:
    return [TaskOut.model_validate(t) for t in _invoke(ctx, "merchants_read", list_tasks, db, merchant_id)]
