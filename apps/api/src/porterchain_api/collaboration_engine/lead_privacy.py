"""PIPEDA/DSAR export + soft erase for CrmLead (distinct from hard delete_lead)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import (
    CrmConversation,
    CrmConversationMessage,
    CrmLead,
    CrmLeadIdentity,
)
from porterchain_api.domain.crm_states import LeadStatus

logger = logging.getLogger(__name__)

PRIVACY_ERASED_TAG = "privacy_erased"
PRIVACY_DELETE_REQUESTED_TAG = "privacy_delete_requested"

# Article 30 / PIPEDA-style processing inventory for CrmLead (Ontario primary).
# Not a multi-region residency product — documents what we process today.
LEAD_ROPA: list[dict[str, Any]] = [
    {
        "activity": "lead_ingest",
        "purpose": "Receive and respond to capacity / partner inquiries",
        "legal_bases": ["consent", "contract", "legitimate_interest"],
        "categories": ["identity", "contact", "company", "consent", "attribution"],
        "systems": ["PorterChain API", "admin Lead Workspace", "worker nurture"],
        "recipients": ["PorterChain growth staff"],
        "retention": "Inactive unconverted soft-archive ~24 months; converted commercial ~7 years",
        "residency": "Canada (Ontario primary); no EU multi-region split in this release",
    },
    {
        "activity": "lead_nurture",
        "purpose": "Marketing follow-up when consent holds (D0/D1/D7 email; D3 staff task)",
        "legal_bases": ["consent"],
        "categories": ["contact", "consent"],
        "systems": ["email queue", "CrmSuppression DNC"],
        "recipients": ["ESP / mail transport"],
        "retention": "Stops on unsubscribe or soft-archive; suppression hashes retained",
        "residency": "Canada (Ontario primary)",
    },
    {
        "activity": "lead_ads_capi",
        "purpose": "Optional conversion attribution to Meta / LinkedIn when configured",
        "legal_bases": ["consent", "legitimate_interest"],
        "categories": ["hashed contact", "event metadata"],
        "systems": ["lead_capi"],
        "recipients": ["Meta / LinkedIn (when enabled)"],
        "retention": "Per ad-platform retention; PorterChain keeps CAPI result on activity",
        "residency": "Canada primary; ad platforms may process outside CA",
    },
    {
        "activity": "lead_privacy_ops",
        "purpose": "DSAR export, delete request, soft erase, suppression",
        "legal_bases": ["legal_obligation", "consent"],
        "categories": ["identity", "contact", "conversation bodies"],
        "systems": ["LeadPrivacyService", "admin_audit"],
        "recipients": ["PorterChain compliance / super_admin"],
        "retention": "Audit retain; erased PII replaced with tokens",
        "residency": "Canada (Ontario primary)",
    },
]


def lead_ropa_inventory() -> dict[str, Any]:
    return {
        "controller": "PorterChain",
        "contact": "privacy@porterchain.com",
        "primary_residency": "CA-ON",
        "multi_region": False,
        "activities": list(LEAD_ROPA),
        "notes": (
            "Record of processing for CrmLead. Cookie CMP consent is separate from lead.consent. "
            "Support tickets and claims are out of scope for Lead 360."
        ),
    }


class LeadPrivacyError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _audit_privacy(
    db: Session,
    *,
    action: str,
    lead_id: str,
    actor_user_id: str,
    payload: dict[str, Any] | None = None,
) -> None:
    try:
        from porterchain_api.crm_models import CrmActivity
        from porterchain_api.platform.admin_audit import log_admin_audit

        log_admin_audit(
            db,
            None,
            action=action,
            resource_type="crm_lead",
            resource_id=lead_id,
            payload={"actor_user_id": actor_user_id, **(payload or {})},
        )
        db.add(
            CrmActivity(
                entity_type="lead",
                entity_id=lead_id,
                activity_type="note",
                subject=action,
                body=None,
                metadata_json={"privacy": True, **(payload or {})},
                actor_id=actor_user_id,
            )
        )
    except Exception:
        logger.exception("lead_privacy_audit_failed action=%s lead=%s", action, lead_id)


class LeadPrivacyService:
    def export_lead(
        self, db: Session, lead: CrmLead, *, actor_user_id: str | None = None
    ) -> dict[str, Any]:
        identities = (
            db.query(CrmLeadIdentity)
            .filter(CrmLeadIdentity.lead_id == lead.id)
            .order_by(CrmLeadIdentity.created_at.asc())
            .all()
        )
        conversations = (
            db.query(CrmConversation)
            .filter(CrmConversation.lead_id == lead.id)
            .order_by(CrmConversation.created_at.desc())
            .limit(50)
            .all()
        )
        message_counts: dict[str, int] = {}
        if conversations:
            ids = [c.id for c in conversations]
            rows = (
                db.query(CrmConversationMessage.conversation_id)
                .filter(CrmConversationMessage.conversation_id.in_(ids))
                .all()
            )
            for (cid,) in rows:
                message_counts[str(cid)] = message_counts.get(str(cid), 0) + 1

        custom = dict(lead.custom_fields or {})
        for secret_key in ("ingest_secret", "webhook_secret", "api_key", "token"):
            custom.pop(secret_key, None)

        out = {
            "exported_at": datetime.now(UTC).isoformat(),
            "lead": {
                "id": lead.id,
                "company_name": lead.company_name,
                "primary_contact_name": lead.primary_contact_name,
                "email": lead.email,
                "phone": lead.phone,
                "status": lead.status,
                "priority": lead.priority,
                "source": lead.source,
                "channel": lead.channel,
                "intent_type": lead.intent_type,
                "consent": dict(lead.consent or {}),
                "tags": list(lead.tags or []),
                "custom_fields": custom,
                "visitor_session_id": lead.visitor_session_id,
                "booking_draft_id": lead.booking_draft_id,
                "quote_id": lead.quote_id,
                "company_id": lead.company_id,
                "deal_id": lead.deal_id,
                "contact_id": lead.contact_id,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
                "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
            },
            "identities": [
                {
                    "id": i.id,
                    "kind": i.kind,
                    "value_normalized": i.value_normalized,
                    "raw_value": i.raw_value,
                }
                for i in identities
            ],
            "conversations": [
                {
                    "id": c.id,
                    "channel": c.channel,
                    "message_count": message_counts.get(c.id, 0),
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in conversations
            ],
            "ropa": lead_ropa_inventory(),
        }
        if actor_user_id:
            _audit_privacy(
                db,
                action="crm.lead.privacy_export",
                lead_id=lead.id,
                actor_user_id=actor_user_id,
            )
        return out

    def request_deletion(
        self,
        db: Session,
        lead: CrmLead,
        *,
        actor_user_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        tags = list(lead.tags or [])
        if PRIVACY_DELETE_REQUESTED_TAG not in tags:
            tags.append(PRIVACY_DELETE_REQUESTED_TAG)
        lead.tags = tags
        fields = dict(lead.custom_fields or {})
        fields["privacy_delete_requested_at"] = datetime.now(UTC).isoformat()
        fields["privacy_delete_requested_by"] = actor_user_id
        if reason:
            fields["privacy_delete_reason"] = reason[:500]
        lead.custom_fields = fields
        db.flush()
        _audit_privacy(
            db,
            action="crm.lead.privacy_delete_request",
            lead_id=lead.id,
            actor_user_id=actor_user_id,
            payload={"reason": (reason or "")[:200]},
        )
        return {
            "lead_id": lead.id,
            "status": "delete_requested",
            "reference": f"dsr-{uuid.uuid4().hex[:12]}",
        }

    def erase_lead(self, db: Session, lead: CrmLead, *, actor_user_id: str) -> dict[str, Any]:
        if lead.status == LeadStatus.CONVERTED.value and (
            lead.company_id
            or (lead.custom_fields or {}).get("linked_customer_id")
            or (lead.custom_fields or {}).get("linked_driver_id")
            or (lead.custom_fields or {}).get("customer_id")
            or (lead.custom_fields or {}).get("driver_id")
        ):
            raise LeadPrivacyError("lead_converted_linked")

        prior_email = lead.email
        prior_phone = lead.phone
        from porterchain_api.collaboration_engine.lead_suppression import (
            upsert_suppression,
        )

        upsert_suppression(
            db,
            email=prior_email,
            phone=prior_phone,
            source="privacy_erase",
            lead_id=lead.id,
        )

        token = uuid.uuid4().hex[:10]
        lead.email = f"erased-{token}@privacy.invalid"
        lead.phone = None
        lead.primary_contact_name = "Erased"
        lead.company_name = f"Erased-{token}"
        lead.internal_notes = None
        lead.consent = {}
        lead.address = {}
        custom = dict(lead.custom_fields or {})
        for key in ("message", "guide_notes", "phone_full", "body", "notes"):
            custom.pop(key, None)
        custom["privacy_erased_at"] = datetime.now(UTC).isoformat()
        custom["privacy_erased_by"] = actor_user_id
        lead.custom_fields = custom
        tags = [t for t in (lead.tags or []) if t != PRIVACY_DELETE_REQUESTED_TAG]
        if PRIVACY_ERASED_TAG not in tags:
            tags.append(PRIVACY_ERASED_TAG)
        lead.tags = tags

        identities = db.query(CrmLeadIdentity).filter(CrmLeadIdentity.lead_id == lead.id).all()
        for identity in identities:
            iid = uuid.uuid4().hex[:12]
            identity.raw_value = f"erased-{iid}"
            identity.value_normalized = f"erased-{iid}"

        conversations = db.query(CrmConversation).filter(CrmConversation.lead_id == lead.id).all()
        if conversations:
            cids = [c.id for c in conversations]
            messages = (
                db.query(CrmConversationMessage)
                .filter(CrmConversationMessage.conversation_id.in_(cids))
                .all()
            )
            for msg in messages:
                msg.body = "[redacted]"
                msg.metadata_json = {}

        db.flush()
        _audit_privacy(
            db,
            action="crm.lead.privacy_erase",
            lead_id=lead.id,
            actor_user_id=actor_user_id,
        )
        logger.info("lead_privacy_erased lead=%s actor=%s", lead.id, actor_user_id)
        return {"lead_id": lead.id, "status": "erased"}


__all__ = [
    "LEAD_ROPA",
    "PRIVACY_DELETE_REQUESTED_TAG",
    "PRIVACY_ERASED_TAG",
    "LeadPrivacyError",
    "LeadPrivacyService",
    "lead_ropa_inventory",
]
