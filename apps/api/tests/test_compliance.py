import uuid
from datetime import UTC, datetime, timedelta

import pytest

from porterchain_api.booking_models import Order
from porterchain_api.platform import compliance as c
from porterchain_api.platform.privacy_erasure import erase_subject


def test_region_profiles_ca_and_at():
    at = c.region_profile(c.normalize_compliance({"region": "AT"}))
    assert at["currency"] == "EUR" and at["tax"]["rate_pct"] == 20.0 and at["cookie_banner"] is True
    assert at["invoice_retention_years"] == 7 and at["locale"] == "de-AT"
    ca = c.region_profile(c.normalize_compliance(None))
    assert ca["currency"] == "CAD" and ca["tax"]["name"] == "HST" and ca["cookie_banner"] is False
    with pytest.raises(ValueError):
        c.normalize_compliance({"region": "XX"})


def test_breach_72h_clock():
    now = datetime(2026, 10, 10, 12, tzinfo=UTC)
    b = c.normalize_breaches([{"title": "Lost laptop", "detected_at": (now - timedelta(hours=70)).isoformat()}])[0]
    clk = c.breach_clock(b, now=now)
    assert clk["hours_left"] == 2.0 and not clk["overdue"]
    assert c.breach_clock(b, now=now + timedelta(hours=3))["overdue"] is True
    b["authority_notified_at"] = now.isoformat()
    assert c.breach_clock(b, now=now + timedelta(hours=3))["overdue"] is False


def test_requests_30_day_due_and_types():
    r = c.normalize_requests([{"type": "portability", "subject": "a@b.c", "opened_at": "2026-10-01T00:00:00+00:00"}])[0]
    assert r["due_at"].startswith("2026-10-31") and r["status"] == "open"
    with pytest.raises(ValueError):
        c.normalize_requests([{"type": "nope", "subject": "x"}])


def test_overview_has_registers(db):
    o = c.overview(db)
    assert o["ropa"] and o["subprocessors"] and o["retention"] and "DPIA" in o["dpia_gps"]


def test_erasure_scrubs_contacts_keeps_books(db):
    tag = uuid.uuid4().hex[:8]
    email = f"erase-{tag}@example.com"
    o = Order(
        order_number=f"ER{tag}", tracking_number=f"ET{tag}", amount_cents=4200,
        pickup={"formatted": "1 Main St, Milton", "city": "Milton"},
        dropoff={"formatted": "5 King St W, Toronto ON M5V 2T6", "contact_email": email, "contact_name": "Jane Doe",
                 "city": "Toronto", "postal": "M5V 2T6", "lat": 43.6451, "lng": -79.3923},
        scheduled_at=datetime.now(UTC),
    )
    db.add(o)
    db.flush()
    plan = erase_subject(db, email=email)
    assert plan["dry_run"] and plan["orders_scrubbed"] == 1 and o.dropoff.get("contact_email") == email
    erase_subject(db, email=email, dry_run=False)
    assert "contact_email" not in o.dropoff and "contact_name" not in o.dropoff
    assert o.dropoff["postal_fsa"] == "M5V" and o.dropoff["lat_round"] == 43.65 and o.amount_cents == 4200
    assert o.pickup["formatted"] == "1 Main St, Milton"  # sender untouched
    assert o.compliance_metadata["erasure"]["at"]
