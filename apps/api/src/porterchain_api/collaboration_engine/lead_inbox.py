"""Unified lead inbox actions: reply (email / WhatsApp), log a call, bulk edit, CSV export.

Every send here is an explicit staff action from the admin UI. Nothing in this
module runs on a timer or on ingest.
"""

from __future__ import annotations

import csv
import io
import logging
import smtplib
import ssl
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_helpers import _now
from porterchain_api.config import Settings
from porterchain_api.collaboration_engine.lead_pipeline import advance, mark_quoted, stamp_status_change
from porterchain_api.crm_models import (
    CrmActivity,
    CrmConversation,
    CrmConversationMessage,
    CrmLead,
)
from porterchain_api.domain.crm_states import LeadPriority, LeadStatus, normalize_lead_status

logger = logging.getLogger(__name__)

WA_SERVICE_WINDOW = timedelta(hours=24)
CALL_DIRECTIONS = ("inbound", "outbound")
CALL_OUTCOMES = (
    "connected",
    "no_answer",
    "voicemail",
    "callback",
    "interested",
    "quote_requested",
    "not_interested",
    "wrong_number",
)
BULK_STATUSES = frozenset(s.value for s in LeadStatus)
BULK_PRIORITIES = frozenset(p.value for p in LeadPriority)


