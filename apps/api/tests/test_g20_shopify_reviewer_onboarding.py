"""G20 (doc 76 §10): reviewer-proof Shopify onboarding. A-SHR-01/02/03/06 at API level."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_models import ShopifyShop
from porterchain_api.routers import shopify as shopify_router
from tests.test_shopify_review_139170 import _settings

_S = "porterchain_api.merchant_engine.shopify_session"
_SVC = "porterchain_api.merchant_engine.shopify_service"


def _client(db) -> TestClient:
    app = FastAPI()
    app.include_router(shopify_router.router)
    app.dependency_overrides[get_settings] = _settings
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def _shop_json(shop: str) -> dict:
    return {
        "id": 7,
        "name": f"PCDC Review {shop}",
        "email": f"owner+{shop}@example.com",
        "address1": "100 King St W",
        "city": "Toronto",
        "province_code": "ON",
        "zip": "M5X 1A9",
        "country_code": "CA",
    }


def _open(c: TestClient, shop: str):
    with (
        patch(f"{_S}.verify_session_token", return_value=shop),
        patch(f"{_S}._exchange_session_token", return_value={"access_token": "shpat_x", "scope": "read_orders"}),
        patch(f"{_SVC}.shop_details_safe", return_value=_shop_json(shop)),
        patch(f"{_S}._register_carrier_inline", lambda row, s: setattr(row, "carrier_service_gid", "gid://c/1")),
        patch(f"{_SVC}._post_install_hooks", return_value={}),
        patch(f"{_S}.ensure_carrier_rates", return_value="ready"),
    ):
        return c.post("/v1/integrations/shopify/session", headers={"Authorization": "Bearer tok"})


def test_four_click_is_default_on() -> None:
    assert Settings(_env_file=None).shopify_four_click_onboarding_enabled is True


def test_fresh_install_auto_provisions_org_without_login(db) -> None:
    shop = f"g20{uuid.uuid4().hex[:8]}.myshopify.com"
    r = _open(_client(db), shop)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["account_ready"] is True
    row = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop).one()
    assert row.merchant_id  # store linked to an organisation on install


def test_reinstall_reuses_same_org(db) -> None:
    shop = f"g20r{uuid.uuid4().hex[:8]}.myshopify.com"
    c = _client(db)
    assert _open(c, shop).status_code == 200
    first = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop).one().merchant_id
    row = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop).one()
    row.encrypted_access_token = None  # simulate uninstall → reinstall
    db.commit()
    assert _open(c, shop).status_code == 200
    rows = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop).all()
    assert len(rows) == 1 and rows[0].merchant_id == first


def test_forged_session_token_is_401(db) -> None:
    r = _client(db).post("/v1/integrations/shopify/session", headers={"Authorization": "Bearer forged.jwt.x"})
    assert r.status_code == 401
    assert _client(db).post("/v1/integrations/shopify/session").status_code == 401
