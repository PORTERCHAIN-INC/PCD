"""Send a Standard-card quote (72 h validity) and per-order adjustments with limits."""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from porterchain_api.pricing_engine.models import PricingOrderAdjustment, PricingSentQuote

logger = logging.getLogger(__name__)

QUOTE_VALID_HOURS = 72
ADJUST_CATEGORIES = ("waiting", "extra_stop", "access", "damage_credit", "goodwill", "correction")
#: Role limits per adjustment: (absolute cap cents | None, % of order total).
ADJUST_LIMITS = {"admin": (5000, 20), "super_admin": (None, 50)}


class AdjustmentRefused(ValueError):
    pass


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def create_sent_quote(db: Session, *, email: str, payload: dict[str, Any], audience: str, card_version: int,
                      org_id: str | None = None, lead_id: str | None = None, actor_id: str | None = None,
                      now: datetime | None = None) -> PricingSentQuote:
    now = now or datetime.now(UTC)
    row = PricingSentQuote(
        token=secrets.token_urlsafe(24), email=email.strip().lower(), payload=payload, audience=audience,
        card_version=card_version, total_cents=int(payload["total_cents"]), org_id=org_id, lead_id=lead_id,
        expires_at=now + timedelta(hours=QUOTE_VALID_HOURS), created_by=actor_id,
    )
    db.add(row)
    db.flush()
    return row


def quote_state(row: PricingSentQuote, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    if row.status == "sent" and _aware(row.expires_at) <= now:
        return "expired"
    return row.status


def deliver_quote_email(db: Session, row: PricingSentQuote, link: str) -> dict[str, Any]:
    try:
        from porterchain_api.notification_engine.delivery_service import DeliveryService

        log = DeliveryService().deliver({
            "channel": "email", "template": "pricing_quote_sent", "recipient": row.email,
            "recipient_type": "lead", "recipient_id": row.lead_id or row.org_id or "",
            "context": {"quote_link": link, "total_cents": row.total_cents,
                        "total": f"${(row.total_cents or 0) / 100:,.2f}",
                        "expires_at": _aware(row.expires_at).isoformat(), "valid_hours": QUOTE_VALID_HOURS},
        })
        return {"sent": getattr(log, "status", "sent") in ("sent", "delivered", "queued")}
    except Exception:  # noqa: BLE001 - the quote stays valid; staff can copy the link
        logger.warning("quote email failed quote=%s", row.id, exc_info=True)
        return {"sent": False, "reason": "delivery_failed"}


def adjustments_total(db: Session, order_id: str) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(PricingOrderAdjustment.cents), 0))
                         .where(PricingOrderAdjustment.order_id == order_id)) or 0)


def add_adjustment(db: Session, *, order: Any, cents: int, category: str, reason: str, role: str,
                   actor_id: str | None) -> PricingOrderAdjustment:
    if category not in ADJUST_CATEGORIES:
        raise AdjustmentRefused("unknown_category")
    if len((reason or "").strip()) < 5:
        raise AdjustmentRefused("reason_required")
    if cents == 0:
        raise AdjustmentRefused("zero_adjustment")
    limits = ADJUST_LIMITS.get(role)
    if limits is None:
        raise AdjustmentRefused("role_not_allowed")
    cap, pct = limits
    total = int(order.amount_cents or 0)
    allowed = total * pct // 100
    if cap is not None:
        allowed = min(allowed, cap)
    if abs(cents) > allowed:
        raise AdjustmentRefused(f"over_limit:{allowed}")
    if total + adjustments_total(db, order.id) + cents < 0:
        raise AdjustmentRefused("below_zero")
    row = PricingOrderAdjustment(order_id=order.id, cents=int(cents), category=category, reason=reason.strip(),
                                 actor_id=actor_id, actor_role=role)
    db.add(row)
    db.flush()
    return row
