"""Admin merchant pricing endpoints — validation, merge safety, engine effect."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_api.merchant_models import Merchant
from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository
from porterchain_pricing.types import GeoPoint, PricingRequest


@pytest.fixture
def merchant(db):
    row = Merchant(
        company_name="Pricing Test Co",
        email="pricing-test@example.com",
        status="ACTIVE",
        pricing_config={},
    )
    db.add(row)
    db.commit()
    yield row
    db.delete(row)
    db.commit()


@pytest.fixture
def client(db, monkeypatch):
    """Admin client sharing the test transaction. Module authz has its own tests."""
    monkeypatch.setattr("porterchain_api.routers.merchants.require_module", lambda ctx, module: None)
    admin = AdminContext(
        user=AdminUser(clerk_user_id="test", email="admin@porterchain.com", role="super_admin"),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _url(m: Merchant) -> str:
    return f"/v1/admin/merchants/{m.id}/pricing"


def test_a_fresh_merchant_reports_platform_defaults(client, merchant):
    body = client.get(_url(merchant)).json()
    assert body["pricing_model"] == "distance"
    assert body["surcharges"] == {"downtown": True, "upper_zone": True}
    assert body["size_tiers"] == []
    assert body["card"]["pricing_model"] == "distance"
    assert "what_wins" in body["card"]
    assert "liftgate_cents" in body["card"]
    assert "driver_payout_mode" not in body["card"]


def test_saving_pricing_round_trips(client, merchant):
    payload = {
        "pricing_model": "fsa",
        "surcharges": {"downtown": False, "upper_zone": True},
        "size_tiers": [
            {
                "label": "Pallet",
                "max_length": 48,
                "max_width": 40,
                "max_height": 60,
                "dimension_unit": "in",
                "max_weight": 500,
                "weight_unit": "lb",
                "surcharge_cents": 2500,
            }
        ],
    }
    assert client.put(_url(merchant), json=payload).status_code == 200

    body = client.get(_url(merchant)).json()
    assert body["pricing_model"] == "fsa"
    assert body["surcharges"]["downtown"] is False
    tier = body["size_tiers"][0]
    # Units survive the round trip so the form shows what the admin typed.
    assert tier["dimension_unit"] == "in" and tier["weight_unit"] == "lb"
    assert tier["max_weight"] == 500
    assert tier["surcharge_cents"] == 2500


def test_saving_pricing_preserves_unrelated_contract_keys(client, merchant, db):
    """The screen owns three keys; the JSON column holds several more."""
    merchant.pricing_config = {
        "rate_card": {"liftgate_cents": 9900},
        "custom_rules": [{"label": "Weekend", "amount_cents": 500}],
        "merchant_discount_percent": 10,
    }
    db.commit()

    client.put(_url(merchant), json={"pricing_model": "distance"})
    db.refresh(merchant)

    assert merchant.pricing_config["rate_card"] == {"liftgate_cents": 9900}
    assert merchant.pricing_config["custom_rules"][0]["label"] == "Weekend"
    assert merchant.pricing_config["merchant_discount_percent"] == 10
    assert merchant.pricing_model == "distance"
    assert "pricing_model" not in merchant.pricing_config


def test_auto_pricing_model_is_rejected(client, merchant):
    r = client.put(_url(merchant), json={"pricing_model": "auto"})
    assert r.status_code == 422


def test_an_unknown_pricing_model_is_rejected(client, merchant):
    r = client.put(_url(merchant), json={"pricing_model": "telepathy"})
    assert r.status_code == 422


def test_a_negative_surcharge_is_rejected(client, merchant):
    r = client.put(
        _url(merchant),
        json={"size_tiers": [{"surcharge_cents": -100}]},
    )
    assert r.status_code == 422


def test_an_unknown_unit_is_rejected(client, merchant):
    r = client.put(
        _url(merchant),
        json={"size_tiers": [{"surcharge_cents": 100, "weight_unit": "stone"}]},
    )
    assert r.status_code == 422


def test_pricing_for_an_unknown_merchant_is_a_404(client):
    assert client.get("/v1/admin/merchants/nope/pricing").status_code == 404


def test_saved_policy_reaches_the_pricing_engine(client, merchant, db):
    """The whole point: what an admin saves must change the next quote."""
    client.put(
        _url(merchant),
        json={
            "pricing_model": "distance",
            "surcharges": {"downtown": False, "upper_zone": False},
            "size_tiers": [{"label": "Any", "surcharge_cents": 700}],
        },
    )

    request = PricingRequest(
        pickup=GeoPoint(lat=43.5890, lng=-79.6441, formatted="Mississauga, ON"),
        dropoff=GeoPoint(lat=43.6426, lng=-79.3871, formatted="Toronto, ON"),
        vehicle_class="cargo_van",
        channel="merchant",
        merchant_id=merchant.id,
    )
    policy = SqlAlchemyPricingRepository(db).load_context(request).merchant_policy

    assert policy.pricing_model == "distance"
    assert policy.charge_downtown is False
    assert len(policy.size_tiers) == 1
    assert policy.size_tiers[0].surcharge_cents == 700


def test_gta_rate_overlay_reaches_load_context(client, merchant, db):
    client.put(
        _url(merchant),
        json={
            "pricing_model": "distance",
            "gta_rate": {"vehicles": {"cargo_van": {"base_price": 88.0}}},
        },
    )
    body = client.get(_url(merchant)).json()
    assert body["has_custom_gta"] is True
    assert body["gta_rate"]["vehicles"]["cargo_van"]["base_price"] == 88.0

    request = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38),
        dropoff=GeoPoint(lat=43.66, lng=-79.39),
        vehicle_class="cargo_van",
        channel="merchant",
        merchant_id=merchant.id,
        distance_meters=10_000,
        total_pickups=1,
        total_drops=1,
        is_downtown=False,
        is_upper_zone=False,
    )
    ctx = SqlAlchemyPricingRepository(db).load_context(request)
    assert ctx.gta_rate is not None
    assert ctx.gta_rate.vehicles["cargo_van"]["base_price"] == 88.0

    # Clear overlay
    assert client.put(_url(merchant), json={"pricing_model": "distance", "gta_rate": None}).status_code == 200
    cleared = client.get(_url(merchant)).json()
    assert cleared["has_custom_gta"] is False
    assert cleared["gta_rate"] is None
