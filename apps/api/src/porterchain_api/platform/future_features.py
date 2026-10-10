"""Settings → Future: scoped capabilities to switch on once volume justifies them.

Every toggle is OFF by default and gated by a parcels/day threshold. Turning one on
records intent only; nothing ships behind these flags until it is built and reviewed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

STORAGE_KEY = "future_features"

CATALOG: list[dict[str, Any]] = [
    # AI / ML
    {"id": "ml_eta", "group": "AI / ML", "threshold": 500, "title": "Learned ETA",
     "description": "Gradient-boosted correction on Valhalla ETAs from our own stop/arrival history (needs ~50k stops)."},
    {"id": "ml_demand_forecast", "group": "AI / ML", "threshold": 500, "title": "Demand forecast model",
     "description": "Replace the weekday-average FSA forecast with a seasonal model (holidays, weather, merchant promos)."},
    {"id": "dynamic_pricing", "group": "AI / ML", "threshold": 500, "title": "Dynamic pricing",
     "description": "Price nudges by FSA/time slot from fill and demand, inside the cost floor and contract caps."},
    {"id": "auto_dispatch_ml", "group": "AI / ML", "threshold": 500, "title": "Learned dispatch scoring",
     "description": "Rank drivers with a model trained on acceptance, lateness and failed deliveries."},
    {"id": "failed_delivery_risk", "group": "AI / ML", "threshold": 500, "title": "Failed-delivery risk",
     "description": "Flag stops likely to fail (address quality, time window, history) before the route goes out."},
    {"id": "address_ml", "group": "AI / ML", "threshold": 500, "title": "Address quality model",
     "description": "Learn unit/buzzer/entrance hints per building from driver notes and POD."},
    {"id": "vroom_solver", "group": "Routing", "threshold": 500, "title": "VROOM solver",
     "description": "Self-hosted VROOM for plans over ~120 stops (benchmark: 1–19% better, 10–150x faster than OR-Tools 3s)."},
    # Integrations
    {"id": "woocommerce", "group": "Integrations", "threshold": 500, "title": "WooCommerce app",
     "description": "Checkout rates and order sync for WooCommerce merchants, same 4-click flow as Shopify."},
    {"id": "bigcommerce", "group": "Integrations", "threshold": 500, "title": "BigCommerce app",
     "description": "Carrier rates and order import for BigCommerce stores."},
    {"id": "accounting_sync", "group": "Integrations", "threshold": 500, "title": "QuickBooks / Xero sync",
     "description": "Push invoices, payments and driver payouts to accounting automatically."},
    {"id": "sms_two_way", "group": "Integrations", "threshold": 500, "title": "Two-way customer SMS",
     "description": "Customers reply to reschedule or leave instructions; replies land in Support."},
    {"id": "telematics", "group": "Integrations", "threshold": 500, "title": "Vehicle telematics",
     "description": "Import GPS, odometer and fuel from fleet devices instead of the driver phone."},
]
_IDS = {f["id"] for f in CATALOG}


def default_future() -> dict[str, bool]:
    return {f["id"]: False for f in CATALOG}


def normalize_future(raw: Any) -> dict[str, bool]:
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("future_features must be an object")
    out = default_future()
    for k, v in (raw or {}).items():
        if k not in _IDS:
            raise ValueError(f"unknown_future_feature:{k}")
        out[k] = bool(v)
    return out


def parcels_per_day(db: Any, *, days: int = 14, now: datetime | None = None) -> float:
    from porterchain_api.booking_models import Order

    now = now or datetime.now(UTC)
    n = (
        db.query(Order)
        .filter(Order.is_sandbox.is_(False), Order.scheduled_at >= now - timedelta(days=days), Order.scheduled_at <= now)
        .count()
    )
    return round(n / days, 1)


def future_overview(db: Any) -> dict[str, Any]:
    from porterchain_api.admin_models import SystemConfig

    row = db.get(SystemConfig, STORAGE_KEY)
    state = normalize_future(row.value if row else None)
    volume = parcels_per_day(db)
    return {
        "parcels_per_day": volume,
        "features": [{**f, "enabled": state[f["id"]], "ready": volume >= f["threshold"]} for f in CATALOG],
    }
