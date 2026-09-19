"""Fleetbase sync SLO tests (DD-05b)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.fleetbase_engine.sync_health import (
    SLO_TARGET_PCT,
    assess_fleetbase_sync,
    build_fleetbase_sync_alerts,
)
from porterchain_api.booking_models import Order


def _addr() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


def _bridge_settings(*, enabled: bool = True) -> Settings:
    suffix = uuid4().hex[:8]
    return Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt",
        fleetbase_dispatch_bridge=enabled,
        fleetbase_api_key=f"key-{suffix}" if enabled else "",
        fleetbase_webhook_secret=f"secret-{suffix}" if enabled else "",
        fleetbase_default_company_uuid=f"company-{suffix}" if enabled else "",
    )


def _make_order(db: Session, *, fleetbase_order_id: str | None = None, state: str = OrderState.BOOKED.value) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state,
        fleetbase_order_id=fleetbase_order_id,
        amount_cents=2500,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def test_assess_fleetbase_sync_bridge_disabled(db: Session) -> None:
    settings = _bridge_settings(enabled=False)
    result = assess_fleetbase_sync(db, settings)
    assert result["bridge_enabled"] is False
    assert result["meets_slo"] is True


def test_slo_threshold_is_98_percent() -> None:
    assert SLO_TARGET_PCT == 98.0
    assert 49 / 50 * 100 >= SLO_TARGET_PCT
    assert 97 / 100 * 100 < SLO_TARGET_PCT


def test_build_fleetbase_sync_alerts_below_slo() -> None:
    slo = {
        "bridge_enabled": True,
        "meets_slo": False,
        "link_pct": 90.0,
        "slo_target_pct": SLO_TARGET_PCT,
        "linked_orders": 9,
        "eligible_orders": 10,
        "dead_letters": 2,
        "pending_jobs": 0,
    }
    codes = {a["code"] for a in build_fleetbase_sync_alerts(slo)}
    assert "fleetbase_sync_below_slo" in codes
    assert "fleetbase_sync_dead_letters" in codes


def test_assess_fleetbase_sync_meets_slo(db: Session) -> None:
    settings = _bridge_settings()
    before = assess_fleetbase_sync(db, settings)
    for _ in range(49):
        _make_order(db, fleetbase_order_id=f"fb-{uuid4().hex[:6]}")
    _make_order(db, fleetbase_order_id=None)
    db.flush()

    after = assess_fleetbase_sync(db, settings)
    added_eligible = after["eligible_orders"] - before["eligible_orders"]
    added_linked = after["linked_orders"] - before["linked_orders"]
    assert added_eligible == 50
    assert added_linked == 49
    assert added_linked / added_eligible * 100 == pytest.approx(98.0)
    assert after["slo_target_pct"] == SLO_TARGET_PCT
    if before["eligible_orders"] == 0:
        assert after["meets_slo"] is True
        assert after["alerts"] == []


def test_assess_fleetbase_sync_below_slo(db: Session) -> None:
    settings = _bridge_settings()
    before = assess_fleetbase_sync(db, settings)
    _make_order(db, fleetbase_order_id="fb-linked")
    _make_order(db, fleetbase_order_id=None)
    _make_order(db, fleetbase_order_id=None)
    db.flush()

    after = assess_fleetbase_sync(db, settings)
    added_eligible = after["eligible_orders"] - before["eligible_orders"]
    added_linked = after["linked_orders"] - before["linked_orders"]
    assert added_eligible == 3
    assert added_linked == 1
    assert added_linked / added_eligible * 100 == pytest.approx(33.33, rel=0.01)
    assert after["meets_slo"] is False
    assert any(a["code"] == "fleetbase_sync_below_slo" for a in after["alerts"])


def test_assess_fleetbase_sync_excludes_cancelled(db: Session) -> None:
    settings = _bridge_settings()
    before = assess_fleetbase_sync(db, settings)
    _make_order(db, fleetbase_order_id="fb-1")
    _make_order(db, fleetbase_order_id=None, state=OrderState.CANCELLED.value)
    db.flush()

    after = assess_fleetbase_sync(db, settings)
    added_eligible = after["eligible_orders"] - before["eligible_orders"]
    added_linked = after["linked_orders"] - before["linked_orders"]
    assert added_eligible == 1
    assert added_linked == 1


def test_assess_fleetbase_sync_excludes_delivered(db: Session) -> None:
    settings = _bridge_settings()
    before = assess_fleetbase_sync(db, settings)
    _make_order(db, fleetbase_order_id="fb-open")
    _make_order(db, fleetbase_order_id=None, state=OrderState.DELIVERED.value)
    _make_order(db, fleetbase_order_id=None, state=OrderState.INVOICED.value)
    db.flush()

    after = assess_fleetbase_sync(db, settings)
    added_eligible = after["eligible_orders"] - before["eligible_orders"]
    added_linked = after["linked_orders"] - before["linked_orders"]
    assert added_eligible == 1
    assert added_linked == 1
