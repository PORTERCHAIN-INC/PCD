"""Next-best-action for CrmLead — evidence-first, consent-aware."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmLead, CrmLeadIdentity
from porterchain_api.domain.crm_states import LeadIdentityKind, LeadStatus

_VENDOR = "vendor_import"
_WELCOME_TAG = "agent_welcomed"


def resolve_contacts(db: Session, lead: CrmLead) -> dict[str, Any]:
    """Any reachable email/phone on the lead + identities."""
    emails: list[str] = []
    phones: list[str] = []
    if (lead.email or "").strip() and "@" in (lead.email or ""):
        emails.append((lead.email or "").strip().lower())
    if (lead.phone or "").strip():
        phones.append((lead.phone or "").strip())

    rows = (
        db.query(CrmLeadIdentity)
        .filter(CrmLeadIdentity.lead_id == lead.id)
        .all()
    )
    for row in rows:
        kind = (row.kind or "").lower()
        val = (row.value_normalized or row.raw_value or "").strip()
        if not val:
            continue
        if kind in (LeadIdentityKind.EMAIL.value, "email") and "@" in val:
            emails.append(val.lower())
        elif kind in (
            LeadIdentityKind.PHONE_E164.value,
            LeadIdentityKind.WHATSAPP_WA_ID.value,
            "phone",
            "phone_e164",
            "whatsapp_wa_id",
        ):
            phones.append(val)

    # Dedupe preserve order
    def uniq(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    emails_u = uniq(emails)
    phones_u = uniq(phones)
    return {
        "emails": emails_u,
        "phones": phones_u,
        "primary_email": emails_u[0] if emails_u else None,
        "primary_phone": phones_u[0] if phones_u else None,
    }


def lead_next_best_action(db: Session, lead: CrmLead) -> dict[str, Any]:
    """Rank lawful autonomous actions for this lead."""
    from porterchain_api.collaboration_engine.lead_suppression import is_suppressed
    from porterchain_api.collaboration_engine.lead_whatsapp_gate import (
        whatsapp_outbound_status,
    )

    contacts = resolve_contacts(db, lead)
    consent = lead.consent if isinstance(lead.consent, dict) else {}
    marketing = consent.get("marketing") is True
    wa_consent = consent.get("whatsapp") is True
    suppressed = is_suppressed(
        db, email=contacts["primary_email"], phone=contacts["primary_phone"]
    )
    wa = whatsapp_outbound_status(lead)
    tags = list(lead.tags or [])
    already = _WELCOME_TAG in tags
    source = (lead.source or "").strip()
    is_vendor = source == _VENDOR
    now = datetime.now(UTC)
    sla_due = lead.sla_first_response_due_at
    if sla_due is not None and sla_due.tzinfo is None:
        sla_due = sla_due.replace(tzinfo=UTC)
    sla_breached = bool(
        sla_due
        and sla_due < now
        and lead.status == LeadStatus.NEW.value
    )

    blocks: list[str] = []
    alternatives: list[dict[str, Any]] = []
    primary: dict[str, Any] | None = None

    if suppressed:
        blocks.append("suppressed")
        return _pack(
            "blocked",
            primary={"action": "stop", "reason": "suppressed"},
            alternatives=[],
            blocks=blocks,
            contacts=contacts,
            already=already,
            sla_breached=sla_breached,
            class_name="blocked",
        )

    if lead.status == LeadStatus.CONVERTED.value:
        return _pack(
            "done",
            primary={"action": "stop", "reason": "converted"},
            alternatives=[],
            blocks=["converted"],
            contacts=contacts,
            already=already,
            sla_breached=False,
            class_name="converted",
        )

    if already:
        primary = {"action": "noop", "reason": "already_welcomed"}
        class_name = "warmed" if contacts["primary_email"] else "outbound_cold"
    elif contacts["primary_email"] and marketing:
        primary = {
            "action": "email_template",
            "template_key": "lead_nurture_intro",
            "recipient": contacts["primary_email"],
            "reason": "marketing_consent",
        }
        class_name = "inbound_hot" if not is_vendor else "warmed"
    elif contacts["primary_email"] and not marketing:
        blocks.append("marketing_consent_required")
        class_name = "inbound_reply" if not is_vendor else "outbound_cold"
    elif is_vendor and contacts["primary_phone"] and not contacts["primary_email"]:
        primary = {
            "action": "enrich_email",
            "reason": "phone_only_cold_vendor",
            "phone": contacts["primary_phone"],
        }
        class_name = "outbound_cold"
        alternatives.append(
            {
                "action": "call",
                "reason": "human_or_voice_fallback",
                "phone": contacts["primary_phone"],
            }
        )
    elif contacts["primary_phone"] and not contacts["primary_email"]:
        primary = {
            "action": "enrich_email",
            "reason": "phone_only",
            "phone": contacts["primary_phone"],
        }
        class_name = "inbound_reply"
    else:
        primary = {"action": "capture_contact", "reason": "no_email_or_phone"}
        blocks.append("no_reachable_contact")
        class_name = "blocked"

    # WhatsApp alternative when Cloud path may apply
    if contacts["primary_phone"] and wa["allowed"] and not already:
        alternatives.append(
            {
                "action": "whatsapp_template",
                "template_key": "lead_welcome",
                "phone": contacts["primary_phone"],
                "reason": wa["reason"],
            }
        )
    elif contacts["primary_phone"] and not wa["allowed"]:
        blocks.append(str(wa["reason"]))

    if contacts["primary_phone"]:
        alternatives.append(
            {
                "action": "whatsapp_deeplink",
                "phone": contacts["primary_phone"],
                "url": _wa_deeplink(contacts["primary_phone"], lead),
                "reason": "staff_or_future_cloud",
            }
        )

    if sla_breached:
        alternatives.append({"action": "escalate_sla", "reason": "first_response_overdue"})

    if primary is None:
        primary = {"action": "noop", "reason": "no_action"}

    return _pack(
        primary["action"],
        primary=primary,
        alternatives=alternatives,
        blocks=blocks,
        contacts=contacts,
        already=already,
        sla_breached=sla_breached,
        class_name=class_name,
        marketing=marketing,
        wa_consent=wa_consent,
        whatsapp=wa,
    )


def _wa_deeplink(phone: str, lead: CrmLead) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    company = (lead.company_name or "your business").strip()
    msg = (
        f"Hi — this is PorterChain. We help {company} with vehicle + driver capacity "
        "in the GTA. Reply if you'd like a quick quote."
    )
    from urllib.parse import quote

    return f"https://wa.me/{digits}?text={quote(msg)}"


def _pack(
    primary_action: str,
    *,
    primary: dict[str, Any],
    alternatives: list[dict[str, Any]],
    blocks: list[str],
    contacts: dict[str, Any],
    already: bool,
    sla_breached: bool,
    class_name: str,
    marketing: bool = False,
    wa_consent: bool = False,
    whatsapp: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "class": class_name,
        "primary": primary,
        "primary_action": primary_action,
        "alternatives": alternatives,
        "blocks": blocks,
        "contacts": contacts,
        "already_welcomed": already,
        "sla_breached": sla_breached,
        "marketing_consent": marketing,
        "whatsapp_consent": wa_consent,
        "whatsapp": whatsapp or {},
    }


__all__ = ["_WELCOME_TAG", "lead_next_best_action", "resolve_contacts"]
