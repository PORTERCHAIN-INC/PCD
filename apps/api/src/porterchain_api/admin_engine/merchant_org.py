"""Admin writes the same merchant company file the portal uses."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.merchant_engine.offboard import billing_context
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.merchant_engine.rbac import MerchantContext, parse_merchant_role
from porterchain_api.merchant_models import Merchant, MerchantRecipient, MerchantUser, SavedAddress
from porterchain_api.schemas_merchant import RecipientResponse, SavedAddressResponse

ORG_ERROR_MESSAGES: dict[str, str] = {
    "merchant_not_found": "That company was not found.",
    "address_not_found": "That location was not found.",
    "recipient_not_found": "That recipient was not found.",
    "contact_not_found": "That contact was not found.",
    "billing_contact_not_found": "That billing contact was not found.",
    "team_contacts_are_synced": "Portal teammates appear here automatically. Change them on the Team tab.",
    "team_contact_email_managed_by_team": "This person's login email is managed on the Team tab.",
    "team_contact_remove_via_team": "Remove this teammate from the Team tab, not Contacts.",
    "email_invalid": "Enter a valid email.",
    "api_key_not_found": "That API key was not found.",
    "webhook_not_found": "That webhook was not found.",
    "invalid_period": "Period start must be before period end.",
    "standing_order_not_found": "That standing order was not found.",
    "close_blocked_live_orders": "Close blocked — this company still has live orders.",
    "close_blocked_outstanding_ar": "Close blocked — outstanding invoices must be cleared first.",
    "unsuspend_requires_suspended": "Unsuspend only works when the company is suspended.",
    "reopen_requires_closed": "Reopen only works when the company is closed.",
    "approve_requires_pending_or_onboarding": "Approve only works for pending or onboarding companies.",
    "parent_cannot_be_self": "A company cannot be its own parent.",
    "parent_merchant_not_found": "That parent company was not found.",
    "merchant_already_closed": "This company is already closed.",
    "cannot_suspend_closed": "Closed companies cannot be suspended — use Reopen first.",
    "already_suspended": "This company is already suspended.",
    "suspend_requires_active": "Only active companies can be suspended.",
    "company_name_required": "Company name is required.",
    "nothing_to_update": "Nothing to update.",
    "business_number_invalid": "Enter a valid Canadian business number (9 digits, optional RTxxxx).",
    "hst_number_invalid": "Enter a valid GST/HST number (BN or BN+RTxxxx).",
    "tax_region_invalid": "Tax region must be a Canadian province or territory code (e.g. ON).",
    "rate_limit_invalid": "Rate limit must be at least 10 requests per minute.",
    "contract_not_found": "That contract was not found for this company.",
    "merchant_has_no_crm_company": "Link a CRM company before managing contracts.",
    "delivery_not_found": "That webhook delivery was not found.",
    "shop_not_found": "That Shopify shop was not found.",
    "dlq_not_found": "That Shopify ingress DLQ row was not found.",
    "ingress_still_paused": "Resume Shopify ingress on this shop before replaying held webhooks.",
    "vehicle_class_invalid": "Pick a valid vehicle class (e.g. cargoVan).",
    "package_type_invalid": "Pick a valid package type (e.g. looseParcel).",
    "shop_not_connected": "That Shopify shop is not connected.",
    "shopify_oauth_not_configured": "Shopify OAuth is not configured on this environment.",
    "shop_domain_invalid": "Enter a valid myshopify.com shop domain.",
    "reason_required": "A reason is required for this action.",
    "integrations_elevated_required": "Only Superadmin or Compliance can freeze Partner API, pause Shopify ingress, or force-disconnect Shopify.",
    "source_merchant_not_found": "That source company was not found.",
    "cannot_clone_from_self": "Pick a different company as the pricing template source.",
}


def org_error_message(code: str) -> str:
    return ORG_ERROR_MESSAGES.get(code, code)


def admin_merchant_context(db: Session, merchant_id: str, admin_ctx: AdminContext) -> MerchantContext:
    """Seat for merchant engines. Prefer a live teammate; otherwise a synthetic owner."""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise LookupError("merchant_not_found")
    user = (
        db.query(MerchantUser)
        .filter(MerchantUser.merchant_id == merchant_id, MerchantUser.is_active.is_(True))
        .order_by(MerchantUser.created_at.asc())
        .first()
    )
    if user:
        return MerchantContext(merchant=merchant, user=user, role=parse_merchant_role(user.role))
    ctx = billing_context(merchant)
    ctx.user.id = admin_ctx.user.id
    ctx.user.clerk_user_id = f"admin:{admin_ctx.user.id}"
    ctx.user.email = admin_ctx.user.email or ctx.user.email
    return ctx


def raise_org_http(exc: Exception) -> None:
    code = str(exc) or "merchant_not_found"
    status = 404 if isinstance(exc, LookupError) else 400
    raise HTTPException(status_code=status, detail=org_error_message(code)) from exc


def saved_address_out(row: SavedAddress) -> SavedAddressResponse:
    return SavedAddressResponse(
        id=row.id,
        label=row.label,
        address_type=row.address_type,
        formatted=row.formatted,
        is_default=row.is_default,
        postal=getattr(row, "postal", None),
        lat=row.lat,
        lng=row.lng,
    )


def recipient_out(row: MerchantRecipient) -> RecipientResponse:
    return RecipientResponse(
        id=row.id,
        name=row.name,
        email=row.email,
        phone=row.phone,
        company=row.company,
        default_address=row.default_address,
    )


def linked_company_id(db: Session, merchant_id: str) -> str | None:
    from porterchain_api.admin_engine.merchant360_service import Merchant360Service

    company = Merchant360Service()._linked_company(db, merchant_id)
    return company.id if company else None


def detail_after(db: Session, merchant_id: str) -> dict:
    from porterchain_api.admin_engine.merchant360_service import Merchant360Service

    return Merchant360Service().detail(db, merchant_id) or {}


def after_admin_write(db: Session, ctx: AdminContext, merchant_id: str, writer, **kwargs) -> dict:
    writer(db, ctx, merchant_id, **kwargs)
    return detail_after(db, merchant_id)


def validate_preferred_vehicles(db: Session, preferred: list[str]) -> list[str]:
    """M-6: preferred vehicles must be ⊆ enabled retail catalog."""
    from porterchain_api.domain.retail_vehicles import validate_preferred_vehicles as _validate

    return _validate(db, preferred)


def apply_merchant_terms(
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    *,
    svc=None,
    payment_terms: str | None = None,
    pricing_config: dict | None = None,
    credit_limit_cents: int | None = None,
    parent_merchant_id: str | None = None,
    support_tier: str | None = None,
    billing_cycle: str | None = None,
    preferred_vehicles: list[str] | None = None,
    delivery_zones: list[str] | None = None,
    service_area: str | None = None,
    company_name: str | None = None,
    legal_name: str | None = None,
    email: str | None = None,
    website: str | None = None,
    industry: str | None = None,
    phone: str | None = None,
    hst_number: str | None = None,
    business_number: str | None = None,
    tax_exempt: bool | None = None,
    tax_region: str | None = None,
    billing_address: dict | None = None,
    stripe_enabled: bool | None = None,
    cod_enabled: bool | None = None,
):
    from porterchain_api.admin_engine.merchant_lifecycle import require_billing_cycle
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService
    from porterchain_api.merchant_engine.coverage import apply_coverage
    from porterchain_api.merchant_engine.organization_sync import (
        apply_tax_legal,
        project_merchant_company,
        stamp_identity_meta,
    )

    svc = svc or AdminMerchantService()
    merchant = svc._get_or_raise(db, merchant_id)
    if payment_terms:
        merchant.payment_terms = payment_terms
    if pricing_config is not None:
        merchant.pricing_config = pricing_config
    if credit_limit_cents is not None:
        merchant.credit_limit_cents = credit_limit_cents
    if parent_merchant_id is not None:
        if parent_merchant_id == merchant_id:
            raise ValueError("parent_cannot_be_self")
        if parent_merchant_id:
            parent = svc.get_merchant(db, parent_merchant_id)
            if not parent:
                raise ValueError("parent_merchant_not_found")
        merchant.parent_merchant_id = parent_merchant_id or None
    if support_tier is not None:
        profile = dict(merchant.profile or {})
        enterprise = dict(profile.get("enterprise") or {})
        enterprise["support_tier"] = support_tier
        profile["enterprise"] = enterprise
        merchant.profile = profile
    if billing_cycle is not None:
        merchant.billing_cycle = require_billing_cycle(billing_cycle)
    if preferred_vehicles is not None:
        merchant.preferred_vehicles = svc._validate_preferred_vehicles(db, preferred_vehicles)
    apply_coverage(merchant, service_area=service_area, delivery_zones=delivery_zones)
    if company_name is not None:
        name = company_name.strip()
        if not name:
            raise ValueError("company_name_required")
        merchant.company_name = name
    if email is not None:
        cleaned = email.strip().lower()
        if not cleaned or "@" not in cleaned:
            raise ValueError("email_invalid")
        merchant.email = cleaned
    if phone is not None:
        merchant.phone = phone.strip() or None
    if billing_address is not None:
        merchant.billing_address = billing_address
    if website is not None or industry is not None or stripe_enabled is not None:
        if website is not None:
            merchant.website = website.strip() or None
        if industry is not None:
            merchant.industry = industry.strip() or None
        if stripe_enabled is not None:
            merchant.stripe_enabled = bool(stripe_enabled)
        profile = dict(merchant.profile or {})
        profile.pop("website", None)
        profile.pop("industry", None)
        profile.pop("stripe_enabled", None)
        profile.pop("stripe_checkout", None)
        merchant.profile = profile
    if cod_enabled is not None:
        merchant.cod_enabled = bool(cod_enabled)
    tax_patch: dict[str, object] = {}
    if legal_name is not None:
        tax_patch["legal_name"] = legal_name
    if hst_number is not None:
        tax_patch["hst_number"] = hst_number
    if business_number is not None:
        tax_patch["business_number"] = business_number
    if tax_exempt is not None:
        tax_patch["tax_exempt"] = tax_exempt
    if tax_region is not None:
        tax_patch["tax_region"] = tax_region
    if tax_patch:
        apply_tax_legal(
            merchant,
            actor="admin",
            actor_id=getattr(ctx.user, "id", None),
            **tax_patch,
        )
    stamp_identity_meta(merchant, actor="admin", actor_id=getattr(ctx.user, "id", None))
    project_merchant_company(db, merchant)
    svc._audit(
        db,
        ctx,
        "merchant.terms_updated",
        "merchant",
        merchant_id,
        {
            "payment_terms": payment_terms,
            "parent_merchant_id": parent_merchant_id,
            "support_tier": support_tier,
            "billing_cycle": billing_cycle,
            "preferred_vehicles": preferred_vehicles,
            "delivery_zones": delivery_zones,
            "service_area": service_area,
            "stripe_enabled": stripe_enabled,
            "cod_enabled": cod_enabled,
        },
    )
    return merchant


def create_with_onboarding(db: Session, ctx: AdminContext, settings, **kwargs) -> dict:
    from porterchain_api.admin_engine.merchant360_service import Merchant360Service
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService

    merchant = AdminMerchantService().create_merchant(db, ctx, settings, **kwargs)
    m360 = Merchant360Service()
    return {**(m360.detail(db, merchant.id) or {}), "onboarding": m360.onboarding(db, merchant.id)}


def complete_onboarding_payload(
    db: Session, ctx: AdminContext, settings, merchant_id: str, *, email: str | None
) -> dict:
    from porterchain_api.admin_engine.merchant360_service import Merchant360Service
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService

    merchant = AdminMerchantService().complete_onboarding(
        db, ctx, settings, merchant_id, email=email
    )
    return {
        "merchant_id": merchant.id,
        "status": merchant.status,
        "onboarding": Merchant360Service().onboarding(db, merchant_id),
    }


def merge_pricing_config(db: Session, ctx: AdminContext, merchant_id: str, patch: dict):
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService

    svc = AdminMerchantService()
    merchant = svc.get_merchant(db, merchant_id)
    if not merchant:
        raise LookupError("merchant_not_found")
    config = dict(merchant.pricing_config or {})
    pricing_model = patch.get("pricing_model")
    overlay = {k: v for k, v in patch.items() if k != "pricing_model"}

    if "gta_rate" in overlay:
        gta = overlay.pop("gta_rate")
        if gta is None or gta == {}:
            config.pop("gta_rate", None)
        elif isinstance(gta, dict):
            config["gta_rate"] = dict(gta)

    if "schedule" in overlay:
        schedule = overlay.pop("schedule")
        if schedule is None or schedule == {}:
            config.pop("schedule", None)
        elif isinstance(schedule, dict):
            config["schedule"] = dict(schedule)

    if "rate_card" in overlay:
        card = overlay.pop("rate_card")
        if card is None:
            config.pop("rate_card", None)
        elif isinstance(card, dict):
            merged_card = dict(config.get("rate_card") or {})
            merged_card.update(card)
            config["rate_card"] = merged_card

    config.update(overlay)
    config.pop("pricing_model", None)
    svc.update_merchant_terms(db, ctx, merchant_id, pricing_config=config)
    merchant = svc.get_merchant(db, merchant_id)
    if not merchant:
        raise LookupError("merchant_not_found")
    if pricing_model in ("fsa", "distance"):
        merchant.pricing_model = pricing_model
        db.flush()
    return merchant


def require_merchant(db: Session, merchant_id: str):
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService

    merchant = AdminMerchantService().get_merchant(db, merchant_id)
    if not merchant:
        raise LookupError("merchant_not_found")
    return merchant


def subsidiaries_payload(db: Session, merchant_id: str) -> list[dict]:
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService

    svc = AdminMerchantService()
    require_merchant(db, merchant_id)
    return [
        {
            "merchant_id": m.id,
            "company_name": m.company_name,
            "status": m.status,
            "payment_terms": m.payment_terms,
            "parent_merchant_id": m.parent_merchant_id,
        }
        for m in svc.list_subsidiaries(db, merchant_id)
    ]


def invite_payload(user) -> dict:
    return {
        "merchant_user_id": user.id,
        "email": user.email,
        "role": user.role,
        "invitation_status": "seat_reserved",
        "clerk_user_id": user.clerk_user_id if user.clerk_user_id.startswith("user_") else None,
    }


def create_linked_contract(db: Session, ctx: AdminContext, merchant_id: str, data: dict):
    from porterchain_api.admin_engine.crm_sales_service import CrmSalesService

    require_merchant(db, merchant_id)
    cid = linked_company_id(db, merchant_id)
    if not cid:
        raise ValueError("merchant_has_no_crm_company")
    payload = {**data, "company_id": cid}
    return CrmSalesService().create_contract(db, ctx, payload)


def require_detail(db: Session, merchant_id: str) -> dict:
    detail = detail_after(db, merchant_id)
    if not detail:
        raise LookupError("merchant_not_found")
    return detail


def pricing_view_for(db: Session, merchant_id: str) -> dict:
    from porterchain_api.merchant_engine.rate_card_view import admin_pricing_view

    return admin_pricing_view(db, require_merchant(db, merchant_id))


def merge_pricing_view(db: Session, ctx: AdminContext, merchant_id: str, patch: dict) -> dict:
    from porterchain_api.merchant_engine.rate_card_view import admin_pricing_view

    return admin_pricing_view(db, merge_pricing_config(db, ctx, merchant_id, patch))


def apply_kaylulu_pricing_template(db: Session, ctx: AdminContext, merchant_id: str) -> dict:
    """Write Kaylulu schedule + A3 size_tiers onto this merchant (FSA rows unchanged)."""
    from porterchain_api.merchant_engine.kaylulu_template import kaylulu_pricing_config
    from porterchain_api.merchant_engine.rate_card_view import admin_pricing_view

    merchant = require_merchant(db, merchant_id)
    merchant.pricing_config = kaylulu_pricing_config(existing=merchant.pricing_config)
    merchant.pricing_model = "fsa"
    db.flush()
    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="pricing.kaylulu_template_applied",
        resource_type="pricing",
        resource_id=merchant_id,
        payload={},
    )
    return admin_pricing_view(db, merchant)


def clone_pricing_from(
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    source_merchant_id: str,
    *,
    include_fsa: bool = False,
) -> dict:
    """Copy pricing_model + pricing_config (and optionally FSA rows) from source → target."""
    from copy import deepcopy

    from porterchain_api.admin_models import PricingFsaRate
    from porterchain_api.merchant_engine.rate_card_view import admin_pricing_view

    if source_merchant_id == merchant_id:
        raise ValueError("cannot_clone_from_self")
    target = require_merchant(db, merchant_id)
    source = require_merchant(db, source_merchant_id)
    if not source:
        raise LookupError("source_merchant_not_found")

    target.pricing_model = source.pricing_model
    target.pricing_config = deepcopy(source.pricing_config or {})
    db.flush()

    fsa_copied = 0
    if include_fsa:
        db.query(PricingFsaRate).filter(PricingFsaRate.merchant_id == merchant_id).delete(
            synchronize_session=False
        )
        rows = (
            db.query(PricingFsaRate)
            .filter(PricingFsaRate.merchant_id == source_merchant_id)
            .all()
        )
        for row in rows:
            db.add(
                PricingFsaRate(
                    merchant_id=merchant_id,
                    origin_fsa=row.origin_fsa,
                    dest_fsa=row.dest_fsa,
                    vehicle_class=row.vehicle_class,
                    flat_cents=row.flat_cents,
                    includes_location_fees=row.includes_location_fees,
                    label=row.label,
                    is_active=row.is_active,
                    config=deepcopy(row.config or {}),
                )
            )
            fsa_copied += 1
        db.flush()

    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="pricing.cloned_from",
        resource_type="pricing",
        resource_id=merchant_id,
        payload={
            "source_merchant_id": source_merchant_id,
            "include_fsa": include_fsa,
            "fsa_rows_copied": fsa_copied,
        },
    )
    view = admin_pricing_view(db, target)
    view["clone"] = {
        "source_merchant_id": source_merchant_id,
        "include_fsa": include_fsa,
        "fsa_rows_copied": fsa_copied,
    }
    return view


def timeline_for(db: Session, merchant_id: str) -> list[dict]:
    from porterchain_api.admin_engine.merchant360_service import Merchant360Service

    return Merchant360Service().timeline(db, merchant_id, linked_company_id(db, merchant_id))


def list_contracts(db: Session, merchant_id: str) -> list:
    from porterchain_api.admin_engine.crm_sales_service import CrmSalesService

    cid = linked_company_id(db, merchant_id)
    return CrmSalesService().list_contracts(db, company_id=cid) if cid else []


def update_linked_contract(db: Session, merchant_id: str, contract_id: str, data: dict):
    from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
    from porterchain_api.crm_models import CrmContract

    cid = linked_company_id(db, merchant_id)
    if not cid:
        raise ValueError("merchant_has_no_crm_company")
    contract = db.get(CrmContract, contract_id)
    if not contract or contract.company_id != cid:
        raise LookupError("contract_not_found")
    return CrmSalesService().update_contract(db, contract_id, data)

def list_activities(db: Session, merchant_id: str) -> list[dict]:
    from porterchain_api.admin_engine.crm_sales_service import CrmSalesService

    crm = CrmSalesService()
    cid = linked_company_id(db, merchant_id)
    rows = crm.list_activities(db, entity_id=cid) if cid else crm.list_activities(db, entity_id=merchant_id)
    return [crm.activity_dict(a) for a in rows]


def list_tasks(db: Session, merchant_id: str) -> list:
    from porterchain_api.admin_engine.crm_sales_service import CrmSalesService

    cid = linked_company_id(db, merchant_id)
    return CrmSalesService().list_tasks(db, entity_id=cid) if cid else []


def reserve_owner_seat(db: Session, ctx: AdminContext, settings, merchant_id: str, email: str) -> dict:
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService

    return invite_payload(AdminMerchantService().invite_owner(db, ctx, settings, merchant_id, email=email))


def reserve_team_seat(
    db: Session, ctx: AdminContext, settings, merchant_id: str, email: str, role: str
) -> dict:
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService

    return invite_payload(
        AdminMerchantService().invite_team_member(db, ctx, settings, merchant_id, email=email, role=role)
    )


def activate_users_payload(db: Session, ctx: AdminContext, merchant_id: str, email: str | None) -> dict:
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService

    users = AdminMerchantService().activate_merchant_users(db, ctx, merchant_id, email=email)
    return {"activated": len(users), "emails": [u.email for u in users]}


def team_member_payload(user) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role, "is_active": user.is_active}


def create_address(db: Session, ctx: AdminContext, merchant_id: str, **fields):
    from porterchain_api.merchant_engine.profile_service import MerchantProfileService

    seat = admin_merchant_context(db, merchant_id, ctx)
    return saved_address_out(MerchantProfileService().create_saved_address(db, seat, **fields))


def update_address(db: Session, ctx: AdminContext, merchant_id: str, address_id: str, body):
    from porterchain_api.merchant_engine.profile_service import MerchantProfileService

    seat = admin_merchant_context(db, merchant_id, ctx)
    return saved_address_out(MerchantProfileService().update_saved_address(db, seat, address_id, body))


def set_default_address(db: Session, ctx: AdminContext, merchant_id: str, address_id: str):
    from porterchain_api.merchant_engine.profile_service import MerchantProfileService

    seat = admin_merchant_context(db, merchant_id, ctx)
    return saved_address_out(MerchantProfileService().set_default_saved_address(db, seat, address_id))


def delete_address(db: Session, ctx: AdminContext, merchant_id: str, address_id: str) -> None:
    from porterchain_api.merchant_engine.profile_service import MerchantProfileService

    seat = admin_merchant_context(db, merchant_id, ctx)
    MerchantProfileService().delete_saved_address(db, seat, address_id)


def create_recipient(db: Session, ctx: AdminContext, merchant_id: str, **fields):
    from porterchain_api.merchant_engine.profile_service import MerchantProfileService

    seat = admin_merchant_context(db, merchant_id, ctx)
    return recipient_out(MerchantProfileService().create_recipient(db, seat, **fields))


def update_recipient(db: Session, ctx: AdminContext, merchant_id: str, recipient_id: str, body):
    from porterchain_api.merchant_engine.profile_service import MerchantProfileService

    seat = admin_merchant_context(db, merchant_id, ctx)
    return recipient_out(MerchantProfileService().update_recipient(db, seat, recipient_id, body))


def delete_recipient(db: Session, ctx: AdminContext, merchant_id: str, recipient_id: str) -> None:
    from porterchain_api.merchant_engine.profile_service import MerchantProfileService

    seat = admin_merchant_context(db, merchant_id, ctx)
    MerchantProfileService().delete_recipient(db, seat, recipient_id)


def list_billing_contacts(db: Session, ctx: AdminContext, merchant_id: str) -> list[dict]:
    from porterchain_api.merchant_engine.settings_service import MerchantSettingsService

    seat = admin_merchant_context(db, merchant_id, ctx)
    return MerchantSettingsService().list_billing_contacts(seat)


def save_billing_contact(db: Session, ctx: AdminContext, merchant_id: str, **fields) -> dict:
    from porterchain_api.merchant_engine.settings_service import MerchantSettingsService

    seat = admin_merchant_context(db, merchant_id, ctx)
    return MerchantSettingsService().save_billing_contact(db, seat, **fields)


def patch_billing_contact(db: Session, ctx: AdminContext, merchant_id: str, contact_id: str, **fields) -> dict:
    from porterchain_api.merchant_engine.settings_service import MerchantSettingsService

    seat = admin_merchant_context(db, merchant_id, ctx)
    return MerchantSettingsService().patch_billing_contact(db, seat, contact_id, **fields)


def delete_billing_contact(db: Session, ctx: AdminContext, merchant_id: str, contact_id: str) -> None:
    from porterchain_api.merchant_engine.settings_service import MerchantSettingsService

    seat = admin_merchant_context(db, merchant_id, ctx)
    MerchantSettingsService().delete_billing_contact(db, seat, contact_id)


def list_contacts(db: Session, ctx: AdminContext, merchant_id: str) -> list[dict]:
    from porterchain_api.merchant_engine.contacts_service import MerchantContactsService

    seat = admin_merchant_context(db, merchant_id, ctx)
    return MerchantContactsService().list_contacts(db, seat)


def create_contact(db: Session, ctx: AdminContext, merchant_id: str, data: dict) -> dict:
    from porterchain_api.merchant_engine.contacts_service import MerchantContactsService

    seat = admin_merchant_context(db, merchant_id, ctx)
    return MerchantContactsService().create_contact(db, seat, data)


def update_contact(db: Session, ctx: AdminContext, merchant_id: str, contact_id: str, data: dict) -> dict:
    from porterchain_api.merchant_engine.contacts_service import MerchantContactsService

    seat = admin_merchant_context(db, merchant_id, ctx)
    return MerchantContactsService().update_contact(db, seat, contact_id, data)


def delete_contact(db: Session, ctx: AdminContext, merchant_id: str, contact_id: str) -> None:
    from porterchain_api.merchant_engine.contacts_service import MerchantContactsService

    seat = admin_merchant_context(db, merchant_id, ctx)
    MerchantContactsService().delete_contact(db, seat, contact_id)


def _staff_payload(ctx: AdminContext, extra: dict | None = None) -> dict:
    body = {
        "admin_user_id": ctx.user.id,
        "admin_email": getattr(ctx.user, "email", None),
        "admin_role": ctx.role.value,
    }
    if extra:
        body.update(extra)
    return body


def write_staff_audit(
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None,
    payload: dict | None = None,
) -> None:
    from porterchain_api.merchant_models import MerchantAuditLog

    db.add(
        MerchantAuditLog(
            merchant_id=merchant_id,
            actor_user_id=f"admin:{ctx.user.id}",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=_staff_payload(ctx, payload),
        )
    )
    db.commit()


def require_integrations_elevated(ctx: AdminContext) -> None:
    from porterchain_api.admin_engine.rbac import AdminRole

    if ctx.role not in (AdminRole.SUPER_ADMIN, AdminRole.COMPLIANCE):
        raise PermissionError(org_error_message("integrations_elevated_required"))


def revoke_api_key(db: Session, ctx: AdminContext, merchant_id: str, key_id: str) -> None:
    from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService

    seat = admin_merchant_context(db, merchant_id, ctx)
    MerchantApiKeyService().revoke_key(db, seat, key_id)
    write_staff_audit(
        db, ctx, merchant_id, action="api_key.revoked", resource_type="api_key", resource_id=key_id
    )


def deactivate_webhook(db: Session, ctx: AdminContext, merchant_id: str, webhook_id: str) -> None:
    from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService

    seat = admin_merchant_context(db, merchant_id, ctx)
    MerchantApiKeyService().deactivate_webhook(db, seat, webhook_id)
    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="webhook.disabled",
        resource_type="webhook",
        resource_id=webhook_id,
    )


def activate_webhook(db: Session, ctx: AdminContext, merchant_id: str, webhook_id: str) -> None:
    from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService

    seat = admin_merchant_context(db, merchant_id, ctx)
    MerchantApiKeyService().activate_webhook(db, seat, webhook_id)
    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="webhook.enabled",
        resource_type="webhook",
        resource_id=webhook_id,
    )


def freeze_partner_api(
    db: Session, ctx: AdminContext, merchant_id: str, *, reason: str | None = None
) -> dict:
    from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService
    from porterchain_api.merchant_models import MerchantApiKey, MerchantWebhook

    require_integrations_elevated(ctx)
    note = (reason or "").strip()
    if not note:
        raise ValueError("reason_required")

    seat = admin_merchant_context(db, merchant_id, ctx)
    svc = MerchantApiKeyService()
    keys = (
        db.query(MerchantApiKey)
        .filter(MerchantApiKey.merchant_id == merchant_id, MerchantApiKey.is_active.is_(True))
        .all()
    )
    hooks = (
        db.query(MerchantWebhook)
        .filter(MerchantWebhook.merchant_id == merchant_id, MerchantWebhook.is_active.is_(True))
        .all()
    )
    for key in keys:
        svc.revoke_key(db, seat, key.id)
    for hook in hooks:
        svc.deactivate_webhook(db, seat, hook.id)

    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="partner_api.frozen",
        resource_type="partner_api",
        resource_id=merchant_id,
        payload={"reason": note, "keys_revoked": len(keys), "webhooks_disabled": len(hooks)},
    )
    return {"keys_revoked": len(keys), "webhooks_disabled": len(hooks), "reason": note}


def force_disconnect_shopify(
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    shop_id: str,
    *,
    reason: str | None = None,
) -> None:
    from porterchain_api.merchant_engine.shopify_service import disconnect_shop

    require_integrations_elevated(ctx)
    note = (reason or "").strip()
    if not note:
        raise ValueError("reason_required")

    seat = admin_merchant_context(db, merchant_id, ctx)
    disconnect_shop(db, seat, shop_id)
    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="shopify.force_disconnected",
        resource_type="shopify_shop",
        resource_id=shop_id,
        payload={"reason": note},
    )


def shopify_install_url_for(
    db: Session, ctx: AdminContext, merchant_id: str, settings, *, shop: str
) -> dict:
    from porterchain_api.merchant_engine.shopify_urls import install_url

    require_merchant(db, merchant_id)
    url = install_url(shop, settings, merchant_id=merchant_id)
    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="shopify.install_url_copied",
        resource_type="shopify_shop",
        resource_id=None,
        payload={"shop_domain": shop},
    )
    return {"install_url": url, "shop_domain": shop, "merchant_id": merchant_id}


def test_webhook(
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    webhook_id: str,
    *,
    encryption_key: str,
) -> dict:
    from porterchain_api.merchant_engine.integrations_service import MerchantIntegrationsService

    seat = admin_merchant_context(db, merchant_id, ctx)
    result = MerchantIntegrationsService().test_webhook(
        db, seat, webhook_id, encryption_key=encryption_key
    )
    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="webhook.test",
        resource_type="webhook",
        resource_id=webhook_id,
        payload={"success": bool(result.get("success")) if isinstance(result, dict) else None},
    )
    return result


def preview_cycle_ar(db: Session, merchant_id: str) -> dict:
    from porterchain_api.admin_engine.merchant_ar_service import MerchantArService

    return MerchantArService().preview(db, merchant_id=merchant_id)


def generate_cycle_ar(db: Session, ctx: AdminContext, merchant_id: str) -> dict:
    from porterchain_api.admin_engine.merchant_ar_service import MerchantArService

    return MerchantArService().generate(db, ctx, merchant_id=merchant_id)
