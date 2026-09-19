"""§9.2 — monopoly / network-effect metrics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant
from porterchain_api.booking_models import Order

ICP_GTA_BOUNDS = {
    "min_lat": 43.58,
    "max_lat": 43.78,
    "min_lng": -79.55,
    "max_lng": -79.25,
}
ICP_GEO_SHARE_TARGET = 40.0
GRID_PRECISION = 2


def _in_bounds(lat: float, lng: float, bounds: dict[str, float]) -> bool:
    return (
        bounds["min_lat"] <= lat <= bounds["max_lat"]
        and bounds["min_lng"] <= lng <= bounds["max_lng"]
    )


def _order_coords(order: Order) -> tuple[float, float] | None:
    dropoff = order.dropoff if isinstance(order.dropoff, dict) else {}
    lat, lng = dropoff.get("lat"), dropoff.get("lng")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def route_density_optimization(db: Session, *, window_days: int = 30) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    orders = db.query(Order).filter(Order.created_at >= cutoff).limit(5000).all()
    cells: dict[str, int] = {}
    for order in orders:
        coords = _order_coords(order)
        if not coords:
            continue
        lat, lng = coords
        key = f"{round(lat, GRID_PRECISION)}:{round(lng, GRID_PRECISION)}"
        cells[key] = cells.get(key, 0) + 1
    hotspots = sorted(
        [{"cell": k, "orders": v} for k, v in cells.items()],
        key=lambda row: row["orders"],
        reverse=True,
    )[:20]
    return {
        "window_days": window_days,
        "orders_with_coordinates": sum(cells.values()),
        "unique_cells": len(cells),
        "hotspots": hotspots,
        "recommendation": "Batch dispatch-ready orders in top cells before expanding driver pool.",
    }


def icp_geo_share(db: Session, *, window_days: int = 90) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    orders = db.query(Order).filter(Order.created_at >= cutoff).limit(5000).all()
    with_coords = 0
    in_icp = 0
    for order in orders:
        coords = _order_coords(order)
        if not coords:
            continue
        with_coords += 1
        if _in_bounds(coords[0], coords[1], ICP_GTA_BOUNDS):
            in_icp += 1
    pct = round(in_icp / with_coords * 100, 1) if with_coords else 0.0
    return {
        "window_days": window_days,
        "icp_region": "GTA core",
        "bounds": ICP_GTA_BOUNDS,
        "orders_with_coordinates": with_coords,
        "orders_in_icp": in_icp,
        "icp_geo_share_pct": pct,
        "target_pct": ICP_GEO_SHARE_TARGET,
        "meets_target": pct >= ICP_GEO_SHARE_TARGET,
    }


def white_label_adoption(db: Session) -> dict[str, Any]:
    merchants = db.query(Merchant).all()
    enabled = 0
    samples: list[dict[str, Any]] = []
    for merchant in merchants:
        profile = merchant.profile if isinstance(merchant.profile, dict) else {}
        settings = profile.get("settings") if isinstance(profile.get("settings"), dict) else {}
        branding = settings.get("branding") if isinstance(settings.get("branding"), dict) else {}
        if branding.get("white_label_enabled") or branding.get("logo_url"):
            enabled += 1
            if len(samples) < 10:
                samples.append(
                    {
                        "merchant_id": merchant.id,
                        "company_name": merchant.company_name,
                        "logo_url": branding.get("logo_url"),
                        "tracking_domain": branding.get("tracking_domain"),
                    }
                )
    return {
        "merchants_total": len(merchants),
        "white_label_enabled": enabled,
        "adoption_pct": round(enabled / len(merchants) * 100, 1) if merchants else 0.0,
        "samples": samples,
        "configure_via": "PATCH /v1/merchant/settings/branding",
        "docs": "docs/3PL_WHITE_LABEL.md",
    }


def carrier_pool_legal_model() -> dict[str, Any]:
    return {
        "model": "independent_contractor_carrier_pool",
        "merchant_relationship": "merchant_contracts_with_porterchain_platform",
        "driver_relationship": "porterchain_vetted_independent_operators",
        "docs": "docs/legal/CARRIER_POOL_MODEL.md",
        "fleetbase_boundary": "execution_dispatch_via_adapter_not_product_surface",
    }


def monopoly_snapshot(db: Session, *, window_days: int = 30) -> dict[str, Any]:
    return {
        "as_of": datetime.now(UTC).isoformat(),
        "route_density": route_density_optimization(db, window_days=window_days),
        "icp_geo_share": icp_geo_share(db, window_days=max(window_days, 90)),
        "white_label": white_label_adoption(db),
        "carrier_pool_legal": carrier_pool_legal_model(),
    }
