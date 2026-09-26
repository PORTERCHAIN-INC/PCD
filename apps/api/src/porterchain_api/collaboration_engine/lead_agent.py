"""Zero-human lead agent — NBA → email (ready) / WhatsApp Cloud (when configured)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.lead_nba import (
    _WELCOME_TAG,
    lead_next_best_action,
)
from porterchain_api.crm_models import CrmLead
from porterchain_api.domain.crm_states import LeadStatus

logger = logging.getLogger(__name__)

_INTRO_TEMPLATE = "lead_nurture_intro"

_AGENT_CF = "lead_agent"


def _agent_enabled() -> bool:
    from porterchain_api.config import get_settings

    return bool(getattr(get_settings(), "lead_agent_auto_send", True))


def _cf(lead: CrmLead) -> dict[str, Any]:
    bag = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
    agent = bag.get(_AGENT_CF)
    return dict(agent) if isinstance(agent, dict) else {}


def _set_cf(lead: CrmLead, patch: dict[str, Any]) -> None:
    bag = dict(lead.custom_fields) if isinstance(lead.custom_fields, dict) else {}
    cur = dict(bag.get(_AGENT_CF) or {}) if isinstance(bag.get(_AGENT_CF), dict) else {}
    cur.update(patch)
    bag[_AGENT_CF] = cur
    lead.custom_fields = bag


def ensure_inbound_sla(db: Session, lead: CrmLead) -> bool:
    """Set first-response SLA when missing on non-vendor NEW leads."""
    if lead.source == "vendor_import":
        return False
    if lead.status != LeadStatus.NEW.value:
        return False
    if lead.sla_first_response_due_at:
        return False
    from datetime import timedelta

    from porterchain_api.collaboration_engine.lead_ops import sla_minutes_for_channel

    mins = sla_minutes_for_channel(lead.channel)
    lead.sla_first_response_due_at = datetime.now(UTC) + timedelta(minutes=mins)
    return True


def _mark_welcomed(lead: CrmLead, *, channel: str, detail: dict[str, Any]) -> None:
    tags = list(lead.tags or [])
    if _WELCOME_TAG not in tags:
        tags.append(_WELCOME_TAG)
        lead.tags = tags
    lead.last_touch_at = datetime.now(UTC)
    # First response satisfied
    if lead.status == LeadStatus.NEW.value:
        lead.sla_first_response_due_at = None
    _set_cf(
        lead,
        {
            "last_send_at": datetime.now(UTC).isoformat(),
            "last_channel": channel,
            "last_detail": detail,
            "status": "sent",
        },
    )


def _send_email(
    db: Session, lead: CrmLead, *, template_key: str, recipient: str, website_url: str
) -> dict[str, Any]:
    from porterchain_api.collaboration_engine.lead_consent import make_unsubscribe_token
    from porterchain_api.collaboration_engine.lead_suppression import is_suppressed
    from porterchain_api.config import get_settings
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    if is_suppressed(db, email=recipient, phone=lead.phone):
        return {"status": "blocked", "reason": "suppressed"}
    settings = get_settings()
    base = (website_url or getattr(settings, "website_url", "") or "https://porterchain.com").rstrip(
        "/"
    )
    secret = (settings.jwt_secret or settings.public_ingest_api_key or "").strip()
    unsub = ""
    if secret:
        token = make_unsubscribe_token(lead_id=lead.id, secret=secret)
        unsub = f"{base}/unsubscribe?token={token}"
    try:
        get_queue_publisher().enqueue(
            QueueName.EMAILS,
            {
                "channel": "email",
                "template": template_key,
                "recipient": recipient,
                "recipient_type": "lead",
                "recipient_id": lead.id,
                "context": {
                    "company_name": lead.company_name,
                    "contact_name": lead.primary_contact_name or "",
                    "quote_url": f"{base}/sign-up?intent=quote&utm_source=lead_agent&utm_medium=email",
                    "unsubscribe_url": unsub,
                    "lead_id": lead.id,
                },
            },
        )
    except Exception as exc:
        logger.exception("lead_agent_email_enqueue_failed lead=%s", lead.id)
        return {"status": "error", "reason": "enqueue_failed", "detail": str(exc)[:200]}
    _mark_welcomed(
        lead,
        channel="email",
        detail={"template_key": template_key, "recipient": recipient},
    )
    return {
        "status": "sent",
        "channel": "email",
        "template_key": template_key,
        "recipient": recipient,
    }


def _try_whatsapp(db: Session, lead: CrmLead, action: dict[str, Any]) -> dict[str, Any]:
    from porterchain_api.collaboration_engine.lead_whatsapp_cloud import (
        send_whatsapp_template,
        whatsapp_cloud_configured,
    )
    from porterchain_api.collaboration_engine.lead_whatsapp_gate import (
        WhatsAppSendBlocked,
        assert_whatsapp_outbound_allowed,
    )

    phone = action.get("phone") or (lead.phone or "")
    template = str(action.get("template_key") or "lead_welcome")
    if not whatsapp_cloud_configured():
        # P0: return deeplink evidence — no fake sent
        from porterchain_api.collaboration_engine.lead_nba import lead_next_best_action as _nba

        nba = _nba(db, lead)
        deeplink = next(
            (a for a in nba.get("alternatives") or [] if a.get("action") == "whatsapp_deeplink"),
            None,
        )
        return {
            "status": "skipped",
            "reason": "whatsapp_cloud_not_configured",
            "deeplink": (deeplink or {}).get("url"),
        }
    try:
        assert_whatsapp_outbound_allowed(lead)
    except WhatsAppSendBlocked as exc:
        return {"status": "blocked", "reason": exc.code}
    result = send_whatsapp_template(
        phone=phone,
        template_name=template,
        company_name=lead.company_name or "",
        contact_name=lead.primary_contact_name or "",
        lead_id=lead.id,
    )
    if result.get("status") == "sent":
        _mark_welcomed(lead, channel="whatsapp", detail=result)
    return result


def reply_inbound_whatsapp(
    db: Session,
    lead: CrmLead,
    *,
    inbound_text: str = "",
) -> dict[str, Any]:
    """Auto-reply in Meta 24h care window after inbound WA message."""
    from datetime import UTC, datetime

    from porterchain_api.collaboration_engine.lead_whatsapp_cloud import (
        send_whatsapp_text,
        whatsapp_cloud_configured,
    )
    from porterchain_api.collaboration_engine.lead_whatsapp_gate import (
        WhatsAppSendBlocked,
        assert_whatsapp_outbound_allowed,
    )

    # Inbound message opens care window
    lead.last_touch_at = datetime.now(UTC)
    db.flush()

    if not _agent_enabled():
        return {"status": "skipped", "reason": "auto_send_disabled"}

    phone = (lead.phone or "").strip()
    if not phone and isinstance(lead.custom_fields, dict):
        phone = str(lead.custom_fields.get("wa_id") or "")

    if not whatsapp_cloud_configured():
        return {"status": "skipped", "reason": "whatsapp_cloud_not_configured"}

    try:
        assert_whatsapp_outbound_allowed(lead)
    except WhatsAppSendBlocked as exc:
        return {"status": "blocked", "reason": exc.code}

    name = lead.primary_contact_name or "there"
    company = lead.company_name or "your business"
    # Prefer short heuristic reply (NIM optional later)
    reply = (
        f"Hi {name.split()[0] if name else 'there'} — thanks for messaging PorterChain. "
        f"We provide vehicle + driver capacity for merchants like {company}. "
        f"Share your city and approx monthly deliveries and we'll point you to a quote: "
        f"https://porterchain.com/sign-up?intent=quote&utm_source=wa_agent"
    )
    if inbound_text and len(inbound_text) > 20:
        reply = (
            f"Thanks for your note — PorterChain here. "
            f"We help with vehicle + driver capacity across the GTA. "
            f"Reply with deliveries/month + cities, or book via "
            f"https://porterchain.com/sign-up?intent=quote&utm_source=wa_agent"
        )

    result = send_whatsapp_text(phone=phone, body=reply, lead_id=lead.id)
    if result.get("status") == "sent":
        _mark_welcomed(lead, channel="whatsapp_reply", detail=result)
        _set_cf(
            lead,
            {
                "last_inbound_reply_at": datetime.now(UTC).isoformat(),
                "inbound_preview": (inbound_text or "")[:120],
            },
        )
        db.flush()
    return result


def maybe_auto_reply_after_ingest(
    db: Session,
    lead: CrmLead,
    *,
    channel: str | None,
    message: str | None,
) -> dict[str, Any] | None:
    """Hook for webhook / queued ingest when channel is WhatsApp DM."""
    ch = (channel or lead.channel or "").lower()
    if ch != "whatsapp":
        return None
    tags = lead.tags or []
    if "dm" not in tags and "meta" not in tags:
        # Still allow if source is whatsapp
        if (lead.source or "").lower() != "whatsapp":
            return None
    try:
        return reply_inbound_whatsapp(db, lead, inbound_text=message or "")
    except Exception:
        logger.exception("wa_auto_reply_failed lead=%s", lead.id)
        return {"status": "error", "reason": "reply_exception"}


def run_lead_agent(
    db: Session,
    lead: CrmLead,
    *,
    trigger: str = "manual",
    website_url: str = "",
    force: bool = False,
) -> dict[str, Any]:
    """Autonomous welcome — email when lawful; WA when Cloud configured + gated."""
    ensure_inbound_sla(db, lead)
    nba = lead_next_best_action(db, lead)
    out: dict[str, Any] = {
        "lead_id": lead.id,
        "trigger": trigger,
        "nba": nba,
        "channels": {},
        "auto_send_enabled": _agent_enabled(),
    }

    if not _agent_enabled() and not force:
        _set_cf(lead, {"status": "disabled", "last_trigger": trigger})
        out["channels"]["agent"] = {"status": "skipped", "reason": "auto_send_disabled"}
        return out

    if nba.get("already_welcomed") and not force:
        out["channels"]["agent"] = {"status": "skipped", "reason": "already_welcomed"}
        return out

    primary = nba.get("primary") or {}
    action = primary.get("action")

    if action == "email_template":
        email_result = _send_email(
            db,
            lead,
            template_key=str(primary.get("template_key") or _INTRO_TEMPLATE),
            recipient=str(primary.get("recipient") or ""),
            website_url=website_url,
        )
        out["channels"]["email"] = email_result
    elif action == "enrich_email":
        out["channels"]["enrich"] = {
            "status": "queued",
            "reason": primary.get("reason"),
            "phone": primary.get("phone"),
        }
        _set_cf(
            lead,
            {
                "status": "needs_enrich",
                "last_trigger": trigger,
                "reason": primary.get("reason"),
            },
        )
        tags = list(lead.tags or [])
        if "needs_enrich" not in tags:
            tags.append("needs_enrich")
            lead.tags = tags
        try:
            from porterchain_api.collaboration_engine.lead_enrich import enrich_lead_email

            er = enrich_lead_email(db, lead)
            out["channels"]["enrich"] = er
            if er.get("status") == "found" and (lead.consent or {}).get("marketing"):
                email_result = _send_email(
                    db,
                    lead,
                    template_key=_INTRO_TEMPLATE,
                    recipient=str(lead.email),
                    website_url=website_url,
                )
                out["channels"]["email"] = email_result
        except Exception:
            logger.exception("inline_enrich_failed lead=%s", lead.id)
    elif action in ("stop", "noop", "capture_contact"):
        out["channels"]["agent"] = {
            "status": "skipped",
            "reason": primary.get("reason") or action,
            "blocks": nba.get("blocks"),
        }
        _set_cf(
            lead,
            {
                "status": "blocked" if nba.get("blocks") else "noop",
                "last_trigger": trigger,
                "blocks": nba.get("blocks"),
            },
        )
    else:
        out["channels"]["agent"] = {"status": "skipped", "reason": f"unhandled:{action}"}

    # Also attempt WA alternative when primary was email and WA is an alternative
    # (dual-channel welcome) — only if Cloud configured.
    if action == "email_template" and (out.get("channels") or {}).get("email", {}).get(
        "status"
    ) == "sent":
        wa_alt = next(
            (
                a
                for a in (nba.get("alternatives") or [])
                if a.get("action") == "whatsapp_template"
            ),
            None,
        )
        if wa_alt:
            # Don't double-mark; WA is additive if cloud works
            tags = list(lead.tags or [])
            # temporarily allow second channel — use cloud only
            from porterchain_api.collaboration_engine.lead_whatsapp_cloud import (
                whatsapp_cloud_configured,
            )

            if whatsapp_cloud_configured():
                # Welcome tag already set; send WA without re-checking already
                wa_result = _try_whatsapp(db, lead, wa_alt)
                out["channels"]["whatsapp"] = wa_result
    elif action != "email_template":
        if action == "enrich_email":
            # Cold / phone-only: never auto WA blast
            out["channels"]["whatsapp"] = {
                "status": "skipped",
                "reason": "no_cold_whatsapp_blast",
            }

    db.flush()
    return out


def process_lead_agent_batch(db: Session, *, limit: int = 25) -> dict[str, int]:
    """Worker tick: welcome NEW leads that still need agent (email+consent)."""
    from sqlalchemy import String, cast, not_

    q = (
        db.query(CrmLead)
        .filter(
            CrmLead.status == LeadStatus.NEW.value,
            CrmLead.email.isnot(None),
            CrmLead.email != "",
            not_(cast(CrmLead.tags, String).ilike(f"%{_WELCOME_TAG}%")),
        )
        .order_by(CrmLead.created_at.asc())
        .limit(limit)
        .all()
    )
    sent = skipped = 0
    from porterchain_api.config import get_settings

    website = getattr(get_settings(), "website_url", "") or ""
    for lead in q:
        consent = lead.consent if isinstance(lead.consent, dict) else {}
        if not consent.get("marketing"):
            skipped += 1
            continue
        result = run_lead_agent(db, lead, trigger="worker", website_url=website)
        email = (result.get("channels") or {}).get("email") or {}
        if email.get("status") == "sent":
            sent += 1
        else:
            skipped += 1
    if sent or skipped:
        db.commit()
    return {"scanned": len(q), "sent": sent, "skipped": skipped}


def staff_welcome_lead(
    db: Session,
    lead: CrmLead,
    *,
    website_url: str = "",
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Staff-triggered welcome; commits when not dry_run."""
    if dry_run:
        return {"ok": True, "dry_run": True, "nba": lead_next_best_action(db, lead)}
    result = run_lead_agent(
        db,
        lead,
        trigger="staff",
        website_url=website_url,
        force=force,
    )
    db.commit()
    return {"ok": True, **result}


__all__ = [
    "ensure_inbound_sla",
    "maybe_auto_reply_after_ingest",
    "process_lead_agent_batch",
    "reply_inbound_whatsapp",
    "run_lead_agent",
    "staff_welcome_lead",
]