class ReplyError(Exception):
    """Send refused or failed. ``code`` is shown to staff."""

    def __init__(self, code: str, *, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


# --------------------------------------------------------------------------- #
# Channel status
# --------------------------------------------------------------------------- #
def email_channel_status(settings: Settings) -> dict[str, Any]:
    transport = (settings.lead_reply_email_transport or "").strip().lower()
    if transport == "zeptomail":
        from porterchain_shared.config.settings import get_platform_settings

        ok = bool((get_platform_settings().smtp_password or "").strip())
        reason = None if ok else "zeptomail_token_missing"
    elif transport == "zoho_smtp":
        ok = bool(settings.zoho_mail_user.strip() and settings.zoho_mail_app_password.strip())
        reason = None if ok else "zoho_smtp_credentials_missing"
    else:
        ok, reason = False, "email_reply_transport_not_configured"
    return {
        "enabled": ok,
        "transport": transport or None,
        "from": settings.lead_reply_from,
        "reason": reason,
    }


def whatsapp_channel_status(settings: Settings, lead: CrmLead | None = None) -> dict[str, Any]:
    from porterchain_api.collaboration_engine.lead_whatsapp_cloud import (
        whatsapp_cloud_configured,
    )

    if not settings.whatsapp_cloud_enabled:
        return {"enabled": False, "reason": "whatsapp_cloud_disabled"}
    if not whatsapp_cloud_configured():
        return {"enabled": False, "reason": "whatsapp_cloud_not_configured"}
    out: dict[str, Any] = {"enabled": True, "reason": None}
    if lead is not None:
        last = _aware(getattr(lead, "last_inbound_at", None))
        wa_thread = bool(_wa_number(lead))
        in_window = bool(last and datetime.now(UTC) - last <= WA_SERVICE_WINDOW)
        out["in_service_window"] = in_window
        out["window_closes_at"] = (last + WA_SERVICE_WINDOW).isoformat() if last else None
        if not wa_thread:
            out.update(enabled=False, reason="lead_has_no_whatsapp_number")
        elif not in_window:
            out.update(enabled=False, reason="outside_24h_service_window")
    return out


def reply_channels(settings: Settings, lead: CrmLead | None = None) -> dict[str, Any]:
    return {
        "email": email_channel_status(settings),
        "whatsapp": whatsapp_channel_status(settings, lead),
    }


def _wa_number(lead: CrmLead) -> str | None:
    cf = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
    raw = cf.get("wa_id") or (lead.phone if lead.channel == "whatsapp" else None)
    digits = "".join(c for c in str(raw or "") if c.isdigit())
    return digits or None


# --------------------------------------------------------------------------- #
# Thread helpers
# --------------------------------------------------------------------------- #
def _thread(db: Session, lead: CrmLead, channel: str) -> CrmConversation:
    convo = (
        db.query(CrmConversation)
        .filter(
            CrmConversation.lead_id == lead.id,
            CrmConversation.channel == channel,
            CrmConversation.status == "open",
        )
        .order_by(CrmConversation.created_at.desc())
        .first()
    )
    if convo is None:
        convo = CrmConversation(lead_id=lead.id, channel=channel, status="open")
        db.add(convo)
        db.flush()
    return convo


def _activity(
    db: Session, lead: CrmLead, *, kind: str, subject: str, actor_id: str | None, meta: dict
) -> None:
    db.add(
        CrmActivity(
            entity_type="lead",
            entity_id=lead.id,
            activity_type=kind,
            subject=subject[:255],
            actor_id=actor_id,
            metadata_json=meta,
        )
    )


def mark_responded(lead: CrmLead, *, at: datetime | None = None) -> None:
    now = at or _now()
    lead.awaiting_reply = False
    lead.last_touch_at = now
    if lead.first_response_at is None:
        lead.first_response_at = now
    if lead.status in (LeadStatus.NEW.value, LeadStatus.LOST.value, LeadStatus.ARCHIVED.value):
        lead.status = LeadStatus.NEW.value  # re-open, then advance
        advance(lead, LeadStatus.REPLIED.value, at=now)


# --------------------------------------------------------------------------- #
# Reply
# --------------------------------------------------------------------------- #
def send_lead_reply(
    db: Session,
    settings: Settings,
    lead: CrmLead,
    *,
    channel: str,
    body: str,
    subject: str | None,
    actor_id: str,
    quote: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Staff-initiated reply. Raises ReplyError when the channel is off or refused.

    ``quote`` (from the lead's instant quote) moves the lead to Quoted once sent.
    """
    text = (body or "").strip()
    if not text:
        raise ReplyError("body_required", status=422)
    if len(text) > 10_000:
        raise ReplyError("body_too_long", status=422)
    ch = (channel or "").strip().lower()
    if ch == "email":
        result = _reply_email(db, settings, lead, text=text, subject=subject)
    elif ch == "whatsapp":
        result = _reply_whatsapp(settings, lead, text=text)
    else:
        raise ReplyError("unsupported_channel", status=422)

    convo = _thread(db, lead, ch)
    msg = CrmConversationMessage(
        conversation_id=convo.id,
        direction="outbound",
        body=text if ch == "whatsapp" else f"{result.get('subject', '')}\n\n{text}".strip(),
        actor_type="staff",
        actor_id=actor_id,
        channel=ch,
        external_message_id=result.get("message_id"),
        delivery_status=result.get("status", "sent"),
        metadata_json={k: v for k, v in result.items() if k in ("to", "transport", "subject")},
    )
    db.add(msg)
    mark_responded(lead)
    if quote:
        mark_quoted(lead, quote)
    _activity(
        db,
        lead,
        kind="email" if ch == "email" else "whatsapp",
        subject=f"Replied by {ch}",
        actor_id=actor_id,
        meta={"channel": ch, "to": result.get("to")},
    )
    db.commit()
    db.refresh(msg)
    return {
        "id": msg.id,
        "channel": ch,
        "status": msg.delivery_status,
        "to": result.get("to"),
        "occurred_at": msg.occurred_at.isoformat() if msg.occurred_at else None,
    }


def _reply_email(
    db: Session, settings: Settings, lead: CrmLead, *, text: str, subject: str | None
) -> dict[str, Any]:
    status = email_channel_status(settings)
    if not status["enabled"]:
        raise ReplyError(str(status["reason"]), status=409)
    to = (lead.email or "").strip()
    if "@" not in to:
        raise ReplyError("lead_has_no_email", status=409)
    from porterchain_api.collaboration_engine.lead_suppression import is_suppressed

    if is_suppressed(db, email=to, phone=None):
        # Do-not-contact wins even for one-to-one replies.
        raise ReplyError("suppressed", status=409)
    subj = (subject or "").strip() or f"Re: your PorterChain inquiry ({lead.company_name})"
    subj = subj[:200]
    transport = status["transport"]
    try:
        if transport == "zoho_smtp":
            message_id = send_via_zoho_smtp(settings, to=to, subject=subj, text=text)
        else:
            message_id = send_via_zeptomail(settings, to=to, subject=subj, text=text)
    except ReplyError:
        raise
    except Exception as exc:
        logger.warning("lead_reply_email_failed lead=%s err=%s", lead.id, str(exc)[:200])
        raise ReplyError("email_send_failed", status=502) from exc
    return {
        "status": "sent",
        "to": to,
        "subject": subj,
        "transport": transport,
        "message_id": message_id,
    }


def _plain_to_html(text: str) -> str:
    import html

    paras = [html.escape(p).replace("\n", "<br>") for p in text.split("\n\n")]
    return "".join(f"<p>{p}</p>" for p in paras)


def send_via_zeptomail(settings: Settings, *, to: str, subject: str, text: str) -> str | None:
    """ZeptoMail HTTPS API from sales@ (same token the platform mailer uses)."""
    import httpx
    from porterchain_shared.config.settings import get_platform_settings

    platform = get_platform_settings()
    token = (platform.smtp_password or "").strip()
    if not token:
        raise ReplyError("zeptomail_token_missing", status=409)
    auth = token if token.startswith("Zoho-enczapikey") else f"Zoho-enczapikey {token}"
    api_url = (
        getattr(platform, "zeptomail_api_url", None) or "https://api.zeptomail.ca/v1.1/email"
    ).strip()
    payload = {
        "from": {"address": settings.lead_reply_from, "name": settings.lead_reply_from_name},
        "reply_to": [{"address": settings.lead_reply_from}],
        "to": [{"email_address": {"address": to}}],
        "subject": subject,
        "textbody": text,
        "htmlbody": _plain_to_html(text),
    }
    resp = httpx.post(
        api_url,
        json=payload,
        headers={"accept": "application/json", "authorization": auth},
        timeout=30.0,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"zeptomail_http_{resp.status_code}")
    try:
        data = resp.json()
        return str((data.get("data") or [{}])[0].get("message_id") or "") or None
    except Exception:  # noqa: BLE001
        return None


def send_via_zoho_smtp(settings: Settings, *, to: str, subject: str, text: str) -> str:
    """Zoho Mail SMTP with an app password — lands in the sales@ Sent folder."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.lead_reply_from_name} <{settings.lead_reply_from}>"
    msg["To"] = to
    message_id = make_msgid(domain=settings.lead_reply_from.split("@")[-1] or "porterchain.com")
    msg["Message-ID"] = message_id
    msg.set_content(text)
    msg.add_alternative(_plain_to_html(text), subtype="html")
    ctx = ssl.create_default_context()
    host, port = settings.zoho_smtp_host, int(settings.zoho_smtp_port or 465)
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as smtp:
            smtp.login(settings.zoho_mail_user, settings.zoho_mail_app_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls(context=ctx)
            smtp.login(settings.zoho_mail_user, settings.zoho_mail_app_password)
            smtp.send_message(msg)
    return message_id


def _reply_whatsapp(settings: Settings, lead: CrmLead, *, text: str) -> dict[str, Any]:
    status = whatsapp_channel_status(settings, lead)
    if not status["enabled"]:
        raise ReplyError(str(status["reason"]), status=409)
    from porterchain_api.collaboration_engine.lead_whatsapp_cloud import (
        send_whatsapp_text,
    )

    number = _wa_number(lead) or ""
    out = send_whatsapp_text(phone=number, body=text, lead_id=lead.id)
    if out.get("status") != "sent":
        raise ReplyError(str(out.get("reason") or "whatsapp_send_failed"), status=502)
    return {"status": "sent", "to": out.get("to"), "message_id": out.get("message_id")}


# --------------------------------------------------------------------------- #
# Log a call (regular mobile — no telephony integration)
# --------------------------------------------------------------------------- #
def log_call(
    db: Session,
    lead: CrmLead,
    *,
    direction: str,
    outcome: str,
    notes: str | None,
    duration_minutes: int | None,
    actor_id: str,
    follow_up_at: datetime | None = None,
) -> dict[str, Any]:
    d = (direction or "").strip().lower()
    o = (outcome or "").strip().lower()
    if d not in CALL_DIRECTIONS:
        raise ReplyError("invalid_direction", status=422)
    if o not in CALL_OUTCOMES:
        raise ReplyError("invalid_outcome", status=422)
    now = _now()
    label = f"{'Inbound' if d == 'inbound' else 'Outbound'} call — {o.replace('_', ' ')}"
    if duration_minutes:
        label += f" ({int(duration_minutes)} min)"
    body = label + (f"\n{notes.strip()}" if notes and notes.strip() else "")
    convo = _thread(db, lead, "phone_call")
    msg = CrmConversationMessage(
        conversation_id=convo.id,
        direction=d,
        body=body,
        actor_type="staff",
        actor_id=actor_id,
        channel="phone_call",
        delivery_status="logged",
        metadata_json={"call": True, "outcome": o, "duration_minutes": duration_minutes},
    )
    db.add(msg)
    if d == "inbound":
        lead.last_inbound_at = now
    if o in ("connected", "interested", "quote_requested", "callback", "not_interested") or (
        d == "inbound"
    ):
        # A live conversation (either way) answers the lead.
        mark_responded(lead, at=now)
    else:
        lead.last_touch_at = now
    if o == "not_interested":
        stamp_status_change(lead, LeadStatus.LOST.value, at=now)
        lead.status = LeadStatus.LOST.value
        lead.lost_reason = lead.lost_reason or "not_a_fit"
    elif o == "wrong_number" and lead.status == LeadStatus.NEW.value:
        pass  # not an answer; keep it in New
    task_id = None
    if follow_up_at is not None or o == "callback":
        from porterchain_api.crm_models import CrmSalesTask

        task = CrmSalesTask(
            title=f"Call back {lead.company_name}"[:255],
            description=notes or None,
            task_type="call",
            status="open",
            priority=lead.priority or "medium",
            entity_type="lead",
            entity_id=lead.id,
            due_at=follow_up_at or now + timedelta(days=1),
            assigned_to=lead.assigned_to or actor_id,
            created_by=actor_id,
        )
        db.add(task)
        db.flush()
        task_id = task.id
    _activity(
        db,
        lead,
        kind="call",
        subject=label,
        actor_id=actor_id,
        meta={"direction": d, "outcome": o, "duration_minutes": duration_minutes},
    )
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "status": lead.status, "task_id": task_id}


# --------------------------------------------------------------------------- #
# Bulk + export
# --------------------------------------------------------------------------- #
def bulk_update(
    db: Session,
    lead_ids: list[str],
    *,
    assigned_to: str | None = None,
    unassign: bool = False,
    status: str | None = None,
    priority: str | None = None,
) -> dict[str, Any]:
    ids = [i for i in dict.fromkeys(lead_ids) if i][:500]
    if not ids:
        raise ReplyError("lead_ids_required", status=422)
    status = normalize_lead_status(status) if status else None
    if status and status not in BULK_STATUSES:
        raise ReplyError("invalid_status", status=422)
    if priority and priority not in BULK_PRIORITIES:
        raise ReplyError("invalid_priority", status=422)
    if not (assigned_to or unassign or status or priority):
        raise ReplyError("nothing_to_update", status=422)
    if assigned_to and not unassign:
        from porterchain_api.collaboration_engine.lead360_service import staff_user_exists

        if not staff_user_exists(db, assigned_to):
            raise ReplyError("assignee_not_found", status=422)
    rows = db.query(CrmLead).filter(CrmLead.id.in_(ids)).all()
    for lead in rows:
        if unassign:
            lead.assigned_to = None
        elif assigned_to:
            lead.assigned_to = assigned_to
        if status:
            stamp_status_change(lead, status)
            lead.status = status
            if status in (LeadStatus.CONVERTED.value, LeadStatus.ARCHIVED.value):
                lead.awaiting_reply = False
        if priority:
            lead.priority = priority
    db.commit()
    return {"updated": len(rows), "missing": len(ids) - len(rows)}


EXPORT_COLUMNS = (
    "id",
    "created_at",
    "company_name",
    "primary_contact_name",
    "email",
    "phone",
    "channel",
    "source",
    "intent_type",
    "status",
    "priority",
    "lead_score",
    "assigned_to",
    "awaiting_reply",
    "sla_first_response_due_at",
    "first_response_at",
    "industry",
    "estimated_deliveries_per_month",
    "service_area",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "marketing_consent",
)


def _csv_safe(value: Any) -> str:
    """Neutralise spreadsheet formula injection (=, +, -, @ prefixes)."""
    if value is None:
        return ""
    text = value.isoformat() if isinstance(value, datetime) else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def leads_by_ids(db: Session, ids: list[str]) -> list[CrmLead]:
    if not ids:
        return []
    return db.query(CrmLead).filter(CrmLead.id.in_(ids)).all()


def leads_to_csv(leads: list[CrmLead]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPORT_COLUMNS)
    for lead in leads:
        cf = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
        consent = lead.consent if isinstance(lead.consent, dict) else {}
        row = []
        for col in EXPORT_COLUMNS:
            if col.startswith("utm_"):
                row.append(_csv_safe(cf.get(col)))
            elif col == "marketing_consent":
                row.append("yes" if consent.get("marketing") is True else "no")
            else:
                row.append(_csv_safe(getattr(lead, col, None)))
        writer.writerow(row)
    return buf.getvalue()


__all__ = [
    "CALL_OUTCOMES",
    "ReplyError",
    "bulk_update",
    "email_channel_status",
    "leads_to_csv",
    "log_call",
    "mark_responded",
    "reply_channels",
    "send_lead_reply",
    "send_via_zeptomail",
    "send_via_zoho_smtp",
    "whatsapp_channel_status",
]
