"""§8.3 — switching-cost signals (integrations, SLA history, tariffs, RBAC audit)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import MerchantContract, PricingTariff
from porterchain_api.booking_engine.compliance_metadata import delivery_window_end
from porterchain_api.gateway_engine import merchant_api as gateway
from porterchain_api.merchant_engine.rbac import permissions_catalog
from porterchain_api.merchant_models import Merchant, MerchantApiKey, MerchantAuditLog, MerchantWebhook
from porterchain_api.models import Order, OrderEvent

ON_TIME_GRACE_MINUTES = 30


def _month_bounds(offset_months: int, *, reference: datetime | None = None) -> tuple[datetime, datetime, str]:
    ref = (reference or datetime.now(UTC)).replace(tzinfo=None)
    year = ref.year
    month = ref.month - offset_months
    while month <= 0:
        month += 12
        year -= 1
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end, start.strftime("%b %Y")


def integration_depth(db: Session, merchant_id: str) -> dict[str, Any]:
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise LookupError("merchant_not_found")
    keys = (
        db.query(MerchantApiKey)
        .filter(MerchantApiKey.merchant_id == merchant_id, MerchantApiKey.is_active.is_(True))
        .count()
    )
    webhooks = (
        db.query(MerchantWebhook)
        .filter(MerchantWebhook.merchant_id == merchant_id, MerchantWebhook.is_active.is_(True))
        .count()
    )
    profile = merchant.profile if isinstance(merchant.profile, dict) else {}
    integrations = profile.get("integrations") if isinstance(profile.get("integrations"), dict) else {}
    oauth_connections = sum(
        1
        for key, value in integrations.items()
        if key.endswith("_connected") and value is True
    )
    erp_connections = sum(
        1
        for key, value in integrations.items()
        if key.startswith("erp_") and value not in (None, "", False)
    )
    channels = {
        "api_keys": int(keys),
        "webhooks": int(webhooks),
        "oauth_connections": oauth_connections,
        "erp_connections": erp_connections,
    }
    total = sum(channels.values())
    return {
        "merchant_id": merchant_id,
        "integration_channels": channels,
        "total_active_integrations": total,
        "meets_switching_threshold": total >= 3,
        "threshold": 3,
        "erp_platforms_ready": [p["id"] for p in gateway.ERP_READINESS if p["status"] == "ready"],
    }


def sla_history_12mo(db: Session, merchant_id: str) -> dict[str, Any]:
    from porterchain_api.order_engine.buckets import DONE_STATES

    grace = timedelta(minutes=ON_TIME_GRACE_MINUTES)
    labels: list[str] = []
    sla_series: list[float] = []
    on_time_series: list[int] = []
    delivered_series: list[int] = []

    for offset in range(11, -1, -1):
        start, end, label = _month_bounds(offset)
        labels.append(label)
        orders = (
            db.query(Order)
            .filter(
                Order.merchant_id == merchant_id,
                Order.created_at >= start,
                Order.created_at < end,
                Order.state.in_(DONE_STATES),
            )
            .all()
        )
        delivered = len(orders)
        on_time = 0
        for order in orders:
            event = (
                db.query(OrderEvent)
                .filter(OrderEvent.order_id == order.id, OrderEvent.event_type == "order.delivered")
                .order_by(OrderEvent.occurred_at.desc())
                .first()
            )
            delivered_at = event.occurred_at if event else order.updated_at
            if delivered_at and delivered_at.tzinfo is None:
                delivered_at = delivered_at.replace(tzinfo=UTC)
            target_end = delivery_window_end(order.compliance_metadata) or order.scheduled_at
            if target_end and target_end.tzinfo is None:
                target_end = target_end.replace(tzinfo=UTC)
            if not target_end or not delivered_at:
                on_time += 1
                continue
            if delivered_at <= target_end + grace:
                on_time += 1
        pct = round(on_time / delivered * 100, 1) if delivered else 100.0
        sla_series.append(pct)
        on_time_series.append(on_time)
        delivered_series.append(delivered)

    return {
        "merchant_id": merchant_id,
        "months": 12,
        "labels": labels,
        "sla_percent": sla_series,
        "on_time_orders": on_time_series,
        "delivered_orders": delivered_series,
        "rolling_avg_sla_percent": round(sum(sla_series) / len(sla_series), 1) if sla_series else 100.0,
    }


def custom_tariffs_summary(db: Session, *, merchant_id: str | None = None) -> dict[str, Any]:
    contract_q = db.query(MerchantContract).filter(MerchantContract.is_active.is_(True))
    tariff_q = db.query(PricingTariff).filter(PricingTariff.is_active.is_(True))
    if merchant_id:
        contract_q = contract_q.filter(MerchantContract.merchant_id == merchant_id)
        tariff_q = tariff_q.filter(
            (PricingTariff.merchant_id == merchant_id) | (PricingTariff.tariff_type == "merchant")
        )
    contracts = contract_q.count()
    tariffs = tariff_q.count()
    return {
        "merchant_id": merchant_id,
        "active_merchant_contracts": int(contracts),
        "active_custom_tariffs": int(tariffs),
        "custom_pricing_enabled": contracts > 0 or tariffs > 0,
        "admin_surface": "/v1/admin/pricing/contracts",
        "merchant_surface": "/v1/merchant/billing/contract",
    }


def rbac_and_audit_snapshot(db: Session, merchant_id: str, *, limit: int = 50) -> dict[str, Any]:
    logs = (
        db.query(MerchantAuditLog)
        .filter(MerchantAuditLog.merchant_id == merchant_id)
        .order_by(MerchantAuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "merchant_id": merchant_id,
        "rbac": permissions_catalog(),
        "audit_log_count": (
            db.query(func.count(MerchantAuditLog.id))
            .filter(MerchantAuditLog.merchant_id == merchant_id)
            .scalar()
            or 0
        ),
        "recent_audit_logs": [
            {
                "id": row.id,
                "action": row.action,
                "actor_user_id": row.actor_user_id,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "payload": row.payload,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in logs
        ],
    }
