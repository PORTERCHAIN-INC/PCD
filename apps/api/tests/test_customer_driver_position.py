"""Privacy rules for the customer in-app live map driver position."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from porterchain_api.booking_engine.customer_driver_position import (
    ACTIVE_STATES,
    RateLimited,
    check_rate,
    customer_driver_position,
    reset_rate_limits,
)

NOW = datetime(2026, 10, 16, 15, 0, tzinfo=UTC)
DRIVER = SimpleNamespace(
    id="d1", full_name="Amrit Singh", phone="+14165550000", documents={}
)
PIN = {
    "lat": 43.648712,
    "lng": -79.381734,
    "recorded_at": (NOW - timedelta(seconds=40)).isoformat(),
}


def order(
    state: str = "IN_TRANSIT", customer_id: str = "c1", driver_id: str | None = "d1"
):
    return SimpleNamespace(
        state=state, customer_id=customer_id, assigned_driver_id=driver_id
    )


def call(o, **kw):
    args = {
        "customer_id": "c1",
        "driver": DRIVER,
        "pin": PIN,
        "gps_allowed": lambda d: True,
        "now": NOW,
    }
    args.update(kw)
    return customer_driver_position(o, **args)


def test_owner_gets_coarse_position_only():
    out = call(order())
    assert out["available"] is True
    assert out["position"]["lat"] == 43.649
    assert out["position"]["lng"] == -79.382
    blob = repr(out)
    for secret in ("+1416", "Amrit", "d1", "phone", "email", "rating"):
        assert secret not in blob


def test_other_customer_is_not_found():
    assert call(order(customer_id="someone-else")) is None
    assert call(None) is None
    assert call(order(), customer_id="") is None


@pytest.mark.parametrize(
    "state",
    [
        "BOOKED",
        "DISPATCH_READY",
        "DRIVER_ASSIGNED",
        "DELIVERED",
        "POD_COMPLETED",
        "INVOICED",
        "CLOSED",
        "CANCELLED",
        "FAILED",
    ],
)
def test_never_outside_active_window(state):
    out = call(order(state))
    assert out == {"available": False, "reason": "not_active", "position": None}


def test_active_states_cover_out_for_delivery():
    assert {"PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"} <= ACTIVE_STATES
    assert "DELIVERED" not in ACTIVE_STATES


def test_respects_gps_policy_and_consent():
    assert call(order(), gps_allowed=lambda d: False)["reason"] == "sharing_off"


def test_no_driver_or_signal():
    assert call(order(driver_id=None))["reason"] == "no_driver"
    assert call(order(), pin=None)["reason"] == "no_signal"


def test_stale_positions_are_dropped():
    old = {**PIN, "recorded_at": (NOW - timedelta(minutes=11)).isoformat()}
    assert call(order(), pin=old)["reason"] == "stale"
    assert call(order(), pin={**PIN, "recorded_at": None})["reason"] == "stale"


def test_rate_limit_per_customer_and_order():
    reset_rate_limits()
    check_rate("c1:T1", now=100.0)
    with pytest.raises(RateLimited) as exc:
        check_rate("c1:T1", now=102.0)
    assert exc.value.retry_after == 3
    check_rate("c1:T2", now=102.0)  # other order is independent
    check_rate("c1:T1", now=105.5)  # interval passed


def test_route_requires_sign_in():
    from fastapi.testclient import TestClient

    from porterchain_api.config import Settings, get_settings
    from porterchain_api.main import app

    # Bypass off: a local CLERK_DEV_BYPASS would otherwise sign the request in.
    locked = Settings(
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt-secret-local",
        spicedb_enabled=False,
        spicedb_use_memory=True,
        spicedb_required=False,
        clerk_dev_bypass=False,
    )
    app.dependency_overrides[get_settings] = lambda: locked
    try:
        resp = TestClient(app).get("/v1/customers/me/orders/PC-1/driver-position")
    finally:
        app.dependency_overrides.pop(get_settings, None)
    assert resp.status_code in {401, 403}
