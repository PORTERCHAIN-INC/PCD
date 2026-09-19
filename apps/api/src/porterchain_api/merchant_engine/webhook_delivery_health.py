"""Merchant outbound webhook delivery SLO (§5.3.7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

MERCHANT_WEBHOOK_DELIVERY_SLO_TARGET_PCT = 99.0
DEFAULT_WINDOW_DAYS = 7


def build_merchant_webhook_delivery_alerts(slo: dict) -> list[dict[str, str]]:
    if int(slo.get("total_deliveries") or 0) == 0:
        return []
    alerts: list[dict[str, str]] = []
    if not slo.get("meets_slo"):
        alerts.append(
            {
                "level": "critical",
                "code": "merchant_webhook_delivery_below_slo",
                "message": (
                    f"Delivery success {slo.get('success_pct')}% below SLO "
                    f"{slo.get('slo_target_pct')}% "
                    f"({slo.get('succeeded_deliveries')}/{slo.get('total_deliveries')} events)"
                ),
            }
        )
    failed = int(slo.get("failed_deliveries") or 0)
    if failed > 0:
        alerts.append(
            {
                "level": "warning",
                "code": "merchant_webhook_delivery_failures",
                "message": f"{failed} merchant webhook event(s) failed final delivery in window",
            }
        )
    return alerts


def assess_merchant_webhook_delivery(
    db: Session,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    merchant_id: str | None = None,
) -> dict:
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    merchant_filter = "AND merchant_id = :merchant_id" if merchant_id else ""
    row = db.execute(
        text(
            f"""
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE success)::int AS succeeded
            FROM (
                SELECT DISTINCT ON (
                    webhook_id,
                    event_type,
                    COALESCE(request_body->>'order_id', '')
                )
                    success
                FROM merchant_webhook_deliveries
                WHERE created_at >= :cutoff
                {merchant_filter}
                ORDER BY
                    webhook_id,
                    event_type,
                    COALESCE(request_body->>'order_id', ''),
                    attempt DESC
            ) finals
            """
        ),
        {"cutoff": cutoff, "merchant_id": merchant_id},
    ).one()

    total = int(row.total or 0)
    succeeded = int(row.succeeded or 0)
    failed = max(total - succeeded, 0)
    success_pct = 100.0 if total == 0 else round(succeeded / total * 100, 2)
    meets_slo = total == 0 or success_pct >= MERCHANT_WEBHOOK_DELIVERY_SLO_TARGET_PCT

    result = {
        "window_days": window_days,
        "total_deliveries": total,
        "succeeded_deliveries": succeeded,
        "failed_deliveries": failed,
        "success_pct": success_pct,
        "slo_target_pct": MERCHANT_WEBHOOK_DELIVERY_SLO_TARGET_PCT,
        "meets_slo": meets_slo,
    }
    result["alerts"] = build_merchant_webhook_delivery_alerts(result)
    return result
