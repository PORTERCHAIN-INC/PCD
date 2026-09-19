"""Lead milestone → Meta / LinkedIn Conversions API (CRM offline). Best-effort; never blocks convert."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

import httpx
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.crm_models import CrmLead, CrmLeadIdentity
from porterchain_api.domain.crm_states import LeadIdentityKind

logger = logging.getLogger(__name__)


def _sha256_hex(value: str | None) -> str | None:
    if not value or not str(value).strip():
        return None
    return hashlib.sha256(str(value).strip().lower().encode("utf-8")).hexdigest()


def _meta_lead_id(db: Session, lead: CrmLead) -> str | None:
    row = (
        db.query(CrmLeadIdentity)
        .filter(
            CrmLeadIdentity.lead_id == lead.id,
            CrmLeadIdentity.kind == LeadIdentityKind.META_LEAD_ID.value,
        )
        .first()
    )
    if row:
        return row.value_normalized
    fields = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
    for key in ("meta_lead_id",):
        val = fields.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _emit_linkedin(
    lead: CrmLead,
    *,
    event_name: str,
    settings: Settings,
) -> str:
    token = (settings.linkedin_capi_token or "").strip()
    conversion = (settings.linkedin_conversion_urn or "").strip()
    if not token:
        return "skipped"
    if not conversion:
        return "missing_conversion_urn"
    user_ids: list[dict[str, str]] = []
    email_h = _sha256_hex(lead.email)
    phone_h = _sha256_hex(lead.phone)
    if email_h:
        user_ids.append({"idType": "SHA256_EMAIL", "idValue": email_h})
    if phone_h:
        user_ids.append({"idType": "SHA256_PHONE", "idValue": phone_h})
    if not user_ids:
        return "no_user_ids"
    payload = {
        "conversion": conversion,
        "conversionHappenedAt": int(time.time() * 1000),
        "eventId": f"{lead.id}:{event_name}",
        "user": {"userIds": user_ids},
        "conversionValue": {"currencyCode": "CAD", "amount": "0"},
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202405",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    with httpx.Client(timeout=8.0) as client:
        resp = client.post(
            "https://api.linkedin.com/rest/conversionEvents",
            headers=headers,
            json=payload,
        )
    return "ok" if resp.is_success else f"http_{resp.status_code}"


def emit_lead_conversion_events(
    db: Session,
    lead: CrmLead,
    *,
    event_name: str = "LeadConverted",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Fire Meta + LinkedIn CRM CAPI when configured. Never raises to callers."""
    settings = settings or get_settings()
    out: dict[str, Any] = {"meta": "skipped", "linkedin": "skipped"}
    try:
        meta_token = (settings.meta_capi_access_token or "").strip()
        pixel = (settings.meta_pixel_id or "").strip()
        lead_id = _meta_lead_id(db, lead)
        if meta_token and pixel:
            user_data: dict[str, Any] = {}
            if lead_id:
                user_data["lead_id"] = lead_id
            email_h = _sha256_hex(lead.email)
            phone_h = _sha256_hex(lead.phone)
            if email_h:
                user_data["em"] = [email_h]
            if phone_h:
                user_data["ph"] = [phone_h]
            payload = {
                "data": [
                    {
                        "event_name": event_name,
                        "event_time": int(time.time()),
                        "action_source": "system_generated",
                        "user_data": user_data,
                        "custom_data": {
                            "lead_event_source": "crm",
                            "lead_event_id": lead.id,
                            "currency": "CAD",
                        },
                    }
                ],
                "access_token": meta_token,
            }
            url = f"https://graph.facebook.com/v21.0/{pixel}/events"
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, json=payload)
            out["meta"] = "ok" if resp.is_success else f"http_{resp.status_code}"
        out["linkedin"] = _emit_linkedin(lead, event_name=event_name, settings=settings)
    except Exception:
        logger.exception("lead_capi_emit_failed", extra={"lead_id": lead.id})
        out["error"] = "emit_failed"
    return out


__all__ = ["emit_lead_conversion_events"]
