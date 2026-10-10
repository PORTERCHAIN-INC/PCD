"""Execution metrics tests (§5.3.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.execution_metrics import (
    DEPLOY_FREQUENCY_TARGET_PER_WEEK,
    ORDERS_PER_WEEK_TARGET,
    assess_deploy_frequency_policy,
    assess_orders_per_week,
    build_execution_metrics_dashboard,
)
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState


def _seed_order(db: Session) -> None:
    addr = {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}
    db.add(
        Order(
            id=str(uuid4()),
            order_number=generate_order_number(),
            tracking_number=generate_tracking_number(),
            state=OrderState.DISPATCH_READY.value,
            amount_cents=3200,
            currency="cad",
            pickup=addr,
            dropoff=addr,
            scheduled_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
    )


def test_assess_orders_per_week_structure(db: Session) -> None:
    result = assess_orders_per_week(db, window_days=7)
    assert result["target_per_week"] == ORDERS_PER_WEEK_TARGET
    assert isinstance(result["orders_last_7d"], int)
    assert isinstance(result["meets_target"], bool)


def test_assess_orders_per_week_counts_recent(db: Session) -> None:
    before = assess_orders_per_week(db, window_days=7)["orders_last_7d"]
    _seed_order(db)
    db.commit()
    after = assess_orders_per_week(db, window_days=7)["orders_last_7d"]
    assert after == before + 1


def test_assess_deploy_frequency_policy() -> None:
    policy = assess_deploy_frequency_policy()
    assert policy["target_per_week"] == DEPLOY_FREQUENCY_TARGET_PER_WEEK
    assert "deploy.yml" in policy["workflow_file"]


def test_build_execution_metrics_dashboard(db: Session, settings: Settings) -> None:
    dashboard = build_execution_metrics_dashboard(db, settings)
    assert "orders" in dashboard
    assert "deploy_frequency" in dashboard
    assert "dispatch" in dashboard
    assert dashboard["dispatch"].get("engine") == "ortools"
    assert "merchant_webhook_delivery" in dashboard
    assert "auto_dispatch" in dashboard
    assert "on_time_delivery" in dashboard
    assert "support_first_response" in dashboard
