"""AV — admin save → card GET → preview cents match on every door."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.admin_models import AdminUser, PricingTariff
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.auth.merchant_api import MerchantApiKeyContext, get_merchant_api_context
from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.main import app
from porterchain_api.merchant_models import MerchantApiKey
from porterchain_pricing.gta_rate import default_gta_rate_config

LIFTGATE_CENTS = 7777
SIZE_TIER_CENTS = 1300
CARGO_VAN_BASE_CAD = 91.11
DISTANCE_METERS = 15_000


def _booking_body() -> dict:
    return {
        "pickup": {
            "formatted": "100 King St W, Toronto",
            "postal": "M5X 1A1",
            "lat": 43.65,
            "lng": -79.38,
        },
        "dropoff": {
            "formatted": "200 Bay St, Toronto",
            "postal": "M5J 2J2",
            "lat": 43.64,
            "lng": -79.37,
        },
        "vehicle_class": "cargoVan",
        "package_type": "looseParcel",
        "weight_kg": 10,
        "scheduled_at": (datetime.now(UTC) + timedelta(hours=4)).isoformat(),
        "requires_liftgate": True,
    }


def test_admin_save_card_get_and_preview_cents_match(db, settings, admin_ctx, merchant_ctx, monkeypatch) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    merchant_ctx.user.role = MerchantRole.OWNER.value
    tariff_rows = db.query(PricingTariff).filter(PricingTariff.is_active.is_(True)).all()
    for row in tariff_rows:
        row.is_active = False
    db.commit()

    settings_svc = AdminSettingsService()
    previous_gta = settings_svc.get_config_value(db, "pricing_gta_rate")
    previous_card = settings_svc.get_config_value(db, "pricing_rate_card")

    gta = deepcopy(default_gta_rate_config().to_dict())
    if isinstance(previous_gta, dict) and previous_gta.get("vehicles"):
        gta = deepcopy(previous_gta)
    gta.setdefault("vehicles", {})["cargo_van"] = dict(gta.get("vehicles", {}).get("cargo_van") or {})
    gta["vehicles"]["cargo_van"]["base_price"] = CARGO_VAN_BASE_CAD
    settings_svc.set_config(db, admin_ctx, "pricing_gta_rate", gta, reason="AV golden")
    settings_svc.set_config(
        db, admin_ctx, "pricing_rate_card", {"liftgate_cents": LIFTGATE_CENTS}, reason="AV golden"
    )

    monkeypatch.setattr("porterchain_api.routers.merchants.require_module", lambda ctx, module: None)
    monkeypatch.setattr(
        "porterchain_api.routers.merchant.dashboard_booking.require_module", lambda ctx, module: None
    )
    monkeypatch.setattr("porterchain_api.routers.merchant.billing.require_module", lambda ctx, module: None)

    api_key = MerchantApiKey(
        merchant_id=merchant_ctx.merchant.id,
        name="AV golden",
        key_prefix="pk_av",
        key_hash="av-golden",
        scopes=["shipments:read"],
        environment="test",
    )
    admin = AdminContext(
        user=AdminUser(clerk_user_id="av-admin", email="av-admin@porterchain.com", role="super_admin"),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_merchant_context] = lambda: merchant_ctx
    app.dependency_overrides[get_merchant_api_context] = lambda: MerchantApiKeyContext(
        merchant=merchant_ctx.merchant, api_key=api_key
    )
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        saved = client.put(
            f"/v1/admin/merchants/{merchant_ctx.merchant.id}/pricing",
            json={
                "pricing_model": "distance",
                "surcharges": {"downtown": False, "upper_zone": False},
                "size_tiers": [{"label": "Any", "surcharge_cents": SIZE_TIER_CENTS}],
            },
        )
        assert saved.status_code == 200, saved.text
        admin_card = saved.json()["card"]
        assert admin_card["liftgate_cents"] == LIFTGATE_CENTS
        assert admin_card["pricing_model"] == "distance"
        assert admin_card["size_tiers"][0]["surcharge_cents"] == SIZE_TIER_CENTS

        merchant_card = client.get("/v1/merchant/pricing/rate-card")
        partner_card = client.get("/v1/merchant-api/rate-card")
        assert merchant_card.status_code == 200, merchant_card.text
        assert partner_card.status_code == 200, partner_card.text
        assert merchant_card.json() == partner_card.json() == admin_card

        with patch(
            "porterchain_api.merchant_engine.booking_service.resolve_route_distance",
            return_value=(DISTANCE_METERS, 1200, "haversine"),
        ):
            portal = client.post("/v1/merchant/booking/preview", json=_booking_body())
            partner = client.post("/v1/merchant-api/quotes", json=_booking_body())
        assert portal.status_code == 200, portal.text
        assert partner.status_code == 200, partner.text
        portal_quote = portal.json()
        partner_quote = partner.json()
        assert portal_quote["valid"] is True
        assert partner_quote["valid"] is True
        assert portal_quote["amount_cents"] == partner_quote["amount_cents"]
        assert portal_quote["pricing_breakdown"]["items"] == partner_quote["pricing_breakdown"]["items"]
        assert portal_quote["pricing_breakdown"]["tax_cents"] == partner_quote["pricing_breakdown"]["tax_cents"]

        km = DISTANCE_METERS / 1000.0
        distance = client.post(
            "/v1/pricing/components/distance",
            json={"vehicle_type": "cargo_van", "total_km": km},
        )
        size = client.post(
            "/v1/pricing/components/size-weight",
            json={"merchant_id": merchant_ctx.merchant.id, "weight_kg": 10},
        )
        assert distance.status_code == 200, distance.text
        assert size.status_code == 200, size.text
        distance_cents = distance.json()["total_cents"]
        size_cents = size.json()["total_cents"]
        assert distance_cents == int(round(CARGO_VAN_BASE_CAD * 100))
        assert size_cents == SIZE_TIER_CENTS

        items = {row["code"]: row["amount_cents"] for row in portal_quote["pricing_breakdown"]["items"]}
        assert items["base"] == distance_cents
        assert items["size_tier"] == size_cents
        assert items["liftgate"] == LIFTGATE_CENTS

        subtotal = distance_cents + size_cents + LIFTGATE_CENTS
        tax = portal_quote["pricing_breakdown"]["tax_cents"] or 0
        assert portal_quote["amount_cents"] == subtotal + tax
        assert portal_quote["pricing_breakdown"]["final_cents"] == portal_quote["amount_cents"]
    finally:
        app.dependency_overrides.clear()
        for row in tariff_rows:
            row.is_active = True
        settings_svc.set_config(db, admin_ctx, "pricing_gta_rate", previous_gta, reason="AV restore")
        settings_svc.set_config(db, admin_ctx, "pricing_rate_card", previous_card, reason="AV restore")
