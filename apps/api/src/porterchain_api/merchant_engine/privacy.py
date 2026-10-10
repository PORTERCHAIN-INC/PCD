"""Merchant DSAR export / delete request / erasure — owned by merchant_engine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_models import Order
from porterchain_api.merchant_engine.audit_copy import serialize_audit_log, summarize_audit_action
from porterchain_api.merchant_models import (
    Merchant,
    MerchantApiKey,
    MerchantAuditLog,
    MerchantRecipient,
    MerchantUser,
    MerchantWebhook,
    SavedAddress,
)
from porterchain_shared.events.catalog import DomainEventType

MERCHANT_DELETE_RECEIVED = (
    "Deletion request received. PorterChain will confirm identity and any legal holds "
    "within 30 days. Keep this reference."
)


def merchant_privacy_file(merchant: Merchant) -> dict[str, Any]:
    profile = merchant.profile if isinstance(merchant.profile, dict) else {}
    privacy = dict(profile.get("privacy") or {}) if isinstance(profile.get("privacy"), dict) else {}
    erased_at = privacy.get("erased_at")
    requested_at = privacy.get("delete_requested_at")
    reference = privacy.get("delete_reference")
    if erased_at:
        status = "erased"
        message = (
            "Contact details for this company were removed. Order numbers and invoice amounts are kept."
        )
    elif requested_at:
        status = "pending"
        message = (
            f"Deletion request is under review. Reference {reference}. "
            "PorterChain will confirm identity and legal holds within 30 days."
        )
    else:
        status = "none"
        message = (
            "Download a copy of this company file, or ask PorterChain to delete it. "
            "Live orders and unpaid invoices are not wiped automatically."
        )
    return {
        "status": status,
        "delete_requested_at": requested_at,
        "delete_reference": reference,
        "delete_reason": privacy.get("delete_reason"),
        "erased_at": erased_at,
        "erased_by": privacy.get("erased_by"),
        "sla_days": 30 if status == "pending" else None,
        "message": message,
    }


class MerchantPrivacyService:
    def export_merchant(self, db: Session, merchant: Merchant, *, actor_user_id: str) -> dict[str, Any]:
        users = (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == merchant.id)
            .order_by(MerchantUser.created_at.asc())
            .all()
        )
        orders = (
            db.query(Order)
            .filter(Order.merchant_id == merchant.id)
            .order_by(Order.created_at.desc())
            .limit(500)
            .all()
        )
        audit = (
            db.query(MerchantAuditLog)
            .filter(MerchantAuditLog.merchant_id == merchant.id)
            .order_by(MerchantAuditLog.created_at.desc())
            .limit(200)
            .all()
        )
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "subject_type": "merchant",
            "merchant_id": merchant.id,
            "requested_by": actor_user_id,
            "profile": {
                "company_name": merchant.company_name,
                "legal_name": merchant.legal_name,
                "email": merchant.email,
                "phone": merchant.phone,
                "billing_address": merchant.billing_address,
                "status": merchant.status,
                "created_at": merchant.created_at.isoformat() if merchant.created_at else None,
            },
            "team": [
                {
                    "user_id": u.id,
                    "email": u.email,
                    "role": u.role,
                    "clerk_user_id": u.clerk_user_id,
                    "is_active": u.is_active,
                }
                for u in users
            ],
            "orders_summary": [
                {
                    "order_id": o.id,
                    "order_number": o.order_number,
                    "tracking_number": o.tracking_number,
                    "state": o.state,
                    "is_sandbox": bool(getattr(o, "is_sandbox", False)),
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in orders
            ],
            "orders_env_counts": {
                "sandbox": sum(1 for o in orders if bool(getattr(o, "is_sandbox", False))),
                "live": sum(1 for o in orders if not bool(getattr(o, "is_sandbox", False))),
            },
            "audit_logs": [
                {
                    "action": row.action,
                    "summary": summarize_audit_action(row.action),
                    "resource_type": row.resource_type,
                    "resource_id": row.resource_id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in audit
            ],
            "documents": _document_index(db, merchant.id),
            "retention_note": (
                "Billing and live shipment records may be retained per legal obligation after "
                "erasure request. Sandbox/test orders are labeled is_sandbox=true in this export "
                "and do not count as live capacity."
            ),
        }

    def privacy_status(self, db: Session, merchant: Merchant, *, log_limit: int = 40) -> dict[str, Any]:
        file = merchant_privacy_file(merchant)
        logs = (
            db.query(MerchantAuditLog)
            .filter(MerchantAuditLog.merchant_id == merchant.id)
            .order_by(MerchantAuditLog.created_at.desc())
            .limit(log_limit)
            .all()
        )
        file["recent_logs"] = [serialize_audit_log(row) for row in logs]
        return file

    def request_merchant_deletion(
        self,
        db: Session,
        merchant: Merchant,
        *,
        actor_user_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        current = merchant_privacy_file(merchant)
        if current["status"] == "erased":
            return {
                "reference": current.get("delete_reference") or "",
                "status": "already_erased",
                "sla_days": 0,
                "message": "This company file has already been erased.",
            }
        if current["status"] == "pending" and current.get("delete_reference"):
            return {
                "reference": current["delete_reference"],
                "status": "received",
                "sla_days": 30,
                "message": MERCHANT_DELETE_RECEIVED,
            }

        reference = f"DSR-{uuid.uuid4().hex[:12].upper()}"
        reason_text = (reason or "").strip() or "merchant_portal_request"
        payload = {
            "reference": reference,
            "reason": reason_text,
            "requested_by": actor_user_id,
        }
        profile = dict(merchant.profile or {})
        privacy = dict(profile.get("privacy") or {}) if isinstance(profile.get("privacy"), dict) else {}
        privacy["delete_requested_at"] = datetime.now(UTC).isoformat()
        privacy["delete_reference"] = reference
        privacy["delete_reason"] = reason_text
        profile["privacy"] = privacy
        merchant.profile = profile
        db.add(
            MerchantAuditLog(
                merchant_id=merchant.id,
                actor_user_id=actor_user_id,
                action="privacy.delete_requested",
                resource_type="merchant",
                resource_id=merchant.id,
                payload=payload,
            )
        )
        emit_event(
            db,
            event_type=DomainEventType.PRIVACY_DELETE_REQUESTED,
            aggregate_type="merchant",
            aggregate_id=merchant.id,
            actor_type="merchant_user",
            actor_id=actor_user_id,
            payload=payload,
        )
        db.commit()
        db.refresh(merchant)
        return {
            "reference": reference,
            "status": "received",
            "sla_days": 30,
            "message": MERCHANT_DELETE_RECEIVED,
        }

    def execute_merchant_erasure(
        self,
        db: Session,
        merchant: Merchant,
        *,
        actor_user_id: str,
    ) -> dict[str, Any]:
        """Ops DSR execute after close. Keep order numbers and financial aggregates."""
        from porterchain_api.domain.merchant_states import MerchantStatus
        from porterchain_api.merchant_engine.offboard import (
            operational_order_count,
            outstanding_cents,
        )

        profile = dict(merchant.profile or {})
        privacy = dict(profile.get("privacy") or {})
        if privacy.get("erased_at"):
            return {
                "merchant_id": merchant.id,
                "status": "already_erased",
                "erased_at": privacy.get("erased_at"),
            }
        if merchant.status != MerchantStatus.CLOSED.value:
            raise ValueError("merchant_not_closed")
        if operational_order_count(db, merchant.id) > 0:
            raise ValueError("close_blocked_live_orders")
        if outstanding_cents(db, merchant) > 0:
            raise ValueError("close_blocked_outstanding_ar")

        token = merchant.id.replace("-", "")[:12]
        merchant.email = f"erased-{token}@privacy.invalid"
        merchant.phone = None
        merchant.legal_name = None
        merchant.company_name = f"Closed merchant {token}"
        merchant.billing_address = {}
        profile.pop("website", None)
        settings = dict(profile.get("settings") or {})
        settings["billing_contacts"] = []
        branding = dict(settings.get("branding") or {})
        branding["logo_url"] = None
        settings["branding"] = branding
        profile["settings"] = settings
        privacy["erased_at"] = datetime.now(UTC).isoformat()
        privacy["erased_by"] = actor_user_id
        profile["privacy"] = privacy
        merchant.profile = profile

        for user in db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant.id).all():
            user.email = f"erased-{user.id[:8]}@privacy.invalid"
            user.is_active = False
            if user.clerk_user_id and not str(user.clerk_user_id).startswith("erased:"):
                user.clerk_user_id = f"erased:{user.id}"

        for recipient in db.query(MerchantRecipient).filter(MerchantRecipient.merchant_id == merchant.id).all():
            recipient.name = "Redacted"
            recipient.email = None
            recipient.phone = None
            recipient.company = None
            recipient.default_address = None

        for address in db.query(SavedAddress).filter(SavedAddress.merchant_id == merchant.id).all():
            address.formatted = "Redacted"
            address.place_id = None

        for key in db.query(MerchantApiKey).filter(MerchantApiKey.merchant_id == merchant.id).all():
            key.is_active = False
        for hook in db.query(MerchantWebhook).filter(MerchantWebhook.merchant_id == merchant.id).all():
            hook.is_active = False

        from porterchain_api.merchant_engine.account_ops.documents import purge_documents

        documents_purged = purge_documents(db, merchant.id)

        db.add(
            MerchantAuditLog(
                merchant_id=merchant.id,
                actor_user_id=actor_user_id,
                action="privacy.erasure_completed",
                resource_type="merchant",
                resource_id=merchant.id,
                payload={
                    "kept": ["orders", "invoices", "amounts"],
                    "documents_purged": documents_purged,
                    "note": "Sandbox orders remain labeled is_sandbox on kept shipment rows",
                },
            )
        )
        from porterchain_api.merchant_engine.organization_sync import project_merchant_company

        project_merchant_company(db, merchant)
        db.commit()
        db.refresh(merchant)
        return {
            "merchant_id": merchant.id,
            "status": "erased",
            "erased_at": privacy["erased_at"],
            "message": "Contact details removed. Order numbers and invoice amounts are retained.",
        }

    def status_for_id(self, db: Session, merchant_id: str) -> dict[str, Any]:
        from porterchain_api.merchant_engine.lookups import get_merchant

        merchant = get_merchant(db, merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")
        return self.privacy_status(db, merchant)

    def execute_for_id(self, db: Session, merchant_id: str, *, actor_user_id: str) -> dict[str, Any]:
        from porterchain_api.merchant_engine.lookups import get_merchant

        merchant = get_merchant(db, merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")
        return self.execute_merchant_erasure(db, merchant, actor_user_id=actor_user_id)


def _document_index(db: Session, merchant_id: str) -> list[dict[str, Any]]:
    """Vault metadata for the DSAR export (files themselves are sent on request)."""
    from porterchain_api.merchant_engine.account_ops.documents import list_documents

    return list_documents(db, merchant_id)
