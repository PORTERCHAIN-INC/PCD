"""Self-serve sign-ups → CRM leads (Shopify install, merchant portal, driver).

Linked to existing leads by the ingest bus dedup (email / phone). Never sends
anything to the person (``skip_outreach``) — this only makes the sign-up
visible to sales in the unified inbox. Best-effort: failures are logged and
never break the sign-up itself.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.domain.crm_states import (
    LeadIntentType,
    LeadPriority,
    LeadSourceChannel,
    LeadStatus,
)

logger = logging.getLogger(__name__)

_KINDS: dict[str, dict[str, str]] = {
    "shopify_install": {
        "channel": LeadSourceChannel.APP_INSTALL.value,
        "source": "shopify_app_install",
        "intent": LeadIntentType.MERCHANT.value,
        "priority": LeadPriority.HIGH.value,
        "label": "Installed the Shopify app",
    },
    "merchant_signup": {
        "channel": LeadSourceChannel.MERCHANT_SIGNUP.value,
        "source": "merchant_portal_signup",
        "intent": LeadIntentType.MERCHANT.value,
        "priority": LeadPriority.HIGH.value,
        "label": "Signed up on the merchant portal",
    },
    "driver_signup": {
        "channel": LeadSourceChannel.DRIVER_SIGNUP.value,
        "source": "driver_signup",
        "intent": LeadIntentType.DRIVER_PARTNER.value,
        "priority": LeadPriority.MEDIUM.value,
        "label": "Signed up as a driver",
    },
}


def record_signup_lead(
    db: Session,
    *,
    kind: str,
    external_id: str,
    email: str | None,
    company_name: str | None = None,
    contact_name: str | None = None,
    phone: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str | None:
    """Create or link a lead for a sign-up. Returns the lead id (or None)."""
    spec = _KINDS.get(kind)
    if spec is None:
        raise ValueError(f"unknown_signup_kind:{kind}")
    if not (email or phone):
        return None
    from porterchain_api.collaboration_engine.lead_ingest_service import (
        CanonicalLeadEvent,
        LeadIngestService,
    )

    name = (company_name or contact_name or (email or "").split("@", 1)[0] or kind).strip()
    try:
        result = LeadIngestService().ingest(
            db,
            CanonicalLeadEvent(
                channel=spec["channel"],
                source=spec["source"],
                provider=f"signup_{kind}",
                external_event_id=f"{kind}:{external_id}"[:255],
                company_name=name[:255],
                primary_contact_name=(contact_name or None),
                email=email,
                phone=phone,
                intent_type=spec["intent"],
                priority=spec["priority"],
                status=LeadStatus.NEW.value,
                tags=[kind, "self_serve"],
                custom_fields={k: v for k, v in (extra or {}).items() if v not in (None, "")},
                seed_conversation=False,
                skip_outreach=True,
            ),
        )
    except Exception:
        db.rollback()
        logger.exception("signup_lead_failed kind=%s ref=%s", kind, external_id)
        return None
    lead = result.lead
    from porterchain_api.collaboration_engine.crm_activity import CrmActivityMixin

    try:
        CrmActivityMixin().log_activity(
            db,
            entity_type="lead",
            entity_id=lead.id,
            activity_type="system",
            subject=spec["label"],
            metadata={"kind": kind, "ref": external_id, **(extra or {})},
        )
    except Exception:  # noqa: BLE001
        db.rollback()
    return lead.id


__all__ = ["record_signup_lead"]


def record_shopify_install_lead(db: Session, *, shop_domain: str, merchant_id: str | None) -> str | None:
    """Shopify app install → CRM lead, using the linked merchant's contact details."""
    from porterchain_api.merchant_models import Merchant

    merchant = db.get(Merchant, merchant_id) if merchant_id else None
    return record_signup_lead(
        db,
        kind="shopify_install",
        external_id=shop_domain,
        email=getattr(merchant, "email", None),
        company_name=getattr(merchant, "company_name", None) or shop_domain,
        phone=getattr(merchant, "phone", None),
        extra={"shop_domain": shop_domain, "merchant_id": merchant_id},
    )
