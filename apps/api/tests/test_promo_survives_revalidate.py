"""Promo must survive payment revalidation (Stripe uses revalidate_retail_quote)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from porterchain_api.booking_models import Quote
from porterchain_api.domain.states import QuoteState
from porterchain_api.pricing_engine.quote_bridge import _promo_code_from_quote, _request_from_quote


def _quote(**kwargs) -> Quote:
    now = datetime.now(UTC)
    defaults = dict(
        state=QuoteState.QUOTE.value,
        pickup={"formatted": "A", "lat": 43.65, "lng": -79.38},
        dropoff={"formatted": "B", "lat": 43.70, "lng": -79.40},
        vehicle_class="cargo_van",
        package_type="looseParcel",
        scheduled_at=now + timedelta(minutes=30),
        schedule_mode="now",
        amount_cents=5000,
        pricing_breakdown={"items": [], "summary": {}},
        parcels={"booking_mode": "parcels", "items": []},
        expires_at=now + timedelta(minutes=15),
    )
    defaults.update(kwargs)
    return Quote(**defaults)


def test_promo_code_from_parcels():
    q = _quote(parcels={"booking_mode": "parcels", "items": [], "promo_code": "TESTFREE100"})
    assert _promo_code_from_quote(q) == "TESTFREE100"


def test_promo_code_from_breakdown_summary():
    q = _quote(
        parcels={"booking_mode": "parcels", "items": []},
        pricing_breakdown={"items": [], "summary": {"promo_code": "TESTFREE100", "final_cents": 0}},
    )
    assert _promo_code_from_quote(q) == "TESTFREE100"


def test_request_from_quote_keeps_promo_code():
    q = _quote(parcels={"booking_mode": "parcels", "items": [], "promo_code": "TESTFREE100"})
    req = _request_from_quote(q)
    assert req.promo_code == "TESTFREE100"
