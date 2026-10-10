"""Per-merchant FSA rate card: routing → banded cells → PricingEngine columns, cache, overrides, exports."""

from __future__ import annotations

from uuid import uuid4

import pytest
from porterchain_pricing.fsa_card import default_fsa_card, drop_price_cents

from porterchain_api.merchant_models import Merchant, SavedAddress
from porterchain_api.pricing_engine import fsa_rate_card as cards

CALLS: list[tuple[float, float]] = []


def _fake_table(origin, targets, **_):
    """1 km and 1.5 min per 0.01° of latitude offset, never zero."""
    CALLS.append(origin)
    return [
        (
            int((abs(t[0] - origin[0]) * 100 + 1) * 90),
            int((abs(t[0] - origin[0]) * 100 + 1) * 1000),
        )
        for t in targets
    ]


@pytest.fixture(autouse=True)
def _routing(monkeypatch):
    CALLS.clear()
    monkeypatch.setattr(cards, "route_table", _fake_table)


def _merchant(db, *, lat=43.6935, lng=-79.5874, postal="M9W1G6") -> str:
    tag = uuid4().hex[:8]
    m = Merchant(company_name=f"Card Co {tag}", email=f"card-{tag}@test.local", status="ACTIVE")
    db.add(m)
    db.flush()
    db.add(
        SavedAddress(
            merchant_id=m.id,
            label="Warehouse",
            address_type="pickup",
            is_default=True,
            formatted="77 Belfield Rd, Etobicoke, ON",
            postal=postal,
            lat=lat,
            lng=lng,
        )
    )
    db.commit()
    return m.id


def test_every_gta_fsa_gets_a_banded_price_from_the_pickup(db) -> None:
    mid = _merchant(db)
    rows = cards.generate(db, mid)
    drops = cards.gta_drop_fsas(default_fsa_card())
    assert {r.dest_fsa for r in rows} == {d["code"] for d in drops}
    card = default_fsa_card()
    for row in rows:
        km, minutes = row.config["km"], row.config["minutes"]
        assert row.flat_cents % 100 == 0 and row.flat_cents >= card["minimum_cents"]
        assert row.origin_fsa == "M9W" and row.includes_location_fees
        assert abs(row.flat_cents - drop_price_cents(km, minutes, row.dest_fsa, card)) <= 500  # rounding of km/min


def test_cached_per_pickup_and_regenerated_when_it_moves(db) -> None:
    mid = _merchant(db)
    cards.generate(db, mid)
    cards.generate(db, mid)
    assert len(CALLS) == 1  # second read is the cache
    addr = db.query(SavedAddress).filter(SavedAddress.merchant_id == mid).one()
    addr.lat, addr.postal = 43.80, "L4K1A1"
    db.commit()
    rows = cards.generate(db, mid)
    assert len(CALLS) == 2
    assert {r.origin_fsa for r in rows} == {"L4K"}


def test_admin_override_survives_regeneration_and_can_be_cleared(db) -> None:
    mid = _merchant(db)
    cards.generate(db, mid)
    row = cards.override(db, mid, "m5v", 4200)
    assert row.flat_cents == 4200 and row.config["override"]
    cards.generate(db, mid, force=True)
    kept = next(r for r in cards._rows(db, mid) if r.dest_fsa == "M5V")
    assert kept.flat_cents == 4200
    cleared = cards.override(db, mid, "M5V", None)
    assert cleared.flat_cents == cleared.config["computed_cents"] and "override" not in cleared.config
    with pytest.raises(LookupError):
        cards.override(db, mid, "X9X", 100)


def test_card_columns_are_pricing_engine_quotes_and_export(db) -> None:
    mid = _merchant(db)
    card = cards.rate_card(db, mid)
    assert card["pickup"]["fsa"] == "M9W" and card["tier_columns"] == [5, 10, 20]
    m5v = next(c for c in card["cells"] if c["dest_fsa"] == "M5V")
    assert m5v["downtown"] is True
    if card["pricing_model_is_fsa"]:
        assert m5v["parcel_tiers_cents"]["5"] >= m5v["price_cents"]
    csv_text = cards.to_csv(card)
    assert csv_text.splitlines()[0].startswith("drop_fsa,price_cad,5_parcels_cad")
    assert any(line.startswith("M5V,") for line in csv_text.splitlines())
    assert cards.to_pdf(card).startswith(b"%PDF")


def test_refuses_without_pickup_or_routing(db, monkeypatch) -> None:
    tag = uuid4().hex[:8]
    m = Merchant(company_name=f"No Pickup {tag}", email=f"np-{tag}@test.local", status="ACTIVE")
    db.add(m)
    db.commit()
    with pytest.raises(ValueError, match="pickup_required"):
        cards.generate(db, m.id)

    def down(*_a, **_k):
        raise RuntimeError("routing_unavailable")

    monkeypatch.setattr(cards, "route_table", down)
    mid = _merchant(db)
    with pytest.raises(RuntimeError, match="routing_unavailable"):
        cards.generate(db, mid)
    assert cards._rows(db, mid) == []
