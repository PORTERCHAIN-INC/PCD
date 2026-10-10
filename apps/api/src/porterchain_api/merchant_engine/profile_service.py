"""Merchant business profile, saved addresses, and recipients."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.stop_sync import persist_address
from porterchain_api.merchant_engine.organization_sync import (
    apply_tax_legal,
    industry_of,
    project_merchant_company,
    stamp_identity_meta,
    website_of,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantRecipient, SavedAddress
from porterchain_api.schemas_merchant import (
    MerchantProfileUpdateRequest,
    RecipientUpdateRequest,
    SavedAddressUpdateRequest,
)


def _profile_map(merchant: Merchant) -> dict[str, Any]:
    return dict(merchant.profile) if isinstance(merchant.profile, dict) else {}


def _tax_legal_patch(body: Any) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    for key in ("legal_name", "hst_number", "business_number", "tax_exempt", "tax_region"):
        if hasattr(body, key) and getattr(body, key) is not None:
            patch[key] = getattr(body, key)
    return patch


class MerchantProfileService:
    def get_profile(self, ctx: MerchantContext) -> Merchant:
        return ctx.merchant

    def update_profile(
        self,
        db: Session,
        ctx: MerchantContext,
        body: MerchantProfileUpdateRequest,
    ) -> Merchant:
        merchant = ctx.merchant
        for field in (
            "company_name",
            "phone",
            "billing_address",
        ):
            value = getattr(body, field)
            if value is not None:
                setattr(merchant, field, value)
        apply_tax_legal(
            merchant,
            actor="merchant",
            actor_id=ctx.user.id,
            **_tax_legal_patch(body),
        )
        if body.email is not None:
            email = body.email.strip().lower()
            if not email or "@" not in email:
                raise ValueError("email_invalid")
            merchant.email = email

        profile = _profile_map(merchant)
        if body.website is not None:
            merchant.website = body.website.strip() or None
            profile.pop("website", None)
        if body.industry is not None:
            merchant.industry = body.industry.strip() or None
            profile.pop("industry", None)
        profile.pop("stripe_enabled", None)
        profile.pop("hst_number", None)
        profile.pop("business_number", None)
        profile.pop("legal_name", None)
        merchant.profile = profile
        stamp_identity_meta(merchant, actor="merchant", actor_id=ctx.user.id)
        project_merchant_company(db, merchant)
        db.commit()
        db.refresh(merchant)
        return merchant

    def list_saved_addresses(self, db: Session, ctx: MerchantContext) -> list[SavedAddress]:
        return (
            db.query(SavedAddress)
            .filter(SavedAddress.merchant_id == ctx.merchant.id)
            .order_by(SavedAddress.is_default.desc(), SavedAddress.label)
            .all()
        )

    def _get_address(self, db: Session, ctx: MerchantContext, address_id: str) -> SavedAddress:
        record = (
            db.query(SavedAddress)
            .filter(SavedAddress.id == address_id, SavedAddress.merchant_id == ctx.merchant.id)
            .first()
        )
        if not record:
            raise LookupError("address_not_found")
        return record

    def _clear_defaults(self, db: Session, merchant_id: str) -> None:
        db.query(SavedAddress).filter(SavedAddress.merchant_id == merchant_id).update(
            {"is_default": False}
        )

    def create_saved_address(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        label: str,
        address_type: str,
        formatted: str,
        place_id: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        postal: str | None = None,
        is_default: bool = False,
    ) -> SavedAddress:
        if is_default:
            self._clear_defaults(db, ctx.merchant.id)
        shared = persist_address(
            db,
            {
                "formatted": formatted,
                "place_id": place_id,
                "lat": lat,
                "lng": lng,
                "postal": postal,
            },
        )
        record = SavedAddress(
            merchant_id=ctx.merchant.id,
            label=label,
            address_type=address_type,
            formatted=formatted,
            place_id=place_id,
            lat=lat,
            lng=lng,
            postal=postal,
            is_default=is_default,
            address_id=shared.id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        self._bind_shopify_pickups(db, record)
        return record

    def update_saved_address(
        self,
        db: Session,
        ctx: MerchantContext,
        address_id: str,
        body: SavedAddressUpdateRequest,
    ) -> SavedAddress:
        record = self._get_address(db, ctx, address_id)
        for field in ("label", "address_type", "formatted", "place_id", "lat", "lng", "postal"):
            value = getattr(body, field)
            if value is not None:
                setattr(record, field, value)
        if body.is_default is True:
            self._clear_defaults(db, ctx.merchant.id)
            record.is_default = True
        elif body.is_default is False:
            record.is_default = False
        db.commit()
        db.refresh(record)
        self._bind_shopify_pickups(db, record)
        return record

    def set_default_saved_address(
        self, db: Session, ctx: MerchantContext, address_id: str
    ) -> SavedAddress:
        record = self._get_address(db, ctx, address_id)
        self._clear_defaults(db, ctx.merchant.id)
        record.is_default = True
        db.commit()
        db.refresh(record)
        self._bind_shopify_pickups(db, record)
        return record

    def _bind_shopify_pickups(self, db: Session, record: SavedAddress) -> None:
        if record.address_type not in ("pickup", "warehouse"):
            return
        from porterchain_api.merchant_engine.shopify_one_click import (
            bind_merchant_shop_pickups,
        )

        bind_merchant_shop_pickups(db, record.merchant_id)

    def delete_saved_address(self, db: Session, ctx: MerchantContext, address_id: str) -> None:
        record = self._get_address(db, ctx, address_id)
        db.delete(record)
        db.commit()

    def list_recipients(self, db: Session, ctx: MerchantContext) -> list[MerchantRecipient]:
        return (
            db.query(MerchantRecipient)
            .filter(MerchantRecipient.merchant_id == ctx.merchant.id)
            .order_by(MerchantRecipient.name)
            .all()
        )

    def _get_recipient(
        self, db: Session, ctx: MerchantContext, recipient_id: str
    ) -> MerchantRecipient:
        record = (
            db.query(MerchantRecipient)
            .filter(
                MerchantRecipient.id == recipient_id,
                MerchantRecipient.merchant_id == ctx.merchant.id,
            )
            .first()
        )
        if not record:
            raise LookupError("recipient_not_found")
        return record

    def create_recipient(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        name: str,
        email: str | None = None,
        phone: str | None = None,
        company: str | None = None,
        default_address: dict | None = None,
    ) -> MerchantRecipient:
        record = MerchantRecipient(
            merchant_id=ctx.merchant.id,
            name=name,
            email=email,
            phone=phone,
            company=company,
            default_address=default_address,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def update_recipient(
        self,
        db: Session,
        ctx: MerchantContext,
        recipient_id: str,
        body: RecipientUpdateRequest,
    ) -> MerchantRecipient:
        record = self._get_recipient(db, ctx, recipient_id)
        for field in ("name", "email", "phone", "company", "default_address"):
            value = getattr(body, field)
            if value is not None:
                setattr(record, field, value)
        db.commit()
        db.refresh(record)
        return record

    def delete_recipient(self, db: Session, ctx: MerchantContext, recipient_id: str) -> None:
        record = self._get_recipient(db, ctx, recipient_id)
        db.delete(record)
        db.commit()

    def me_payload(self, ctx: MerchantContext) -> dict[str, Any]:
        from porterchain_api.merchant_engine.rbac import english_role

        return {
            "user_id": ctx.user.id,
            "user_email": ctx.user.email,
            "role": ctx.role.value,
            "role_label": english_role(ctx.role),
            "merchant_id": ctx.merchant.id,
            "company_name": ctx.merchant.company_name,
            "status": ctx.merchant.status,
        }

    def session_payload(self, ctx: MerchantContext, db: Session) -> dict[str, Any]:
        from porterchain_api.merchant_engine.company_file import (
            can_edit_company_file,
            completeness_payload,
            merchant_status_label,
        )
        from porterchain_api.merchant_engine.coverage import coverage_snapshot
        from porterchain_api.merchant_engine.organization_sync import branding_logo_url
        from porterchain_api.merchant_engine.rbac import english_role, modules_for_role

        return {
            "merchant_id": ctx.merchant.id,
            "company_name": ctx.merchant.company_name,
            "role": ctx.role.value,
            "role_label": english_role(ctx.role),
            "modules": sorted(modules_for_role(ctx.role)),
            "user_email": ctx.user.email,
            "status": ctx.merchant.status,
            "status_label": merchant_status_label(ctx.merchant.status),
            "logo_url": branding_logo_url(ctx.merchant),
            "completeness": completeness_payload(
                ctx.merchant,
                can_edit=can_edit_company_file(ctx.merchant.status, ctx.role),
            ),
            "coverage": coverage_snapshot(ctx.merchant, db),
        }


def profile_public_fields(merchant: Merchant) -> dict[str, Any]:
    profile = _profile_map(merchant)
    meta = profile.get("identity_meta")
    return {
        "website": website_of(merchant),
        "industry": industry_of(merchant),
        "identity_meta": meta if isinstance(meta, dict) else None,
    }
