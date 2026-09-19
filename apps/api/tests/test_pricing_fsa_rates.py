"""FSA rate storage, merchant isolation and the component endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser, PricingFsaRate
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository


@pytest.fixture
def rates(db):
    """Rows removed after each test so the unique scope index stays clean."""
    created: list[PricingFsaRate] = []

    def _make(**kw) -> PricingFsaRate:
        row = PricingFsaRate(
            dest_fsa=kw.pop("dest_fsa", "M5V"),
            flat_cents=kw.pop("flat_cents", 1800),
            config={},
            **kw,
        )
        db.add(row)
        db.flush()
        created.append(row)
        return row

    yield _make

    for row in created:
        db.delete(row)
    db.commit()


@pytest.fixture
def client(db):
    """Admin-authenticated client sharing the test transaction."""
    admin = AdminContext(
        user=AdminUser(clerk_user_id="test", email="admin@porterchain.com", role="super_admin"),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ------------------------------------------------------- repository loading


def test_repository_loads_platform_and_own_rates_only(db, rates):
    rates(dest_fsa="M5V", flat_cents=2500)  # platform-wide
    rates(dest_fsa="M4B", flat_cents=1800, merchant_id="mine")
    rates(dest_fsa="M6H", flat_cents=900, merchant_id="theirs")

    loaded = SqlAlchemyPricingRepository(db)._load_fsa_rates("mine")
    owners = {r.merchant_id for r in loaded}
    assert "theirs" not in owners
    assert {None, "mine"} <= owners


def test_inactive_rates_are_not_loaded(db, rates):
    rates(dest_fsa="M5V", flat_cents=2500, is_active=False)
    loaded = SqlAlchemyPricingRepository(db)._load_fsa_rates("mine")
    assert not [r for r in loaded if r.dest_fsa == "M5V"]


# ---------------------------------------------------------------- endpoints


def test_distance_endpoint_prices_a_trip(client):
    r = client.post(
        "/v1/pricing/components/distance",
        json={"vehicle_type": "cargo_van", "total_km": 40},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["component"] == "distance"
    assert body["total_cents"] > 0
    assert body["metadata"]["extra_km"] > 0


def test_location_endpoint_honours_forced_flags(client):
    r = client.post(
        "/v1/pricing/components/location",
        json={"is_downtown": True, "is_upper_zone": False},
    )
    assert r.status_code == 200
    assert [i["code"] for i in r.json()["items"]] == ["downtown"]


def test_size_weight_endpoint_charges_nothing_by_default(client, monkeypatch):
    """Catalog default weight_cents_per_kg is 0 — isolate from live SystemConfig overlays."""
    from porterchain_pricing.rate_card import default_rate_card

    monkeypatch.setattr(
        SqlAlchemyPricingRepository,
        "_load_rate_card",
        lambda self: default_rate_card(),
    )
    r = client.post("/v1/pricing/components/size-weight", json={"weight_kg": 400})
    assert r.status_code == 200
    assert r.json()["total_cents"] == 0


def test_fsa_endpoint_reports_a_miss_rather_than_guessing(client):
    r = client.post("/v1/pricing/components/fsa", json={"dest_fsa": "X9X"})
    assert r.status_code == 200
    assert r.json()["metadata"]["matched"] is False


def test_fsa_endpoint_matches_a_stored_rate(client, rates, db):
    rates(dest_fsa="M5V", flat_cents=1800)
    db.commit()
    r = client.post("/v1/pricing/components/fsa", json={"dest_fsa": "M5V 2T6"})
    assert r.status_code == 200
    body = r.json()
    assert body["metadata"]["matched"] is True
    assert body["total_cents"] == 1800


# ----------------------------------------------------------- rate management


def test_create_normalizes_the_postal_code_to_an_fsa(client, db):
    r = client.post(
        "/v1/pricing/components/fsa/rates",
        json={"dest_fsa": "m5v 2t6", "origin_fsa": "l4w", "flat_cents": 1800},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["dest_fsa"] == "M5V"
    assert body["origin_fsa"] == "L4W"

    db.query(PricingFsaRate).filter(PricingFsaRate.id == body["id"]).delete()
    db.commit()


def test_a_malformed_fsa_is_rejected(client):
    r = client.post(
        "/v1/pricing/components/fsa/rates",
        json={"dest_fsa": "12345", "flat_cents": 1800},
    )
    assert r.status_code == 422
    assert "dest_fsa_invalid" in r.json()["detail"]


def test_deleting_an_unknown_rate_is_a_404(client):
    assert client.delete("/v1/pricing/components/fsa/rates/nope").status_code == 404
