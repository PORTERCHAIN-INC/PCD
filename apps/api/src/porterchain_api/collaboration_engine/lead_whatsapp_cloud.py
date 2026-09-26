"""Meta WhatsApp Cloud API outbound (template messages).

Inbound webhooks already land in lead_channel_adapters. This module is the
missing send path — no-ops with clear status when secrets are unset.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

_GRAPH = "https://graph.facebook.com/v21.0"


def whatsapp_cloud_configured() -> bool:
    from porterchain_api.config import get_settings

    s = get_settings()
    token = (getattr(s, "meta_wa_access_token", None) or "").strip()
    phone_id = (getattr(s, "meta_wa_phone_number_id", None) or "").strip()
    return bool(token and phone_id)


def send_whatsapp_template(
    *,
    phone: str,
    template_name: str,
    company_name: str = "",
    contact_name: str = "",
    lead_id: str = "",
    language_code: str = "en",
) -> dict[str, Any]:
    """Send an approved Meta template. Returns status dict (never raises for config gaps)."""
    from porterchain_api.config import get_settings

    s = get_settings()
    token = (getattr(s, "meta_wa_access_token", None) or "").strip()
    phone_id = (getattr(s, "meta_wa_phone_number_id", None) or "").strip()
    if not token or not phone_id:
        return {"status": "skipped", "reason": "whatsapp_cloud_not_configured"}

    to = "".join(c for c in phone if c.isdigit())
    if not to:
        return {"status": "blocked", "reason": "invalid_phone"}

    # Map PCD template keys → Meta template names (env override).
    name_map_raw = (getattr(s, "meta_wa_template_map_json", None) or "").strip()
    meta_name = template_name
    if name_map_raw:
        import json

        try:
            mapping = json.loads(name_map_raw)
            if isinstance(mapping, dict) and template_name in mapping:
                meta_name = str(mapping[template_name])
        except json.JSONDecodeError:
            logger.warning("meta_wa_template_map_json_invalid")

    body = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": meta_name,
            "language": {"code": language_code},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": (contact_name or company_name or "there")[:60]},
                        {"type": "text", "text": (company_name or "your business")[:60]},
                    ],
                }
            ],
        },
    }
    url = f"{_GRAPH}/{phone_id}/messages"
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
            )
        if resp.status_code >= 400:
            logger.warning(
                "whatsapp_cloud_send_failed lead=%s status=%s body=%s",
                lead_id,
                resp.status_code,
                resp.text[:300],
            )
            return {
                "status": "error",
                "reason": "meta_api_error",
                "http_status": resp.status_code,
                "detail": resp.text[:300],
            }
        data = resp.json()
        msg_id = None
        try:
            msg_id = (data.get("messages") or [{}])[0].get("id")
        except (IndexError, AttributeError, TypeError):
            msg_id = None
        return {
            "status": "sent",
            "channel": "whatsapp",
            "template_key": template_name,
            "meta_template": meta_name,
            "message_id": msg_id,
            "to": to,
        }
    except Exception as exc:
        logger.exception("whatsapp_cloud_send_exception lead=%s", lead_id)
        return {"status": "error", "reason": "request_failed", "detail": str(exc)[:200]}


def send_whatsapp_text(
    *,
    phone: str,
    body: str,
    lead_id: str = "",
) -> dict[str, Any]:
    """Free-form text — only valid inside Meta 24h care window."""
    from porterchain_api.config import get_settings

    s = get_settings()
    token = (getattr(s, "meta_wa_access_token", None) or "").strip()
    phone_id = (getattr(s, "meta_wa_phone_number_id", None) or "").strip()
    if not token or not phone_id:
        return {"status": "skipped", "reason": "whatsapp_cloud_not_configured"}

    to = "".join(c for c in phone if c.isdigit())
    text = (body or "").strip()[:3500]
    if not to or not text:
        return {"status": "blocked", "reason": "invalid_phone_or_body"}

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    url = f"{_GRAPH}/{phone_id}/messages"
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            )
        if resp.status_code >= 400:
            logger.warning(
                "whatsapp_text_failed lead=%s status=%s body=%s",
                lead_id,
                resp.status_code,
                resp.text[:300],
            )
            return {
                "status": "error",
                "reason": "meta_api_error",
                "http_status": resp.status_code,
                "detail": resp.text[:300],
            }
        data = resp.json()
        msg_id = None
        try:
            msg_id = (data.get("messages") or [{}])[0].get("id")
        except (IndexError, AttributeError, TypeError):
            msg_id = None
        return {
            "status": "sent",
            "channel": "whatsapp",
            "kind": "text",
            "message_id": msg_id,
            "to": to,
        }
    except Exception as exc:
        logger.exception("whatsapp_text_exception lead=%s", lead_id)
        return {"status": "error", "reason": "request_failed", "detail": str(exc)[:200]}


def staff_whatsapp_deeplink(phone: str, *, company_name: str = "") -> str:
    digits = "".join(c for c in phone if c.isdigit())
    msg = (
        f"Hi — PorterChain here. We help {company_name or 'your business'} "
        "with vehicle + driver capacity."
    )
    return f"https://wa.me/{digits}?text={quote(msg)}"


__all__ = [
    "send_whatsapp_template",
    "send_whatsapp_text",
    "staff_whatsapp_deeplink",
    "whatsapp_cloud_configured",
]
