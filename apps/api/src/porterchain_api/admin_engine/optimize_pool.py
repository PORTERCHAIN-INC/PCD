"""Optimize pool view — eligible Fleetbase ids plus why other stops are out."""

from __future__ import annotations

from collections.abc import Callable
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
    is_live_id: Callable[[str | None], bool],
) -> dict[str, Any]:
    """Return one page of solver-eligible orders and counts for the rest."""
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
    missing_fleetbase = 0
    sandbox = 0
    paused = 0
    eligible: list[Order] = []
    for order in candidates:
        if order.order_source == OrderSource.SHOPIFY.value and order.merchant_id in paused_merchants:
            paused += 1
            continue
        if order_is_sandbox(order):
            sandbox += 1
            continue
        if not is_live_id(order.fleetbase_order_id):
            missing_fleetbase += 1
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
        "placeholder_skipped": missing_fleetbase,
        "excluded": {
            "missing_fleetbase_id": missing_fleetbase,
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
                "fleetbase_order_id": order.fleetbase_order_id,
                "scheduled_at": order.scheduled_at.isoformat() if order.scheduled_at else None,
                "merchant_id": order.merchant_id,
                "weight_kg": float(order.weight_kg) if order.weight_kg is not None else None,
            }
            for order in page
        ],
    }
