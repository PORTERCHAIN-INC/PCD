"""Merchant settings — profile extensions in merchant.profile (masterrule §3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.company_file import (
    can_edit_company_file,
    completeness_payload,
)
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import MerchantAuditLog, SavedAddress
from porterchain_api.schemas_merchant import MerchantProfileUpdateRequest

DEFAULT_NOTIFICATIONS = {
    "order_booked": True,
    "order_delivered": True,
    "order_failed": True,
    "invoice_generated": True,
    "payment_received": True,
    "claim_updates": True,
    "support_replies": True,
    "weekly_summary": False,
    "channels": {"email": True, "in_app": True},
}

DEFAULT_BRANDING = {
    "logo_url": None,
    "primary_color": "#1e3a5f",
    "accent_color": "#f59e0b",
    "tracking_page_message": None,
    "tracking_domain": None,
    "white_label_enabled": False,
}


def _settings_bucket(merchant) -> dict[str, Any]:
    profile = merchant.profile if isinstance(merchant.profile, dict) else {}
    settings = profile.get("settings")
    return dict(settings) if isinstance(settings, dict) else {}


def _save_settings(merchant, settings: dict[str, Any]) -> None:
    profile = dict(merchant.profile or {})
    profile["settings"] = settings
    merchant.profile = profile


class MerchantSettingsService:
    def __init__(self) -> None:
        self._profile = MerchantProfileService()
        self._billing = MerchantBillingService()

    def overview(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        merchant = ctx.merchant
        settings = _settings_bucket(merchant)
        pickups = [
            a for a in self._profile.list_saved_addresses(db, ctx) if a.address_type in ("pickup", "warehouse")
        ]
        from porterchain_api.compliance_engine.privacy_service import (
            merchant_privacy_file,
        )

        return {
            "profile": self._serialize_profile(merchant, db),
            "notifications": settings.get("notifications") or dict(DEFAULT_NOTIFICATIONS),
            "branding": settings.get("branding") or dict(DEFAULT_BRANDING),
            "billing_contacts": list(settings.get("billing_contacts") or []),
            "warehouses": list(settings.get("warehouses") or []),
            "pickup_locations": [
                {
                    "id": a.id,
                    "label": a.label,
                    "address_type": a.address_type,
                    "formatted": a.formatted,
                    "is_default": a.is_default,
                }
                for a in pickups
            ],
            "documents": list(settings.get("documents") or []),
            "tax": self.tax_info(ctx),
            "contract": self._billing.contract_pricing(db, ctx),
            "privacy": merchant_privacy_file(merchant),
            "quiet_hours": self.quiet_hours(db, merchant),
            "completeness": completeness_payload(
                merchant,
                can_edit=can_edit_company_file(merchant.status, ctx.role),
            ),
        }

    def update_notifications(self, db: Session, ctx: MerchantContext, body: dict[str, Any]) -> dict[str, Any]:
        settings = _settings_bucket(ctx.merchant)
        current = dict(settings.get("notifications") or DEFAULT_NOTIFICATIONS)
        patch = dict(body)
        channels_patch = patch.pop("channels", None)
        current.update(patch)
        if isinstance(channels_patch, dict):
            channels = dict(current.get("channels") or DEFAULT_NOTIFICATIONS["channels"])
            channels.update(channels_patch)
            current["channels"] = channels
        if "channels" not in current or not isinstance(current["channels"], dict):
            current["channels"] = dict(DEFAULT_NOTIFICATIONS["channels"])
        settings["notifications"] = current
        _save_settings(ctx.merchant, settings)
        from porterchain_api.notification_engine.preference_service import (
            PreferenceService,
        )

        PreferenceService().sync_merchant_portal_prefs(
            db, merchant_id=ctx.merchant.id, portal_prefs=current
        )
        self._audit(db, ctx, "settings.notifications", current)
        db.commit()
        db.refresh(ctx.merchant)
        return current

    def quiet_hours(self, db: Session, merchant: Any) -> dict[str, Any]:
        from porterchain_api.notification_engine.user_settings import (
            UserSettingsService,
        )

        svc = UserSettingsService()
        tz = svc.resolve_timezone(db, user_role="merchant", user_id=merchant.id)
        row = svc.get(db, user_role="merchant", user_id=merchant.id)
        return svc.to_dict(row, timezone_fallback=tz or "America/Toronto")

    def update_branding(self, db: Session, ctx: MerchantContext, body: dict[str, Any]) -> dict[str, Any]:
        from porterchain_api.merchant_engine.organization_sync import sanitize_logo_url

        settings = _settings_bucket(ctx.merchant)
        current = dict(settings.get("branding") or DEFAULT_BRANDING)
        patch = dict(body)
        if "logo_url" in patch:
            patch["logo_url"] = sanitize_logo_url(patch.get("logo_url"))
        current.update(patch)
        settings["branding"] = current
        _save_settings(ctx.merchant, settings)
        from porterchain_api.merchant_engine.organization_sync import (
            project_merchant_company,
        )

        project_merchant_company(db, ctx.merchant)
        self._audit(db, ctx, "settings.branding", current)
        db.commit()
        db.refresh(ctx.merchant)
        return current

    def list_billing_contacts(self, ctx: MerchantContext) -> list[dict[str, Any]]:
        return list(_settings_bucket(ctx.merchant).get("billing_contacts") or [])

    def save_billing_contact(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        name: str,
        email: str,
        phone: str | None = None,
        role: str | None = None,
        is_primary: bool | None = None,
        contact_id: str | None = None,
    ) -> dict[str, Any]:
        settings = _settings_bucket(ctx.merchant)
        contacts = list(settings.get("billing_contacts") or [])
        make_primary = bool(is_primary) or (not contact_id and len(contacts) == 0)
        record = {
            "id": contact_id or str(uuid.uuid4()),
            "name": name,
            "email": email,
            "phone": phone,
            "role": role or "billing",
            "is_primary": make_primary,
        }
        if contact_id:
            replaced = False
            next_contacts = []
            for existing in contacts:
                if existing.get("id") == contact_id:
                    next_contacts.append(record)
                    replaced = True
                else:
                    next_contacts.append(existing)
            if not replaced:
                next_contacts.append(record)
            contacts = next_contacts
        else:
            contacts.append(record)
        if make_primary:
            contacts = [{**c, "is_primary": c.get("id") == record["id"]} for c in contacts]
        settings["billing_contacts"] = contacts
        _save_settings(ctx.merchant, settings)
        db.commit()
        db.refresh(ctx.merchant)
        return record

    def patch_billing_contact(
        self,
        db: Session,
        ctx: MerchantContext,
        contact_id: str,
        *,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        role: str | None = None,
        is_primary: bool | None = None,
    ) -> dict[str, Any]:
        settings = _settings_bucket(ctx.merchant)
        contacts = list(settings.get("billing_contacts") or [])
        record = next((c for c in contacts if c.get("id") == contact_id), None)
        if not record:
            raise LookupError("billing_contact_not_found")
        if name is not None:
            record["name"] = name
        if email is not None:
            record["email"] = email
        if phone is not None:
            record["phone"] = phone
        if role is not None:
            record["role"] = role
        if is_primary is True:
            contacts = [{**c, "is_primary": c.get("id") == contact_id} for c in contacts]
            record = next(c for c in contacts if c.get("id") == contact_id)
        elif is_primary is False:
            record["is_primary"] = False
        contacts = [record if c.get("id") == contact_id else c for c in contacts]
        settings["billing_contacts"] = contacts
        _save_settings(ctx.merchant, settings)
        db.commit()
        db.refresh(ctx.merchant)
        return record

    def delete_billing_contact(self, db: Session, ctx: MerchantContext, contact_id: str) -> None:
        settings = _settings_bucket(ctx.merchant)
        contacts = [c for c in settings.get("billing_contacts") or [] if c.get("id") != contact_id]
        if contacts and not any(c.get("is_primary") for c in contacts):
            contacts[0] = {**contacts[0], "is_primary": True}
        settings["billing_contacts"] = contacts
        _save_settings(ctx.merchant, settings)
        db.commit()

    def list_warehouses(self, ctx: MerchantContext) -> list[dict[str, Any]]:
        return list(_settings_bucket(ctx.merchant).get("warehouses") or [])

    def save_warehouse(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        name: str,
        formatted: str,
        warehouse_id: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        postal: str | None = None,
        is_default: bool = False,
    ) -> dict[str, Any]:
        settings = _settings_bucket(ctx.merchant)
        warehouses = list(settings.get("warehouses") or [])
        record = {
            "id": warehouse_id or str(uuid.uuid4()),
            "name": name,
            "formatted": formatted,
            "lat": lat,
            "lng": lng,
            "postal": postal,
            "is_default": is_default,
        }
        if is_default:
            for w in warehouses:
                w["is_default"] = False
        if warehouse_id:
            found = False
            for i, w in enumerate(warehouses):
                if w.get("id") == warehouse_id:
                    warehouses[i] = {**w, **record}
                    found = True
                    break
            if not found:
                warehouses.append(record)
        else:
            warehouses.append(record)
        settings["warehouses"] = warehouses
        _save_settings(ctx.merchant, settings)
        self._sync_pickup_address(
            db,
            ctx,
            label=name,
            formatted=formatted,
            lat=lat,
            lng=lng,
            postal=postal,
            is_default=is_default,
        )
        db.commit()
        db.refresh(ctx.merchant)
        return record

    def _sync_pickup_address(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        label: str,
        formatted: str,
        lat: float | None,
        lng: float | None,
        postal: str | None,
        is_default: bool,
    ) -> None:
        """Warehouses used to live only in profile JSON. Shopify needs a real pickup row."""
        if is_default:
            db.query(SavedAddress).filter(SavedAddress.merchant_id == ctx.merchant.id).update(
                {"is_default": False}
            )
        existing = (
            db.query(SavedAddress)
            .filter(SavedAddress.merchant_id == ctx.merchant.id, SavedAddress.formatted == formatted)
            .first()
        )
        if existing is None:
            db.add(
                SavedAddress(
                    merchant_id=ctx.merchant.id,
                    label=label,
                    address_type="warehouse",
                    formatted=formatted,
                    lat=lat,
                    lng=lng,
                    postal=postal,
                    is_default=is_default,
                )
            )
            return
        existing.label = label
        existing.lat = lat if lat is not None else existing.lat
        existing.lng = lng if lng is not None else existing.lng
        existing.postal = postal or existing.postal
        existing.is_default = is_default or existing.is_default

    def delete_warehouse(self, db: Session, ctx: MerchantContext, warehouse_id: str) -> None:
        settings = _settings_bucket(ctx.merchant)
        settings["warehouses"] = [w for w in settings.get("warehouses") or [] if w.get("id") != warehouse_id]
        _save_settings(ctx.merchant, settings)
        db.commit()

    def list_documents(self, ctx: MerchantContext) -> list[dict[str, Any]]:
        return list(_settings_bucket(ctx.merchant).get("documents") or [])

    def add_document(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        name: str,
        doc_type: str,
        reference: str | None = None,
    ) -> dict[str, Any]:
        settings = _settings_bucket(ctx.merchant)
        docs = list(settings.get("documents") or [])
        record = {
            "id": str(uuid.uuid4()),
            "name": name,
            "type": doc_type,
            "reference": reference,
            "uploaded_at": datetime.now(UTC).isoformat(),
            "uploaded_by": ctx.user.id,
        }
        docs.append(record)
        settings["documents"] = docs
        _save_settings(ctx.merchant, settings)
        db.commit()
        db.refresh(ctx.merchant)
        return record

    def delete_document(self, db: Session, ctx: MerchantContext, doc_id: str) -> None:
        settings = _settings_bucket(ctx.merchant)
        settings["documents"] = [d for d in settings.get("documents") or [] if d.get("id") != doc_id]
        _save_settings(ctx.merchant, settings)
        db.commit()

    def tax_info(self, ctx: MerchantContext) -> dict[str, Any]:
        from porterchain_api.merchant_engine.organization_sync import tax_legal_snapshot

        return tax_legal_snapshot(ctx.merchant)

    def update_tax(self, db: Session, ctx: MerchantContext, body: MerchantProfileUpdateRequest) -> dict[str, Any]:
        self._profile.update_profile(db, ctx, body)
        return self.tax_info(ctx)

    def contract_summary(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        return self._billing.contract_pricing(db, ctx)

    def _serialize_profile(self, merchant, db: Session | None = None) -> dict[str, Any]:
        from porterchain_api.merchant_engine.coverage import coverage_snapshot
        from porterchain_api.merchant_engine.profile_service import (
            profile_public_fields,
        )

        extra = profile_public_fields(merchant)
        return {
            "id": merchant.id,
            "status": merchant.status,
            "company_name": merchant.company_name,
            "legal_name": merchant.legal_name,
            "email": merchant.email,
            "phone": merchant.phone,
            "website": extra["website"],
            "industry": extra["industry"],
            "payment_terms": merchant.payment_terms,
            "billing_cycle": merchant.billing_cycle,
            "hst_number": merchant.hst_number,
            "business_number": merchant.business_number,
            "billing_address": merchant.billing_address,
            "preferred_vehicles": merchant.preferred_vehicles,
            "delivery_zones": merchant.delivery_zones,
            "identity_meta": extra["identity_meta"],
            "coverage": coverage_snapshot(merchant, db),
        }

    def _audit(self, db: Session, ctx: MerchantContext, action: str, payload: dict) -> None:
        db.add(
            MerchantAuditLog(
                merchant_id=ctx.merchant.id,
                actor_user_id=ctx.user.id,
                action=action,
                resource_type="settings",
                resource_id=ctx.merchant.id,
                payload=payload,
            )
        )
