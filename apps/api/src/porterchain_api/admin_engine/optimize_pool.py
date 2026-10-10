"""Optimize pool view — eligible PorterChain orders plus why other stops are out."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.domain.sandbox import order_is_sandbox
from porterchain_api.domain.states import OrderSource
from porterchain_api.merchant_models import ShopifyShop

OPTIMIZE_STATES = frozenset(
    {"BOOKED", "DISPATCH_READY", "DRIVER_REJECTED", "FAILED", "DRIVER_ASSIGNED", "DRIVER_ACCEPTED"}
)
SCAN_CAP = 400


def build_optimize_pool(
    db: Session,
    *,
    limit: int,
    offset: int,
    vehicle_ids: list[str],
    driver_ids: list[str],
) -> dict[str, Any]:
    """Return one page of day-plan-eligible orders and counts for the rest."""
    paused_merchants = {
        row[0]
        for row in db.query(ShopifyShop.merchant_id).filter(ShopifyShop.ingress_paused.is_(True)).all()
    }
    candidates = (
        db.query(Order)
        .filter(Order.state.in_(OPTIMIZE_STATES))
        .order_by(Order.scheduled_at.asc())
        .limit(SCAN_CAP)
        .all()
    )
    sandbox = 0
    paused = 0
    no_coords = 0
    eligible: list[Order] = []
    for order in candidates:
        if order.order_source == OrderSource.SHOPIFY.value and order.merchant_id in paused_merchants:
            paused += 1
            continue
        if order_is_sandbox(order):
            sandbox += 1
            continue
        if not _has_coords(order):
            no_coords += 1
            continue
        eligible.append(order)

    start = max(0, offset)
    page = eligible[start : start + limit]
    merchant_counts: dict[str, int] = {}
    for order in page:
        mid = order.merchant_id or "_none"
        merchant_counts[mid] = merchant_counts.get(mid, 0) + 1
    return {
        "order_count": len(page),
        "eligible_count": len(eligible),
        "synced_count": len(page),
        "preview_cap": limit,
        "offset": start,
        "remaining_after_page": max(0, len(eligible) - start - len(page)),
        "placeholder_skipped": 0,
        "excluded": {
            "missing_coords": no_coords,
            "sandbox": sandbox,
            "shopify_ingress_paused": paused,
        },
        "merchants": [
            {"merchant_id": mid if mid != "_none" else None, "order_count": count}
            for mid, count in sorted(merchant_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "vehicle_ids": vehicle_ids,
        "driver_ids": driver_ids,
        "orders": [
            {
                "id": order.id,
                "tracking_number": order.tracking_number,
                "state": order.state,
                "order_source": order.order_source,
                "assigned_driver_id": getattr(order, "assigned_driver_id", None),
                "scheduled_at": order.scheduled_at.isoformat() if order.scheduled_at else None,
                "merchant_id": order.merchant_id,
                # Order has no weight column — total the package weights (was an AttributeError 500).
                "weight_kg": sum(float(p.weight_kg or 0) for p in (order.packages or [])) or None,
            }
            for order in page
        ],
    }


def _has_coords(order: Order) -> bool:
    for addr in (order.pickup, order.dropoff):
        if not isinstance(addr, dict):
            continue
        lat = addr.get("lat") if addr.get("lat") is not None else addr.get("latitude")
        lng = addr.get("lng") if addr.get("lng") is not None else addr.get("lon") or addr.get("longitude")
        if lat is not None and lng is not None:
            return True
    return False
