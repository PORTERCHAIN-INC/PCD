"""Newsletter subscribers — double opt-in list kept apart from sales leads.

Flow: subscribe → ``pending`` + confirmation email (one-time token) →
``confirmed`` on click. Only ``confirmed`` subscribers count as CASL express
consent. Re-subscribing a confirmed address is a no-op (no extra email).
"""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.lead_consent import form_consent_evidence
from porterchain_api.crm_models import MarketingSubscriber

logger = logging.getLogger(__name__)

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
CONFIRM_TTL = timedelta(days=7)
RESEND_COOLDOWN = timedelta(minutes=10)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def subscribe(
    db: Session,
    *,
    email: str,
    website_url: str,
    source: str = "website_newsletter",
    source_page: str | None = None,
    locale: str | None = None,
    ip: str | None = None,
    attribution: dict[str, Any] | None = None,
    send_email: bool = True,
) -> MarketingSubscriber:
    """Create or refresh a pending subscriber and send the confirmation email."""
    addr = (email or "").strip().lower()
    if not _EMAIL.match(addr):
        raise ValueError("email_invalid")
    row = db.query(MarketingSubscriber).filter(MarketingSubscriber.email == addr).first()
    now = _now()
    if row and row.status == "confirmed":
        return row
    if row is None:
        row = MarketingSubscriber(email=addr, status="pending")
        db.add(row)
    elif row.confirm_sent_at and now - _aware(row.confirm_sent_at) < RESEND_COOLDOWN:  # type: ignore[operator]
        # Don't let anyone spam an inbox with confirmation emails.
        return row
    row.status = "pending"
    row.source = source[:64]
    row.source_page = (source_page or "")[:512] or None
    row.locale = "fr" if (locale or "").lower().startswith("fr") else "en"
    row.attribution = {k: v for k, v in (attribution or {}).items() if v}
    # Pending request evidence; becomes consent only on confirmation.
    row.consent = {
        **form_consent_evidence(
            marketing=False, source=source, ip=ip, locale=row.locale, page=source_page
        ),
        "requested": True,
    }
    token = secrets.token_urlsafe(32)
    row.confirm_token_hash = _hash(token)
    row.confirm_sent_at = now
    row.unsubscribed_at = None
    db.flush()
    if send_email:
        _send_confirm(db, row, token=token, website_url=website_url)
    db.commit()
    db.refresh(row)
    return row


def _send_confirm(db: Session, row: MarketingSubscriber, *, token: str, website_url: str) -> None:
    base = (website_url or "https://porterchain.com").rstrip("/")
    loc = row.locale or "en"
    confirm_url = f"{base}/{loc}/newsletter/confirm?token={token}"
    try:
        from porterchain_api.platform.bus import publish_domain_event
        from porterchain_shared.events.catalog import DomainEventType

        publish_domain_event(
            event_type=DomainEventType.NEWSLETTER_CONFIRM_REQUESTED.value,
            aggregate_type="marketing_subscriber",
            aggregate_id=row.id,
            correlation_id=row.id,
            payload={"subscriber_id": row.id, "email": row.email, "confirm_url": confirm_url},
        )
    except Exception:
        logger.exception("newsletter_confirm_send_failed subscriber=%s", row.id)


def confirm(db: Session, *, token: str, ip: str | None = None) -> MarketingSubscriber | None:
    token = (token or "").strip()
    if len(token) < 16:
        return None
    row = (
        db.query(MarketingSubscriber)
        .filter(MarketingSubscriber.confirm_token_hash == _hash(token))
        .first()
    )
    if row is None:
        return None
    sent = _aware(row.confirm_sent_at)
    if sent and _now() - sent > CONFIRM_TTL:
        return None
    now = _now()
    row.status = "confirmed"
    row.confirmed_at = now
    row.confirm_token_hash = None
    evidence = form_consent_evidence(
        marketing=True,
        source=row.source or "website_newsletter",
        ip=ip,
        locale=row.locale,
        page=row.source_page,
    )
    evidence["method"] = "double_opt_in"
    evidence["requested_at"] = (row.consent or {}).get("captured_at")
    row.consent = evidence
    from porterchain_api.collaboration_engine.lead_suppression import clear_suppression

    clear_suppression(db, email=row.email, phone=None)
    db.commit()
    db.refresh(row)
    return row


def unsubscribe(db: Session, *, email: str) -> bool:
    addr = (email or "").strip().lower()
    row = db.query(MarketingSubscriber).filter(MarketingSubscriber.email == addr).first()
    if row is None:
        return False
    row.status = "unsubscribed"
    row.unsubscribed_at = _now()
    row.confirm_token_hash = None
    row.consent = {**(row.consent or {}), "marketing": False, "source": "unsubscribe"}
    db.commit()
    return True


__all__ = ["confirm", "subscribe", "unsubscribe"]
