"""Public /v1/orders/{tn}/tracking must never leak the driver's exact or stale position."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from porterchain_api.booking_engine import public_tracking_limit as ptl
from porterchain_api.booking_engine.customer_driver_position import coarse_position
from porterchain_api.booking_engine.public_tracking_snapshot import build_public_live_tracking
from porterchain_api.booking_models import Order

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)


def _order(state: str = "IN_TRANSIT", driver: str | None = "drv-1") -> Order:
    order = Order()
    for k, v in {
        "id": "ord-1",
        "tracking_number": "PC-PRIV01",
        "state": state,
        "scheduled_at": None,
        "assigned_driver_id": driver,
        "pickup": {"formatted": "1 King St W", "lat": 43.6487, "lng": -79.3817},
        "dropoff": {"formatted": "100 Queen St W", "lat": 43.6532, "lng": -79.3832},
    }.items():
        setattr(order, k, v)
    return order


def _maps() -> MagicMock:
    m = MagicMock()
    m.eta_between.return_value = None
    m.optimized_route.return_value = None
    return m


def _live(minutes_ago: float = 1, lat: float = 43.6512345, lng: float = -79.3845678) -> dict:
    return {
        "location": {"lat": lat, "lng": lng},
        "coordinates": {"lat": lat, "lng": lng},
        "recorded_at": (NOW - timedelta(minutes=minutes_ago)).isoformat(),
        "heading": 90,
        "speed": 12.3,
        "source": "last_known",
        "driver_id": "drv-1",
    }


def _snap(order: Order, live: dict | None, **kw) -> dict:
    return build_public_live_tracking(order, live, maps=_maps(), now=NOW, **kw)


def test_position_is_rounded_to_three_decimals():
    loc = _snap(_order(), _live())["driver_location"]
    assert loc == {"lat": 43.651, "lng": -79.385, "recorded_at": "2026-10-16T11:59:00+00:00"}


def test_no_extra_fields_leak():
    loc = _snap(_order(), _live())["driver_location"]
    assert set(loc) == {"lat", "lng", "recorded_at"}
    body = repr(_snap(_order(), _live()))
    for leak in ("drv-1", "43.6512345", "-79.3845678", "speed", "heading"):
        assert leak not in body


@pytest.mark.parametrize(
    "state",
    ["DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED", "CANCELLED", "CREATED", "ASSIGNED"],
)
def test_nothing_outside_active_states(state):
    assert _snap(_order(state=state), _live())["driver_location"] is None


@pytest.mark.parametrize(
    "state", ["DRIVER_EN_ROUTE", "AT_PICKUP", "PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"]
)
def test_shown_in_active_states(state):
    assert _snap(_order(state=state), _live())["driver_location"] is not None


def test_stale_position_dropped():
    assert _snap(_order(), _live(minutes_ago=11))["driver_location"] is None
    assert _snap(_order(), _live(minutes_ago=9))["driver_location"] is not None


def test_missing_timestamp_dropped():
    live = _live()
    live.pop("recorded_at")
    assert _snap(_order(), live)["driver_location"] is None


def test_gps_consent_off_hides_position():
    assert _snap(_order(), _live(), gps_allowed=lambda: False)["driver_location"] is None
    assert _snap(_order(), _live(), gps_allowed=lambda: True)["driver_location"] is not None


def test_driver_pin_fallback_is_also_filtered(monkeypatch):
    from porterchain_api.dispatch_engine import driver_pin as dp

    monkeypatch.setattr(
        dp,
        "driver_pin",
        lambda _id: {
            "lat": 43.6599999,
            "lng": -79.3900001,
            "source": "last_known",
            "recorded_at": (NOW - timedelta(minutes=2)).isoformat(),
        },
    )
    loc = _snap(_order(), None)["driver_location"]
    assert loc == {"lat": 43.66, "lng": -79.39, "recorded_at": "2026-10-16T11:58:00+00:00"}
    assert _snap(_order(state="DELIVERED"), None)["driver_location"] is None


def test_coarse_position_rejects_bad_input():
    assert coarse_position("IN_TRANSIT", None, now=NOW) is None
    assert coarse_position("IN_TRANSIT", {"lat": "x", "lng": 1, "recorded_at": NOW.isoformat()}, now=NOW) is None


# ---- rate limit ------------------------------------------------------------


def _req(ip: str = "8.8.8.8"):
    return SimpleNamespace(client=SimpleNamespace(host=ip), headers={})


def test_rate_limit_429_per_ip_and_tracking_number(monkeypatch):
    counts: dict[str, int] = {}

    def fake(key, limit, **_):
        counts[key] = counts.get(key, 0) + 1
        return counts[key] <= limit, counts[key], None

    monkeypatch.setattr(ptl, "check_fixed_window", fake)
    for _ in range(ptl.PUBLIC_TRACKING_LIMIT_PER_MINUTE):
        ptl.enforce_public_tracking_limit(_req(), "PC-A", app_env="production")
    with pytest.raises(HTTPException) as exc:
        ptl.enforce_public_tracking_limit(_req(), "PC-A", app_env="production")
    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"] == "60"
    # Other tracking number / other viewer: separate buckets.
    ptl.enforce_public_tracking_limit(_req(), "PC-B", app_env="production")
    ptl.enforce_public_tracking_limit(_req("1.1.1.1"), "PC-A", app_env="production")


def test_rate_limit_exempts_own_server_renders(monkeypatch):
    monkeypatch.setattr(ptl, "check_fixed_window", lambda *a, **k: (False, 999, None))
    ptl.enforce_public_tracking_limit(_req("10.0.0.5"), "PC-A", app_env="production")


def test_rate_limit_redis_down(monkeypatch):
    monkeypatch.setattr(ptl, "check_fixed_window", lambda *a, **k: (False, 0, "down"))
    ptl.enforce_public_tracking_limit(_req(), "PC-A", app_env="local")
    with pytest.raises(HTTPException) as exc:
        ptl.enforce_public_tracking_limit(_req(), "PC-A", app_env="production")
    assert exc.value.status_code == 503


def test_route_applies_limit_and_no_store(monkeypatch):
    from fastapi.testclient import TestClient

    from porterchain_api.main import app
    from porterchain_api.routers import orders as orders_router
    from porterchain_api.schemas import OrderTrackingResponse

    calls: list[str] = []
    monkeypatch.setattr(
        ptl, "enforce_public_tracking_limit", lambda req, tn, app_env: calls.append(tn)
    )
    monkeypatch.setattr(
        orders_router._tracking,
        "get_order_tracking_response",
        lambda db, settings, tn, **_k: OrderTrackingResponse(
            order_id="o1", tracking_number=tn, state="IN_TRANSIT", live_tracking={}
        ),
    )
    resp = TestClient(app).get("/v1/orders/PC-RL1/tracking")
    assert resp.status_code == 200
    assert calls == ["PC-RL1"]
    assert resp.headers["cache-control"] == "no-store"
