from datetime import UTC, datetime, timedelta

from porterchain_api.reporting.analytics import (
    _fsa,
    _group,
    forecast_by_fsa,
    ops_analytics,
)


def test_fsa_and_group():
    assert _fsa({"postal_code": "m5v 2t6"}) == "M5V" and _fsa({}) == "?"
    rows = [{"m": "a", "revenue_cents": 100, "margin_cents": 30}, {"m": "a", "revenue_cents": 100, "margin_cents": 10}]
    assert _group(rows, "m") == [{"key": "a", "stops": 2, "revenue_cents": 200, "margin_cents": 40, "margin_pct": 20.0}]


def test_forecast_weekday_mean():
    now = datetime(2026, 10, 10, 12, tzinfo=UTC)  # Saturday
    hist = []
    for w in range(6):  # 3 orders every Monday in M5V, 1 every Tuesday in L9T
        mon = now - timedelta(days=5 + 7 * w)
        hist += [(mon, "M5V")] * 3 + [(mon + timedelta(days=1), "L9T")]
    f = {r["fsa"]: r for r in forecast_by_fsa(hist, now=now)}
    mon = next(d for d in f["M5V"]["days"] if d["day"] == "2026-10-12")
    assert mon["expected"] == 3.0 and f["M5V"]["next7_total"] == 3.0 and f["L9T"]["next7_total"] == 1.0


def test_ops_analytics_shape(db):
    out = ops_analytics(db, days=30)
    assert {"kpis", "margin_by", "drivers", "trend", "forecast"} <= set(out)
    assert set(out["margin_by"]) == {"merchant", "fsa", "vehicle", "route"}


def test_new_orders_are_stamped_with_fsa(db):
    import uuid

    from porterchain_api.booking_models import Order

    tag = uuid.uuid4().hex[:8]
    o = Order(order_number=f"AS{tag}", tracking_number=f"AT{tag}", amount_cents=100, pickup={},
              dropoff={"formatted": "1 King St W, Toronto ON M5H 1A1"}, scheduled_at=datetime.now(UTC),
              compliance_metadata={"vehicle_class": "cargo_van"})
    db.add(o)
    db.flush()
    assert o.compliance_metadata["analytics"] == {"fsa": "M5H", "vehicle": "cargo_van"}
