"""Admin install-url: custom-distribution shops get a Partners-link message, not an unsigned URL."""

from __future__ import annotations

from types import SimpleNamespace

from porterchain_api.admin_engine import merchant_org
from porterchain_api.merchant_engine import shopify_apps

SHOP = "8hpwwc-rx.myshopify.com"
S = SimpleNamespace(
    shopify_api_key="pub", shopify_api_secret="pub_secret",
    shopify_extra_apps=f"cust:cust_secret:{SHOP}",
)


def test_custom_app_for():
    assert shopify_apps.custom_app_for(S, SHOP).client_id == "cust"
    assert shopify_apps.custom_app_for(S, "other.myshopify.com") is None


def test_custom_shop_gets_partners_message(monkeypatch):
    monkeypatch.setattr(merchant_org, "require_merchant", lambda db, mid: None)
    audits = []
    monkeypatch.setattr(merchant_org, "write_staff_audit", lambda *a, **k: audits.append(k))
    out = merchant_org.shopify_install_url_for(None, None, "m1", S, shop="8hpwwc-rx")
    assert out["install_url"] is None and out["custom_distribution"] is True
    assert "Partners" in out["message"] and out["client_id"] == "cust"
    assert audits == []


def test_public_shop_still_gets_install_url(monkeypatch):
    monkeypatch.setattr(merchant_org, "require_merchant", lambda db, mid: None)
    monkeypatch.setattr(merchant_org, "write_staff_audit", lambda *a, **k: None)
    out = merchant_org.shopify_install_url_for(None, None, "m1", S, shop="other.myshopify.com")
    assert out["install_url"].endswith("/store/other/oauth/install?client_id=pub")
