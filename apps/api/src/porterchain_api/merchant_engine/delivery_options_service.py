"""Merchant-side delivery options: account default + per-order edit (incl. Shopify orders)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.domain import delivery_options as dopts
from porterchain_api.merchant_models import MerchantAuditLog


class DeliveryOptionsError(ValueError):
    pass


def _audit(db: Session, ctx: Any, action: str, resource_type: str, resource_id: str, payload: dict) -> None:
    db.add(MerchantAuditLog(merchant_id=ctx.merchant.id, actor_user_id=ctx.user.id, action=action,
                            resource_type=resource_type, resource_id=resource_id, payload=payload))


def get_default(ctx: Any) -> dict[str, Any]:
    return dopts.merchant_default(ctx.merchant) or {}


def set_default(db: Session, ctx: Any, raw: dict[str, Any] | None) -> dict[str, Any]:
    clean = dopts.normalize(raw) or {}
    profile = dict(ctx.merchant.profile or {})
    settings = dict(profile.get("settings") or {})
    if clean:
        settings[dopts.DEFAULTS_SETTING] = clean
    else:
        settings.pop(dopts.DEFAULTS_SETTING, None)
    profile["settings"] = settings
    ctx.merchant.profile = profile
    _audit(db, ctx, "settings.delivery_defaults", "settings", ctx.merchant.id, clean)
    db.commit()
    return clean


def _own_order(db: Session, ctx: Any, order_id: str) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.merchant_id != ctx.merchant.id:
        raise DeliveryOptionsError("order_not_found")
    return order


def update_order(db: Session, ctx: Any, order_id: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    """Change one order's options until it is delivered/cancelled. The driver app and the next
    label print read them from the order, so no re-dispatch is needed."""
    order = _own_order(db, ctx, order_id)
    if str(order.state).upper() not in dopts.EDITABLE_STATES:
        raise DeliveryOptionsError("order_not_editable")
    before = dopts.of(order.dropoff)
    order.dropoff = dopts.apply(dict(order.dropoff or {}), raw)
    after = dopts.of(order.dropoff)
    db.add(OrderEvent(order_id=order.id, event_type="order.delivery_options_updated", from_state=order.state,
                      to_state=order.state, payload={"before": before, "after": after, "by": "merchant"},
                      occurred_at=datetime.now(UTC)))
    _audit(db, ctx, "order.delivery_options", "order", order.id, after)
    db.commit()
    return {"order_id": order.id, "delivery_options": after, "summary": dopts.summary_lines(order.dropoff)}


def shopify_orders(db: Session, ctx: Any, *, limit: int = 50) -> list[dict[str, Any]]:
    """Recent Shopify-imported orders with their delivery options (Shopify page list)."""
    rows = (
        db.query(Order)
        .filter(Order.merchant_id == ctx.merchant.id, Order.order_source == "SHOPIFY")
        .order_by(Order.created_at.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )
    out = []
    for o in rows:
        shop = (o.compliance_metadata or {}).get("shopify") or {}
        out.append({
            "order_id": o.id,
            "order_number": o.order_number,
            "tracking_number": o.tracking_number,
            "shopify_order_name": shop.get("order_name") if isinstance(shop, dict) else None,
            "state": o.state,
            "dropoff": (o.dropoff or {}).get("formatted"),
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "delivery_options": dopts.of(o.dropoff),
            "editable": str(o.state).upper() in dopts.EDITABLE_STATES,
        })
    return out
