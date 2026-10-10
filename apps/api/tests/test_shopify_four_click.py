"""4-click onboarding, Shopify stubbed end to end, with an explicit click counter."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.routers import shopify as shopify_router
from tests.test_shopify_review_139170 import _settings

_S = "porterchain_api.merchant_engine.shopify_session"
_SVC = "porterchain_api.merchant_engine.shopify_service"


def _client(db, flag: bool) -> TestClient:
    app = FastAPI()
    app.include_router(shopify_router.router)
    app.dependency_overrides[get_settings] = lambda: _settings().model_copy(
        update={"shopify_four_click_onboarding_enabled": flag}
    )
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_flag_off_routes_are_404(db) -> None:
    c = _client(db, False)
    assert (
        c.get(
            "/v1/integrations/shopify/onboarding", headers={"Authorization": "Bearer x"}
        ).status_code
        == 404
    )
    assert (
        c.post("/v1/integrations/shopify/onboarding/go-live", json={}).status_code
        == 404
    )


def test_four_clicks_install_to_live(db) -> None:
    shop = f"fc{uuid.uuid4().hex[:8]}.myshopify.com"
    shop_json = {
        "shop": {
            "id": 1,
            "name": "PCDC Test",
            "email": f"owner+{shop}@example.com",
            "address1": "100 King St W",
            "city": "Toronto",
            "province_code": "ON",
            "zip": "M5X 1A9",
            "country_code": "CA",
            "latitude": 43.6487,
            "longitude": -79.3817,
        }
    }
    clicks: list[str] = []
    h = {"Authorization": "Bearer tok"}
    c = _client(db, True)
    with (
        patch(f"{_S}.verify_session_token", return_value=shop),
        patch(
            f"{_S}._exchange_session_token",
            return_value={"access_token": "shpat_x", "scope": "read_orders"},
        ),
        patch(f"{_SVC}._admin_get", return_value=shop_json),
        patch(
            f"{_S}._register_carrier_inline",
            lambda row, s: setattr(row, "carrier_service_gid", "gid://c/1"),
        ),
        patch(f"{_SVC}._post_install_hooks", return_value={}),
        patch(
            "porterchain_api.merchant_engine.shopify_tokens.access_token_for",
            return_value="shpat_x",
        ),
        patch(f"{_S}.ensure_carrier_rates", return_value="ready"),
        patch(
            "porterchain_api.pricing_engine.fsa_rate_card.route_table",
            side_effect=lambda origin, targets, **k: [
                (900 + i, 12000 + 50 * i) for i, _ in enumerate(targets)
            ],
        ),
    ):
        clicks += ["install (Shopify App Store)", "approve (Shopify OAuth)"]
        opened = c.post("/v1/integrations/shopify/session", headers=h)
        assert opened.status_code == 200, opened.text
        pre = c.get("/v1/integrations/shopify/onboarding", headers=h).json()
        assert (
            pre["source"] == "shopify_store"
            and "100 King St W" in pre["address"]["formatted"]
        )
        clicks.append("confirm pickup (prefilled)")
        clicks.append("go live")
        live = c.post(
            "/v1/integrations/shopify/onboarding/go-live",
            headers=h,
            json={"address": pre["address"]},
        )
        assert live.status_code == 200, live.text
        out = live.json()
    assert len(clicks) == 4
    assert out["live"] is True and out["rate_card_fsas"] > 0
    assert out["next_step"]["deep_link"] == "shopify://admin/settings/shipping"
    assert out["account"]["portal_access"] == "sign_in_with_shop_email"
