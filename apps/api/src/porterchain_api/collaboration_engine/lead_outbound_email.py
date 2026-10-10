"""Enqueue lawful lead template emails (staff outbound)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmLead


def enqueue_lead_template_email(
    db: Session,
    crm: Any,
    *,
    lead: CrmLead,
    template_key: str,
    actor_id: str,
    website_url: str,
    jwt_secret: str,
) -> dict[str, Any]:
    email = (lead.email or "").strip()
    if not email or "@" not in email:
        raise ValueError("email_required")
    consent = lead.consent if isinstance(lead.consent, dict) else {}
    if not consent.get("marketing"):
        raise ValueError("marketing_consent_required")
    from porterchain_api.collaboration_engine.lead_suppression import is_suppressed

    if is_suppressed(db, email=email, phone=lead.phone):
        raise ValueError("suppressed")
    allowed = {
        "lead_outbound_followup",
        "lead_outbound_quote_invite",
        "lead_nurture_intro",
        "lead_nurture_d1",
        "lead_nurture_d7",
    }
    template = (template_key or "").strip()
    if template not in allowed:
        raise ValueError("invalid_template")
    base = (website_url or "https://porterchain.com").rstrip("/")
    try:
        from porterchain_api.collaboration_engine.lead_consent import (
            make_unsubscribe_token,
        )
        from porterchain_api.notification_engine.engine import get_notification_engine

        unsub = ""
        secret = (jwt_secret or "").strip()
        if secret:
            token = make_unsubscribe_token(lead_id=lead.id, secret=secret)
            unsub = f"{base}/unsubscribe?token={token}"
        get_notification_engine().dispatch(
            db,
            event_type="lead.outbound",
            template_key=template,
            channel="email",
            recipient_type="lead",
            recipient_id=lead.id,
            recipient_address=email,
            context={
                "company_name": lead.company_name,
                "contact_name": lead.primary_contact_name or "",
                "quote_url": f"{base}/sign-up?intent=quote&utm_source=outbound&utm_medium=email",
                "unsubscribe_url": unsub,
                "lead_id": lead.id,
            },
            correlation_id=lead.id,
            category="crm",
        )
    except Exception as exc:
        raise RuntimeError("enqueue_failed") from exc
    crm.log_activity(
        db,
        entity_type="lead",
        entity_id=lead.id,
        activity_type="email",
        subject=f"Sent template {template}",
        actor_id=actor_id,
        metadata={"template_key": template},
    )
    return {"ok": True, "template_key": template, "recipient": email}


__all__ = ["enqueue_lead_template_email"]
