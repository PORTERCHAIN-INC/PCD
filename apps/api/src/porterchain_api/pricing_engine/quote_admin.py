"""Sent quotes (§9.3), per-order adjustments (§9.4) and the public quote view/accept.

DB access for ``routers/pricing_quotes.py``; errors raise ``PricingAdminError``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from porterchain_api.pricing_engine.models import PricingAudit, PricingOrderAdjustment, PricingSentQuote
from porterchain_api.pricing_engine.rate_card_admin import PricingAdminError, audit, org_pricing_obj
from porterchain_pricing.standard_card import Item, ManualQuoteRequired, quote


def sent_out(row: Any) -> dict[str, Any]:
    from porterchain_api.pricing_engine.quote_send import quote_state

    return {
        "id": row.id,
        "token": row.token,
        "email": row.email,
        "org_id": row.org_id,
        "lead_id": row.lead_id,
        "total_cents": row.total_cents,
        "status": quote_state(row),
        "card_version": row.card_version,
        "expires_at": row.expires_at.isoformat(),
        "quote": row.payload,
    }


def send_quote(db: Session, actor_id: str | None, body: Any, items: list[Item]) -> dict[str, Any]:
    """Price on the published card, store it for 72 h and email the link (no booking, no invoice)."""
    from porterchain_api.config import get_settings
    from porterchain_api.pricing_engine.quote_send import create_sent_quote, deliver_quote_email
    from porterchain_api.pricing_engine.standard_live import published_lines as live_lines

    lines, version = live_lines(db)
    org = org_pricing_obj(db, body.org_id)
    try:
        q = quote(items, body.zone, add_ons=body.add_ons, audience=body.audience, lines=lines, org=org, stops=body.stops)
    except ManualQuoteRequired as exc:
        raise PricingAdminError(422, f"manual_quote:{exc}") from exc
    except ValueError as exc:
        raise PricingAdminError(422, str(exc)) from exc
    row = create_sent_quote(
        db,
        email=body.email,
        payload=q,
        audience=body.audience,
        card_version=version,
        org_id=body.org_id,
        lead_id=body.lead_id,
        actor_id=actor_id,
    )
    audit(
        db,
        actor_id,
        "sent_quote",
        row.id,
        "send",
        {"total_cents": row.total_cents, "email_domain": body.email.split("@")[-1]},
    )
    link = f"{get_settings().customer_portal_url.rstrip('/')}/quote/{row.token}"
    delivery = deliver_quote_email(db, row, link)
    db.commit()
    return sent_out(row) | {"link": link, "delivery": delivery}


def list_sent_quotes(db: Session, org_id: str | None, lead_id: str | None) -> dict[str, Any]:
    stmt = select(PricingSentQuote).order_by(PricingSentQuote.created_at.desc()).limit(200)
    if org_id:
        stmt = stmt.where(PricingSentQuote.org_id == org_id)
    if lead_id:
        stmt = stmt.where(PricingSentQuote.lead_id == lead_id)
    return {"items": [sent_out(r) for r in db.scalars(stmt)]}


def void_sent_quote(db: Session, actor_id: str | None, quote_id: str) -> dict[str, Any]:
    row = db.get(PricingSentQuote, quote_id)
    if row is None:
        raise PricingAdminError(404, "quote_not_found")
    row.status = "void"
    audit(db, actor_id, "sent_quote", row.id, "void", None)
    db.commit()
    return sent_out(row)


def list_adjustments(db: Session, order_id: str, role_key: str) -> dict[str, Any]:
    from porterchain_api.booking_models import Order
    from porterchain_api.pricing_engine.quote_send import ADJUST_CATEGORIES, ADJUST_LIMITS, adjustments_total

    order = db.get(Order, order_id)
    if order is None:
        raise PricingAdminError(404, "order_not_found")
    rows = db.scalars(
        select(PricingOrderAdjustment)
        .where(PricingOrderAdjustment.order_id == order_id)
        .order_by(PricingOrderAdjustment.created_at)
    )
    adj = adjustments_total(db, order_id)
    cap, pct = ADJUST_LIMITS[role_key]
    allowed = int(order.amount_cents or 0) * pct // 100
    return {
        "order_amount_cents": int(order.amount_cents or 0),
        "adjustments_cents": adj,
        "adjusted_total_cents": int(order.amount_cents or 0) + adj,
        "limit_cents": min(allowed, cap) if cap is not None else allowed,
        "categories": list(ADJUST_CATEGORIES),
        "items": [
            {
                "id": r.id,
                "cents": r.cents,
                "category": r.category,
                "reason": r.reason,
                "actor_role": r.actor_role,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


def create_adjustment(
    db: Session, actor_id: str | None, role_key: str, order_id: str, cents: int, category: str, reason: str
) -> dict[str, Any]:
    from porterchain_api.booking_models import Order
    from porterchain_api.pricing_engine.quote_send import AdjustmentRefused, add_adjustment

    order = db.get(Order, order_id)
    if order is None:
        raise PricingAdminError(404, "order_not_found")
    try:
        row = add_adjustment(
            db, order=order, cents=cents, category=category, reason=reason, role=role_key, actor_id=actor_id
        )
    except AdjustmentRefused as exc:  # refused before anything was written
        raise PricingAdminError(422, str(exc)) from exc
    audit(db, actor_id, "order_adjustment", order_id, "adjust", {"cents": cents, "category": category}, reason)
    db.commit()
    return list_adjustments(db, order_id, role_key) | {"created_id": row.id}


def public_quote(db: Session, token: str) -> dict[str, Any]:
    from porterchain_api.pricing_engine.quote_send import quote_state

    row = db.scalar(select(PricingSentQuote).where(PricingSentQuote.token == token))
    if row is None:
        raise PricingAdminError(404, "quote_not_found")
    state = quote_state(row)
    if state in ("expired", "void"):
        raise PricingAdminError(410, f"quote_{state}")
    return {
        "status": state,
        "total_cents": row.total_cents,
        "expires_at": row.expires_at.isoformat(),
        "lines": row.payload.get("lines", []),
        "hst_cents": row.payload.get("hst_cents"),
        "subtotal_cents": row.payload.get("subtotal_cents"),
        "zone_label": row.payload.get("zone_label"),
    }


def accept_public_quote(db: Session, token: str) -> dict[str, Any]:
    from porterchain_api.pricing_engine.quote_send import quote_state

    row = db.scalar(select(PricingSentQuote).where(PricingSentQuote.token == token))
    if row is None:
        raise PricingAdminError(404, "quote_not_found")
    state = quote_state(row)
    if state != "sent" and state != "accepted":
        raise PricingAdminError(410, f"quote_{state}")
    if state == "sent":
        row.status = "accepted"
        row.accepted_at = datetime.now(UTC)
        db.add(PricingAudit(entity="sent_quote", entity_id=row.id, action="accept", diff=None))
        db.commit()
    return {"status": "accepted", "total_cents": row.total_cents}
