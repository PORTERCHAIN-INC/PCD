"""Merchant settings — profile extensions in merchant.profile (masterrule §3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import MerchantAuditLog
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
        return {
            "profile": self._serialize_profile(merchant),
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
        }

    def update_notifications(self, db: Session, ctx: MerchantContext, body: dict[str, Any]) -> dict[str, Any]:
        settings = _settings_bucket(ctx.merchant)
        current = dict(settings.get("notifications") or DEFAULT_NOTIFICATIONS)
        current.update(body)
        settings["notifications"] = current
        _save_settings(ctx.merchant, settings)
        self._audit(db, ctx, "settings.notifications", current)
        db.commit()
        db.refresh(ctx.merchant)
        return current

    def update_branding(self, db: Session, ctx: MerchantContext, body: dict[str, Any]) -> dict[str, Any]:
        settings = _settings_bucket(ctx.merchant)
        current = dict(settings.get("branding") or DEFAULT_BRANDING)
        current.update(body)
        settings["branding"] = current
        _save_settings(ctx.merchant, settings)
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
        contact_id: str | None = None,
    ) -> dict[str, Any]:
        settings = _settings_bucket(ctx.merchant)
        contacts = list(settings.get("billing_contacts") or [])
        record = {
            "id": contact_id or str(uuid.uuid4()),
            "name": name,
            "email": email,
            "phone": phone,
            "role": role or "billing",
            "is_primary": len(contacts) == 0,
        }
        if contact_id:
            contacts = [record if c.get("id") == contact_id else c for c in contacts]
            if not any(c.get("id") == contact_id for c in contacts):
                contacts.append(record)
        else:
            contacts.append(record)
        settings["billing_contacts"] = contacts
        _save_settings(ctx.merchant, settings)
        db.commit()
        db.refresh(ctx.merchant)
        return record

    def delete_billing_contact(self, db: Session, ctx: MerchantContext, contact_id: str) -> None:
        settings = _settings_bucket(ctx.merchant)
        contacts = [c for c in settings.get("billing_contacts") or [] if c.get("id") != contact_id]
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
        db.commit()
        db.refresh(ctx.merchant)
        return record

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
        settings = _settings_bucket(ctx.merchant)
        tax = dict(settings.get("tax") or {})
        merchant = ctx.merchant
        return {
            "hst_number": merchant.hst_number,
            "business_number": merchant.business_number,
            "legal_name": merchant.legal_name,
            "tax_exempt": bool(tax.get("tax_exempt", False)),
            "tax_region": tax.get("tax_region") or "ON",
            "billing_address": merchant.billing_address,
        }

    def update_tax(self, db: Session, ctx: MerchantContext, body: MerchantProfileUpdateRequest) -> dict[str, Any]:
        merchant = self._profile.update_profile(db, ctx, body)
        settings = _settings_bucket(merchant)
        tax = dict(settings.get("tax") or {})
        for key in ("tax_exempt", "tax_region"):
            if hasattr(body, key) and getattr(body, key) is not None:
                tax[key] = getattr(body, key)
        settings["tax"] = tax
        _save_settings(merchant, settings)
        db.commit()
        db.refresh(merchant)
        return self.tax_info(ctx)

    def contract_summary(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        return self._billing.contract_pricing(db, ctx)

    def _serialize_profile(self, merchant) -> dict[str, Any]:
        return {
            "id": merchant.id,
            "status": merchant.status,
            "company_name": merchant.company_name,
            "legal_name": merchant.legal_name,
            "email": merchant.email,
            "phone": merchant.phone,
            "payment_terms": merchant.payment_terms,
            "billing_cycle": merchant.billing_cycle,
            "hst_number": merchant.hst_number,
            "business_number": merchant.business_number,
            "billing_address": merchant.billing_address,
            "preferred_vehicles": merchant.preferred_vehicles,
            "delivery_zones": merchant.delivery_zones,
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
