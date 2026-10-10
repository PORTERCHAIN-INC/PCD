"""§7.3 — platform adoption metrics (counts vs Series A targets)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.domain.states import OrderSource
from porterchain_api.merchant_models import Merchant, MerchantApiKey, MerchantWebhookDelivery
from porterchain_api.booking_models import Order

TARGETS = {
    "active_api_keys": 10,
    "webhook_deliveries_per_day": 500,
    "partner_logos_on_site": 3,
    "oauth_apps": 1,
    "gmv_via_api_pct": 25.0,
}


def _oauth_app_count(db: Session) -> int:
    total = 0
    for merchant in db.query(Merchant).all():
        profile = merchant.profile if isinstance(merchant.profile, dict) else {}
        integrations = profile.get("integrations") if isinstance(profile.get("integrations"), dict) else {}
        clients = integrations.get("oauth_clients") or []
        if isinstance(clients, list):
            total += len(clients)
    return total


def _partner_logo_count() -> int:
    partners_file = (
        __import__("pathlib").Path(__file__).resolve().parents[5]
        / "website"
        / "src"
        / "content"
        / "partners.json"
    )
    if not partners_file.is_file():
        return 0
    import json

    data = json.loads(partners_file.read_text(encoding="utf-8"))
    logos = data.get("logos") or data.get("partners") or []
    return len(logos) if isinstance(logos, list) else 0


def platform_metrics(db: Session) -> dict[str, Any]:
    since_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    active_keys = (
        db.query(func.count(MerchantApiKey.id))
        .filter(MerchantApiKey.is_active.is_(True))
        .scalar()
        or 0
    )
    webhook_today = (
        db.query(func.count(MerchantWebhookDelivery.id))
        .filter(MerchantWebhookDelivery.created_at >= since_day)
        .scalar()
        or 0
    )
    oauth_apps = _oauth_app_count(db)
    partner_logos = _partner_logo_count()

    window = datetime.now(UTC) - timedelta(days=30)
    live = Order.is_sandbox.is_(False)
    total_orders = (
        db.query(func.count(Order.id)).filter(live, Order.created_at >= window).scalar() or 0
    )
    api_orders = (
        db.query(func.count(Order.id))
        .filter(
            live,
            Order.created_at >= window,
            Order.order_source.in_((OrderSource.MERCHANT.value, OrderSource.API.value)),
        )
        .scalar()
        or 0
    )
    gmv_pct = round(api_orders / total_orders * 100, 1) if total_orders else 0.0

    metrics = {
        "active_api_keys": {
            "value": int(active_keys),
            "target": TARGETS["active_api_keys"],
            "meets_target": active_keys >= TARGETS["active_api_keys"],
        },
        "webhook_deliveries_today": {
            "value": int(webhook_today),
            "target": TARGETS["webhook_deliveries_per_day"],
            "meets_target": webhook_today >= TARGETS["webhook_deliveries_per_day"],
        },
        "partner_logos_on_site": {
            "value": partner_logos,
            "target": TARGETS["partner_logos_on_site"],
            "meets_target": partner_logos >= TARGETS["partner_logos_on_site"],
        },
        "oauth_apps": {
            "value": oauth_apps,
            "target": TARGETS["oauth_apps"],
            "meets_target": oauth_apps >= TARGETS["oauth_apps"],
        },
        "gmv_via_api_pct": {
            "value": gmv_pct,
            "target": TARGETS["gmv_via_api_pct"],
            "meets_target": gmv_pct >= TARGETS["gmv_via_api_pct"],
            "window_days": 30,
            "api_orders": int(api_orders),
            "total_orders": int(total_orders),
        },
    }
    return {
        "as_of": datetime.now(UTC).isoformat(),
        "metrics": metrics,
        "all_targets_met": all(block["meets_target"] for block in metrics.values()),
    }


class PlatformMetricsService:
    def snapshot(self, db: Session) -> dict[str, Any]:
        return platform_metrics(db)
