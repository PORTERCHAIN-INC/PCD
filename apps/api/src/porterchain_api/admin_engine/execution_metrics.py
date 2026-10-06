"""§5.3 business metrics — orders/week, deploy frequency policy (dev instrumentation)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order

ORDERS_PER_WEEK_TARGET = 50
DEPLOY_FREQUENCY_TARGET_PER_WEEK = 2


def assess_orders_per_week(db: Session, *, window_days: int = 7) -> dict:
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    count = (
        db.query(Order)
        .filter(Order.is_sandbox.is_(False), Order.created_at >= cutoff)
        .count()
    )
    return {
        "window_days": window_days,
        "orders_last_7d": count,
        "target_per_week": ORDERS_PER_WEEK_TARGET,
        "meets_target": count >= ORDERS_PER_WEEK_TARGET,
        "scope": "production_growth",
    }


def assess_deploy_frequency_policy() -> dict:
    """Deploy cadence is measured via GitHub Actions; policy is enforced in deploy.yml."""
    return {
        "target_per_week": DEPLOY_FREQUENCY_TARGET_PER_WEEK,
        "triggers": [
            "workflow_run: CI success on main (scope=full)",
            "workflow_dispatch: manual deploy (scope=full|website)",
        ],
        "workflow_file": ".github/workflows/deploy.yml",
        "tracking": "GitHub Actions → Deploy workflow → filter last 7 days (≥2 runs)",
        "rollback_doc": "infrastructure/deploy/README.md § Rolling deploy / rollback",
    }


def build_execution_metrics_dashboard(db: Session, settings) -> dict:
    del settings
    from porterchain_api.admin_engine.business_metrics import assess_business_metrics
    from porterchain_api.merchant_engine.webhook_delivery_health import assess_merchant_webhook_delivery

    business = assess_business_metrics(db)
    return {
        "orders": assess_orders_per_week(db),
        "deploy_frequency": assess_deploy_frequency_policy(),
        "dispatch": {"status": "porterchain", "engine": "ortools", "ok": True},
        "merchant_webhook_delivery": assess_merchant_webhook_delivery(db),
        "auto_dispatch": business["auto_dispatch"],
        "on_time_delivery": business["on_time_delivery"],
        "support_first_response": business["support_first_response"],
        "business_alerts": business.get("alerts", []),
    }
