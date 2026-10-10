"""Inbound email (sales@ on Zoho Mail) → lead conversation threads.

Two feeds share one ingest path:

* **IMAP poll** (default, simplest with Zoho): the worker reads UNSEEN mail
  from the sales@ mailbox with an app password, behind
  ``LEAD_INBOUND_IMAP_ENABLED``. Mail is marked seen only after ingest.
* **Inbound webhook** ``POST /v1/public/mail/inbound`` — HMAC-signed JSON for
  any forwarder that can POST parsed mail.

Matching uses the Lead Ingest Bus identity spine (email), so a reply from a
known lead lands on that lead's thread and flips it to "awaiting reply".
Idempotent on the RFC 5322 Message-ID. Never sends anything.
"""

from __future__ import annotations

import email
import email.policy
import imaplib
import logging
import re
from dataclasses import dataclass, field
from email.utils import getaddresses, parseaddr
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.crm_models import CrmLead

logger = logging.getLogger(__name__)

PROVIDER = "email_inbound"
_MAX_BODY = 8000
_SKIP_LOCALPARTS = ("mailer-daemon", "postmaster", "no-reply", "noreply", "do-not-reply", "bounce")
_QUOTE_MARKERS = (
    re.compile(r"^On .{0,200} wrote:\s*$", re.MULTILINE),
    re.compile(r"^Le .{0,200} a écrit\s*:\s*$", re.MULTILINE),
    re.compile(r"^-{2,}\s*Original Message\s*-{2,}", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^From: .+$", re.MULTILINE),
)


@dataclass
class InboundEmail:
    from_addr: str
    from_name: str | None
    to: list[str]
    subject: str
    text: str
    message_id: str
    headers: dict[str, str] = field(default_factory=dict)


def strip_quoted(text: str) -> str:
    """Keep only the new part of a reply (drop quoted history / signatures blocks)."""
    body = (text or "").replace("\r\n", "\n")
    cut = len(body)
    for pat in _QUOTE_MARKERS:
        m = pat.search(body)
        if m and m.start() > 0:
            cut = min(cut, m.start())
    lines = [ln for ln in body[:cut].split("\n") if not ln.startswith(">")]
    return "\n".join(lines).strip()


def should_skip(msg: InboundEmail, settings: Settings) -> str | None:
    sender = (msg.from_addr or "").lower()
    if "@" not in sender:
        return "no_sender"
    local, _, domain = sender.partition("@")
    if any(local.startswith(p) for p in _SKIP_LOCALPARTS):
        return "system_sender"
    own = {settings.lead_reply_from.lower(), (settings.zoho_mail_user or "").lower()}
    if sender in own:
        return "own_address"
    h = {k.lower(): (v or "").lower() for k, v in msg.headers.items()}
    if h.get("auto-submitted", "no") not in ("", "no"):
        return "auto_reply"
    if h.get("precedence") in ("bulk", "list", "junk") or h.get("list-unsubscribe"):
        return "bulk_mail"
    if h.get("x-autoreply") or h.get("x-autorespond"):
        return "auto_reply"
    return None


def ingest_inbound_email(db: Session, settings: Settings, msg: InboundEmail) -> dict[str, Any]:
    reason = should_skip(msg, settings)
    if reason:
        return {"status": "skipped", "reason": reason}
    from porterchain_api.collaboration_engine.lead_ingest_service import (
        CanonicalLeadEvent,
        LeadIngestService,
        normalize_email,
    )
    from porterchain_api.crm_models import CrmLeadIdentity

    sender = normalize_email(msg.from_addr) or ""
    known = (
        db.query(CrmLeadIdentity)
        .filter(CrmLeadIdentity.kind == "email", CrmLeadIdentity.value_normalized == sender)
        .first()
        or db.query(CrmLead).filter(CrmLead.email == sender).first()
    )
    if not known and not settings.lead_inbound_email_create_leads:
        return {"status": "skipped", "reason": "unknown_sender"}
    body = strip_quoted(msg.text)[:_MAX_BODY] or "(empty message)"
    subject = (msg.subject or "").strip()[:255]
    text = f"{subject}\n\n{body}".strip() if subject else body
    name = (msg.from_name or "").strip() or sender.split("@", 1)[0]
    domain = sender.split("@", 1)[1] if "@" in sender else ""
    result = LeadIngestService().ingest(
        db,
        CanonicalLeadEvent(
            channel="email",
            source="email_inbound",
            provider=PROVIDER,
            external_event_id=(msg.message_id or "")[:255] or f"noid:{sender}:{hash(text)}",
            company_name=name[:255],
            primary_contact_name=name[:255],
            email=sender,
            intent_type="merchant",
            priority="high",
            message=text,
            tags=["email"],
            custom_fields={
                "email_domain": domain,
                "message_meta": {"subject": subject, "to": msg.to[:5]},
            },
            seed_conversation=True,
            skip_outreach=True,
        ),
    )
    return {"status": "ingested", "lead_id": result.lead.id, "created": result.created}


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def _text_from_message(m: email.message.EmailMessage) -> str:
    part = m.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    content = part.get_content()
    if part.get_content_type() == "text/html":
        content = re.sub(r"<(br|/p|/div)[^>]*>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"<[^>]+>", "", content)
        import html

        content = html.unescape(content)
    return str(content)


def parse_rfc822(raw: bytes) -> InboundEmail:
    m = email.message_from_bytes(raw, policy=email.policy.default)
    name, addr = parseaddr(str(m.get("From") or ""))
    to = [a for _, a in getaddresses([str(m.get("To") or ""), str(m.get("Cc") or "")]) if a]
    headers = {
        k: str(m.get(k) or "")
        for k in ("Auto-Submitted", "Precedence", "List-Unsubscribe", "X-Autoreply", "X-Autorespond")
        if m.get(k)
    }
    return InboundEmail(
        from_addr=addr,
        from_name=name or None,
        to=to,
        subject=str(m.get("Subject") or ""),
        text=_text_from_message(m),  # type: ignore[arg-type]
        message_id=str(m.get("Message-ID") or "").strip(),
        headers=headers,
    )


# --------------------------------------------------------------------------- #
# IMAP poll (worker)
# --------------------------------------------------------------------------- #
def imap_configured(settings: Settings) -> bool:
    return bool(
        settings.lead_inbound_imap_enabled
        and settings.zoho_mail_user.strip()
        and settings.zoho_mail_app_password.strip()
    )


def poll_imap_once(
    db: Session, settings: Settings, *, limit: int = 25, imap_factory: Any = None
) -> dict[str, int]:
    """Read UNSEEN mail, ingest, then mark seen. Returns counters."""
    out = {"fetched": 0, "ingested": 0, "skipped": 0, "failed": 0}
    if not imap_configured(settings):
        return out
    factory = imap_factory or (lambda: imaplib.IMAP4_SSL(settings.zoho_imap_host, 993))
    conn = factory()
    try:
        conn.login(settings.zoho_mail_user, settings.zoho_mail_app_password)
        conn.select(settings.zoho_imap_folder or "INBOX")
        typ, data = conn.uid("search", None, "UNSEEN")
        if typ != "OK":
            return out
        uids = (data[0] or b"").split()[:limit]
        for uid in uids:
            out["fetched"] += 1
            # BODY.PEEK keeps the mail unread until we've stored it.
            typ, parts = conn.uid("fetch", uid, "(BODY.PEEK[])")
            raw = next(
                (p[1] for p in parts or [] if isinstance(p, tuple) and len(p) > 1), None
            )
            if typ != "OK" or not raw:
                out["failed"] += 1
                continue
            try:
                res = ingest_inbound_email(db, settings, parse_rfc822(raw))
            except Exception:
                db.rollback()
                logger.exception("lead_inbound_email_failed uid=%s", uid)
                out["failed"] += 1
                continue
            out["ingested" if res["status"] == "ingested" else "skipped"] += 1
            conn.uid("store", uid, "+FLAGS", "(\\Seen)")
    finally:
        try:
            conn.logout()
        except Exception:  # noqa: BLE001
            pass
    return out


__all__ = [
    "InboundEmail",
    "imap_configured",
    "ingest_inbound_email",
    "parse_rfc822",
    "poll_imap_once",
    "should_skip",
    "strip_quoted",
]
