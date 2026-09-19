"""Pricing Center simulate + merchant A≠B isolation (tariffs present)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.finance_service import AdminFinanceService
from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser, PricingFsaRate, PricingTariff
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.booking_engine.numbers import (
    generate_invoice_number,
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Invoice, Order, Quote
from porterchain_api.db import get_db
from porterchain_api.domain.states import OrderState
from porterchain_api.main import app
from porterchain_api.merchant_models import Merchant
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_pricing.types import GeoPoint, PricingRequest


@pytest.fixture
def client(db):
    admin = AdminContext(
        user=AdminUser(clerk_user_id="sim-admin", email="admin@porterchain.com", role="super_admin"),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def retail_trap(db):
    """Catalog retail tariff that must not steal merchant FSA / GTA bases."""
    row = PricingTariff(
        name="Sim Retail Trap",
        tariff_type="retail",
        vehicle_class="cargo_van",
        zone="gta",
        base_cents=1200,
        per_km_cents=95,
        is_active=True,
    )
    db.add(row)
    db.commit()
    yield row
    db.delete(row)
    db.commit()


def _merchant(db, *, name: str, email: str, model: str = "fsa") -> Merchant:
    row = Merchant(
        company_name=name,
        email=email,
        status="ACTIVE",
        pricing_model=model,
        pricing_config={"surcharges": {"downtown": False, "upper_zone": False}},
    )
    db.add(row)
    db.flush()
    return row


def _req(merchant_id: str, *, postal: str = "M5V 2T6") -> PricingRequest:
    return PricingRequest(
        pickup=GeoPoint(lat=43.589, lng=-79.6441, postal="L4W 5N5", formatted="Mississauga"),
        dropoff=GeoPoint(lat=43.6426, lng=-79.3871, postal=postal, formatted="Toronto"),
        vehicle_class="cargo_van",
        channel="merchant",
        merchant_id=merchant_id,
        distance_meters=15_000,
        total_pickups=1,
        total_drops=1,
        is_downtown=False,
        is_upper_zone=False,
    )


def test_simulate_ignores_global_retail_tariff(client, db, retail_trap):
    merchant = _merchant(db, name="Sim Co", email="sim@example.com", model="distance")
    db.commit()

    r = client.post(
        "/v1/pricing/simulate",
        json={
            "merchant_id": merchant.id,
            "vehicle_class": "cargo_van",
            "distance_meters": 15000,
            "is_downtown": False,
            "is_upper_zone": False,
            "dropoff": {"postal": "M5V 2T6", "lat": 43.6426, "lng": -79.3871},
            "pickup": {"postal": "L4W 5N5", "lat": 43.589, "lng": -79.6441},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pricing_model"] != "contract_tariff"
    assert body["what_won"]
    assert body["final_cents"] > 0
    assert "Retail Trap" not in body["what_won"]


def test_merchants_a_and_b_get_different_fsa_bases(db, retail_trap):
    a = _merchant(db, name="Merchant A", email="a-fsa@example.com", model="fsa")
    b = _merchant(db, name="Merchant B", email="b-fsa@example.com", model="fsa")
    db.add_all(
        [
            PricingFsaRate(dest_fsa="M5V", flat_cents=500, merchant_id=a.id, config={}),
            PricingFsaRate(dest_fsa="M5V", flat_cents=800, merchant_id=b.id, config={}),
        ]
    )
    db.commit()

    svc = get_pricing_service(db)
    qa = svc.to_api_breakdown(svc.calculate(_req(a.id)))
    qb = svc.to_api_breakdown(svc.calculate(_req(b.id)))

    assert qa["metadata"]["pricing_model"] == "fsa_flat_rate"
    assert qb["metadata"]["pricing_model"] == "fsa_flat_rate"
    assert qa["base_cents"] == 500
    assert qb["base_cents"] == 800
    assert qa["final_cents"] != qb["final_cents"]


def test_merchants_a_and_b_get_different_distance_overlays(db, retail_trap):
    a = _merchant(db, name="Dist A", email="a-dist@example.com", model="distance")
    b = _merchant(db, name="Dist B", email="b-dist@example.com", model="distance")
    a.pricing_config = {
        **(a.pricing_config or {}),
        "gta_rate": {"vehicles": {"cargo_van": {"base_price": 40.0, "included_km": 10}}},
        "surcharges": {"downtown": False, "upper_zone": False},
    }
    b.pricing_config = {
        **(b.pricing_config or {}),
        "gta_rate": {"vehicles": {"cargo_van": {"base_price": 99.0, "included_km": 10}}},
        "surcharges": {"downtown": False, "upper_zone": False},
    }
    db.commit()

    svc = get_pricing_service(db)
    qa = svc.to_api_breakdown(svc.calculate(_req(a.id)))
    qb = svc.to_api_breakdown(svc.calculate(_req(b.id)))

    assert qa["metadata"]["pricing_model"] == "gta_delivery_rate"
    assert qb["metadata"]["pricing_model"] == "gta_delivery_rate"
    # Same trip shape; only merchant base_price overlays differ ($40 vs $99).
    assert qb["base_cents"] - qa["base_cents"] == 5900
    assert qa["final_cents"] != qb["final_cents"]


def test_finance_invoice_detail_surfaces_quote_lineage(db):
    now = datetime.now(UTC)
    api = {
        "base_cents": 800,
        "subtotal_cents": 800,
        "tax_cents": 104,
        "final_cents": 904,
        "currency": "cad",
        "items": [{"code": "fsa", "label": "FSA M5V", "amount_cents": 800}],
        "metadata": {
            "pricing_model": "fsa_flat_rate",
            "pricing_model_requested": "fsa",
            "dest_fsa": "M5V",
        },
    }
    quote = Quote(
        pickup={"formatted": "A"},
        dropoff={"formatted": "B", "postal": "M5V 2T6"},
        vehicle_class="cargo_van",
        package_type="parcel",
        scheduled_at=now,
        amount_cents=904,
        currency="cad",
        pricing_breakdown={"items": api["items"], "summary": api},
        expires_at=now + timedelta(hours=1),
    )
    db.add(quote)
    db.flush()
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.INVOICED.value,
        quote_id=quote.id,
        amount_cents=904,
        currency="cad",
        pickup={"formatted": "A"},
        dropoff={"formatted": "B"},
        scheduled_at=now,
    )
    db.add(order)
    db.flush()
    invoice = Invoice(
        invoice_number=generate_invoice_number(),
        order_id=order.id,
        amount_cents=904,
        tax_cents=104,
        fees_cents=0,
        currency="cad",
    )
    db.add(invoice)
    db.commit()

    detail = AdminFinanceService().get_invoice_detail(db, invoice.id)
    assert detail is not None
    assert detail["quote_id"] == quote.id
    assert detail["quote_amount_cents"] == quote.amount_cents
    assert detail["quote_amount_cents"] == detail["amount_cents"]
    assert detail["pricing_model"] == "fsa_flat_rate"
    assert detail["pricing_metadata"]["dest_fsa"] == "M5V"
    assert detail["pricing_breakdown"]["summary"]["final_cents"] == 904
