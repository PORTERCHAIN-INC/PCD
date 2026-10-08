"""Shopify App Store review: no JSON dead ends, coherent reconnect, real CarrierService."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine import shopify_fulfillment_ops as ops
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine.activation_service import SIGNUP_SOURCE_SHOPIFY
from porterchain_api.merchant_engine.shopify_admin_graphql import ShopifyAdminError
from porterchain_api.merchant_models import Merchant, MerchantUser, ShopifyShop

_GQL = "porterchain_api.merchant_engine.shopify_admin_graphql"
_CALLBACK = "https://api.porterchain.com/v1/integrations/shopify/carrier-service/rates"
_GID = "gid://shopify/DeliveryCarrierService/777"


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt-secret-key-32chars!!",
        porterchain_api_url="https://api.porterchain.com",
        merchant_portal_url="https://merchant.porterchain.com",
        shopify_api_key="cid",
        shopify_api_secret="shpss_test",
        fleetbase_dispatch_bridge=False,
        spicedb_enabled=False,
        spicedb_use_memory=True,
        spicedb_required=False,
    )


def _qs(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


# ---------------------------------------------------------------- router (no DB)


def _client(settings: Settings):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from porterchain_api.config import get_settings
    from porterchain_api.db import get_db
    from porterchain_api.routers.shopify import router

    def _db():
        yield MagicMock()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = _db
    return TestClient(app)


@pytest.mark.parametrize(
    ("raised", "code"),
    [
        (ValueError("shop_already_connected"), "shop_already_connected"),
        (ValueError("oauth_state_expired"), "oauth_state_expired"),
        (RuntimeError("shopify down"), "install_failed"),
    ],
)
def test_callback_error_redirects_to_portal_page_not_json(raised, code) -> None:
    client = _client(_settings())
    with patch.object(shopify, "complete_oauth", side_effect=raised):
        res = client.get(
            "/v1/integrations/shopify/callback",
            params={"shop": "qhrk0d-5s.myshopify.com", "code": "abc", "state": "s"},
            follow_redirects=False,
        )
    assert res.status_code == 302
    assert "application/json" not in res.headers.get("content-type", "")
    loc = res.headers["location"]
    assert loc.startswith("https://merchant.porterchain.com/shopify?")
    assert _qs(loc) == {"shop": "qhrk0d-5s.myshopify.com", "error": code}


def test_callback_without_code_redirects() -> None:
    client = _client(_settings())
    res = client.get(
        "/v1/integrations/shopify/callback",
        params={"shop": "qhrk0d-5s.myshopify.com"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert _qs(res.headers["location"])["error"] == "oauth_code_missing"


@pytest.mark.parametrize(
    ("row", "rates"),
    [
        (SimpleNamespace(shop_domain="demo.myshopify.com", carrier_service_gid=_GID), "ready"),
        (
            SimpleNamespace(
                shop_domain="demo.myshopify.com",
                carrier_service_gid=None,
                install_hooks={"carrier_error": "carrier_plan_unsupported"},
            ),
            "carrier_plan_unsupported",
        ),
    ],
)
def test_callback_success_reports_real_rate_status(row, rates) -> None:
    client = _client(_settings())
    with patch.object(shopify, "complete_oauth", return_value=row):
        res = client.get(
            "/v1/integrations/shopify/callback",
            params={"shop": "demo.myshopify.com", "code": "abc"},
            follow_redirects=False,
        )
    assert res.status_code == 302
    assert _qs(res.headers["location"]) == {
        "shop": "demo.myshopify.com",
        "connected": "1",
        "rates": rates,
    }


def test_install_bad_shop_redirects_not_400() -> None:
    client = _client(_settings())
    res = client.get(
        "/v1/integrations/shopify/install", params={"shop": "not a shop"}, follow_redirects=False
    )
    assert res.status_code == 302
    assert _qs(res.headers["location"]) == {"error": "shop_domain_invalid"}


def test_error_code_is_sanitised() -> None:
    from porterchain_api.merchant_engine.shopify_urls import app_error_url

    url = app_error_url(_settings(), code="<script>Bad Code!", shop_domain="evil")
    assert _qs(url) == {"shop": "evil.myshopify.com", "error": "scriptbadcode"}


# ------------------------------------------------------- carrier registration


def test_carrier_registered_with_api_callback_and_gid_persisted(db) -> None:
    settings = _settings()
    ctx = _company(db)
    shop = _shop(db, ctx.id, token=shopify._encrypt("tok", settings))
    with patch(f"{_GQL}.carrier_service_create", return_value=_GID) as create:
        assert ops._register_carrier_service(shop, settings) == _GID
    create.assert_called_once()
    assert create.call_args.kwargs["callback_url"] == _CALLBACK
    db.expire_all()
    assert db.get(ShopifyShop, shop.id).carrier_service_gid == _GID


def test_carrier_input_is_active_with_service_discovery() -> None:
    settings = _settings()
    with patch(f"{_GQL}.admin_graphql") as gql:
        gql.return_value = {"carrierServiceCreate": {"carrierService": {"id": _GID}, "userErrors": []}}
        from porterchain_api.merchant_engine.shopify_admin_graphql import carrier_service_create

        assert carrier_service_create("demo.myshopify.com", "tok", settings, callback_url=_CALLBACK) == _GID
    variables = gql.call_args.args[4]
    assert variables["input"]["active"] is True
    assert variables["input"]["supportsServiceDiscovery"] is True
    assert variables["input"]["callbackUrl"] == _CALLBACK


def test_carrier_already_on_store_is_adopted(db) -> None:
    settings = _settings()
    ctx = _company(db)
    shop = _shop(db, ctx.id, token=shopify._encrypt("tok", settings))
    with (
        patch(f"{_GQL}.carrier_service_create", side_effect=ShopifyAdminError("PorterChain is already configured")),
        patch(f"{_GQL}.carrier_service_find", return_value=_GID),
        patch(f"{_GQL}.carrier_service_update", return_value=_GID) as update,
    ):
        assert ops._register_carrier_service(shop, settings) == _GID
    assert update.call_args.kwargs["service_id"] == _GID
    assert shop.carrier_service_gid == _GID


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ("Carrier Calculated Shipping must be enabled for your store", "carrier_plan_unsupported"),
        ("graphql_errors:ACCESS_DENIED", "carrier_scope_missing"),
        ("http_500", "carrier_register_failed"),
    ],
)
def test_carrier_failure_is_surfaced_not_swallowed(db, message, code) -> None:
    settings = _settings()
    ctx = _company(db)
    shop = _shop(db, ctx.id, token=shopify._encrypt("tok", settings), gid="gid://shopify/DeliveryCarrierService/1")
    with (
        patch(f"{_GQL}.carrier_service_update", side_effect=ShopifyAdminError(message)),
        patch(f"{_GQL}.carrier_service_create", side_effect=ShopifyAdminError(message)),
        patch(f"{_GQL}.carrier_service_find", return_value=None),
        patch.object(shopify, "_admin_post", return_value=None),
        patch("porterchain_api.merchant_engine.shopify_fulfillment_service._register_webhooks"),
    ):
        with pytest.raises(RuntimeError, match=code):
            ops._register_carrier_service(shop, settings)
        result = shopify._post_install_hooks(shop, settings)
    assert result["ok"] is False
    assert result["carrier_registered"] is False
    assert result["carrier_error"] == code
    # A stale id that Shopify no longer accepts must not keep claiming "registered".
    assert shop.carrier_service_gid is None
    assert shopify.rates_status(shop) == code


def test_carrier_without_token_is_an_error_not_silent() -> None:
    shop = SimpleNamespace(shop_domain="demo.myshopify.com", encrypted_access_token=None, carrier_service_gid=None)
    with pytest.raises(RuntimeError, match="carrier_no_token"):
        ops._register_carrier_service(shop, _settings())


def test_open_app_heals_missing_carrier(db) -> None:
    from porterchain_api.merchant_engine.shopify_session import ensure_carrier_rates

    settings = _settings()
    ctx = _company(db)
    shop = _shop(db, ctx.id, token=shopify._encrypt("tok", settings))
    with patch(f"{_GQL}.carrier_service_create", return_value=_GID):
        assert ensure_carrier_rates(db, settings, shop.shop_domain) == "ready"
    db.refresh(shop)
    assert shop.carrier_service_gid == _GID
    with patch(f"{_GQL}.carrier_service_create") as create:
        assert ensure_carrier_rates(db, settings, shop.shop_domain) == "ready"
    create.assert_not_called()


# ------------------------------------------------------------ reconnect (DB)


def _company(db, *, claimed: bool = True, placeholder_for: str | None = None) -> Merchant:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Co {suffix}",
        email=f"co-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        profile=(
            {"source": SIGNUP_SOURCE_SHOPIFY, "shopify_shop_domain": placeholder_for}
            if placeholder_for
            else {}
        ),
    )
    db.add(merchant)
    db.flush()
    db.add(
        MerchantUser(
            merchant_id=merchant.id,
            clerk_user_id=f"user_{suffix}" if claimed else f"pending:owner-{suffix}@test.local",
            email=f"owner-{suffix}@test.local",
            role=MerchantRole.OWNER.value,
            is_active=True,
        )
    )
    db.commit()
    return merchant


def _shop(db, merchant_id: str, *, token: str = "enc", gid: str | None = None, domain: str | None = None) -> ShopifyShop:
    row = ShopifyShop(
        merchant_id=merchant_id,
        shop_domain=domain or f"rv-{uuid4().hex[:8]}.myshopify.com",
        installed_at=datetime.now(UTC),
        encrypted_access_token=token,
        carrier_service_gid=gid,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _oauth(db, settings: Settings, shop_domain: str, merchant_id: str | None):
    state = shopify.sign_oauth_state(merchant_id, settings)
    with (
        patch.object(shopify, "verify_oauth_hmac", return_value=True),
        patch.object(shopify, "_exchange_token", return_value={"access_token": "new-token", "scope": "write_shipping"}),
        patch.object(shopify, "_admin_get", return_value={"shop": {"id": 42, "email": "x@shop.test"}}),
        patch("porterchain_api.merchant_engine.shopify_fulfillment_service._register_webhooks"),
        patch(f"{_GQL}.carrier_service_update", return_value=_GID) as update,
        patch(f"{_GQL}.carrier_service_create", return_value=_GID) as create,
    ):
        row = shopify.complete_oauth(
            db, settings, shop_domain=shop_domain, code="c", state=state, query_string="x"
        )
    return row, update, create


def test_same_company_reconnect_is_idempotent_and_reregisters_carrier(db) -> None:
    settings = _settings()
    company = _company(db)
    shop = _shop(db, company.id, gid="gid://shopify/DeliveryCarrierService/1")
    row, update, create = _oauth(db, settings, shop.shop_domain, company.id)
    assert row.id == shop.id
    assert row.merchant_id == company.id
    assert shopify._decrypt(row.encrypted_access_token, settings) == "new-token"
    update.assert_called_once()
    create.assert_not_called()
    assert row.carrier_service_gid == _GID
    assert shopify.rates_status(row) == "ready"
    assert db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop.shop_domain).count() == 1


def test_other_claimed_company_gets_shop_already_connected(db) -> None:
    settings = _settings()
    owner = _company(db)
    other = _company(db)
    shop = _shop(db, owner.id)
    with pytest.raises(ValueError, match="shop_already_connected"):
        _oauth(db, settings, shop.shop_domain, other.id)
    db.rollback()
    assert db.get(ShopifyShop, shop.id).merchant_id == owner.id


def test_unclaimed_install_placeholder_moves_to_signed_in_company(db) -> None:
    """The review flow: Shopify install made a placeholder; the review login connects."""
    settings = _settings()
    domain = f"rv-{uuid4().hex[:8]}.myshopify.com"
    placeholder = _company(db, claimed=False, placeholder_for=domain)
    review = _company(db)
    shop = _shop(db, placeholder.id, domain=domain)
    row, _update, create = _oauth(db, settings, domain, review.id)
    assert row.id == shop.id
    assert row.merchant_id == review.id
    create.assert_called_once()
    assert row.carrier_service_gid == _GID


def test_uninstalled_shop_can_be_connected_by_another_company(db) -> None:
    settings = _settings()
    owner = _company(db)
    newcomer = _company(db)
    shop = _shop(db, owner.id, token=None)
    shop.uninstalled_at = datetime.now(UTC)
    db.commit()
    row, _u, _c = _oauth(db, settings, shop.shop_domain, newcomer.id)
    assert row.merchant_id == newcomer.id
    assert row.uninstalled_at is None


def test_shop_lookup_tells_signed_in_view_who_holds_the_store(db) -> None:
    from porterchain_api.merchant_engine.shopify_one_click import connection_payload

    settings = _settings()
    me = _company(db)
    owner = _company(db)
    domain = f"rv-{uuid4().hex[:8]}.myshopify.com"
    placeholder = _company(db, claimed=False, placeholder_for=domain)
    mine = _shop(db, me.id)
    theirs = _shop(db, owner.id)
    _shop(db, placeholder.id, domain=domain)

    def lookup(shop: str):
        return connection_payload(db, me.id, settings, shop_domain=shop)["shop_lookup"]

    assert lookup(mine.shop_domain)["status"] == "linked_here"
    assert lookup(theirs.shop_domain) == {
        "shop_domain": theirs.shop_domain,
        "status": "linked_elsewhere",
        "can_link": False,
    }
    assert lookup(domain)["status"] == "linked_elsewhere"
    assert lookup(domain)["can_link"] is True
    assert lookup("nobody-here.myshopify.com")["status"] == "not_linked"
    assert connection_payload(db, me.id, settings)["shop_lookup"] is None


def test_go_live_blocks_until_carrier_registered(db) -> None:
    from porterchain_api.merchant_engine.shopify_one_click import connection_payload

    settings = _settings()
    me = _company(db)
    shop = _shop(db, me.id)
    payload = connection_payload(db, me.id, settings)
    assert payload["go_live"]["checks"]["carrier_registered"] is False
    assert "carrier_not_registered" in payload["go_live"]["blocking"]
    shop.carrier_service_gid = _GID
    db.commit()
    payload = connection_payload(db, me.id, settings)
    assert payload["go_live"]["checks"]["carrier_registered"] is True
    assert "carrier_not_registered" not in payload["go_live"]["blocking"]
