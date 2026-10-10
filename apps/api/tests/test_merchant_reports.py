"""Honest merchant reports — no fake 100% SLA, real order export."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.reporting_metrics import (
    delivery_performance,
    order_export_rows,
)
from porterchain_api.merchant_engine.reports_service import MerchantReportsService
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.reporting.switching_costs import sla_history_12mo


def _addr() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


def _merchant_ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Report Co {suffix}",
        email=f"report-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"user-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def _order(db, merchant_id: str, *, state: str, scheduled_at: datetime) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state,
        merchant_id=merchant_id,
        amount_cents=2500,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=scheduled_at,
    )
    db.add(order)
    db.flush()
    return order


def test_empty_merchant_percents_are_blank_not_100(db):
    ctx = _merchant_ctx(db)
    db.commit()
    perf = delivery_performance(db, ctx.merchant.id)
    assert perf["total_orders"] == 0
    assert perf["on_time_percent"] is None
    assert perf["delivery_success_percent"] is None
    assert perf["sla_percent"] is None
    assert perf["on_time_sample_size"] == 0

    history = sla_history_12mo(db, ctx.merchant.id)
    assert history["rolling_avg_sla_percent"] == 0.0
    assert all(pct == 0.0 for pct in history["sla_percent"])


def test_on_time_requires_delivered_event(db):
    ctx = _merchant_ctx(db)
    promised = datetime.now(UTC) + timedelta(hours=2)
    done = _order(db, ctx.merchant.id, state=OrderState.DELIVERED.value, scheduled_at=promised)
    late = _order(db, ctx.merchant.id, state=OrderState.DELIVERED.value, scheduled_at=promised)
    _order(db, ctx.merchant.id, state=OrderState.DELIVERED.value, scheduled_at=promised)
    db.add(
        OrderEvent(
            order_id=done.id,
            event_type="order.delivered",
            to_state=OrderState.DELIVERED.value,
            occurred_at=promised - timedelta(minutes=10),
        )
    )
    db.add(
        OrderEvent(
            order_id=late.id,
            event_type="order.delivered",
            to_state=OrderState.DELIVERED.value,
            occurred_at=promised + timedelta(hours=2),
        )
    )
    db.commit()

    perf = delivery_performance(db, ctx.merchant.id)
    assert perf["delivered"] == 3
    assert perf["on_time_sample_size"] == 2
    assert perf["on_time_orders"] == 1
    assert perf["on_time_percent"] == 50.0
    assert perf["delivery_success_percent"] == 100.0


def test_order_export_is_orders_not_routes(db):
    ctx = _merchant_ctx(db)
    order = _order(db, ctx.merchant.id, state=OrderState.BOOKED.value, scheduled_at=datetime.now(UTC))
    db.commit()
    rows = order_export_rows(db, ctx.merchant.id)
    assert rows[0]["order_number"] == order.order_number
    assert rows[0]["tracking_number"] == order.tracking_number

    csv_text = MerchantReportsService().export_csv(db, ctx, "orders")
    assert order.order_number in csv_text
    assert "route" not in csv_text.splitlines()[0]


def test_overview_does_not_claim_scheduled_email(db):
    ctx = _merchant_ctx(db)
    db.commit()
    overview = MerchantReportsService().overview(db, ctx)
    assert overview["scheduled_email_available"] is False
    assert overview["period"]["timezone"] == "UTC"
    assert overview["executive"]["on_time_percent"] is None
