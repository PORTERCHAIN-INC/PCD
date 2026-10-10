"""Shopify expiring offline tokens: grant params, storage, refresh, migration, reauth."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs
from uuid import uuid4

import httpx
import pytest

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine import shopify_fulfillment_ops as ops
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine.shopify_session import install_from_session_token
from porterchain_api.merchant_engine import shopify_tokens as tokens
from porterchain_api.merchant_engine.shopify_admin_graphql import ShopifyAdminError, admin_graphql
from porterchain_api.merchant_models import Merchant, MerchantUser, ShopifyShop

_REAL_TOKEN_REQUEST = tokens._token_request  # conftest stubs it per test
_REAL_HTTPX_CLIENT = httpx.Client
_GQL = "porterchain_api.merchant_engine.shopify_admin_graphql"
_GID = "gid://shopify/DeliveryCarrierService/777"
_NON_EXPIRING_BODY = (
    '{"errors":"[API] Non-expiring access tokens are no longer accepted for the Admin API. '
    'Start using expiring offline tokens: https://shopify.dev/docs/apps/build/authentication-'
    'authorization/access-tokens/offline-access-tokens#expiring-vs-non-expiring-offline-tokens"}'
)


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


def _pair(n: int = 1) -> dict[str, object]:
    return {
        "access_token": f"shpat_new_{n}",
        "scope": "write_shipping,read_orders",
        "expires_in": 3600,
        "refresh_token": f"shprt_new_{n}",
        "refresh_token_expires_in": 7776000,
    }


class _Recorder:
    """Stands in for the token endpoint; records every form body."""

    def __init__(self, *responses: object) -> None:
        self.calls: list[dict[str, str]] = []
        self._responses = list(responses)

    def __call__(self, shop: str, data: dict[str, str]) -> dict[str, object]:
        self.calls.append({"shop": shop, **data})
        result = self._responses.pop(0) if self._responses else _pair()
        if isinstance(result, Exception):
            raise result
        return result  # type: ignore[return-value]


def _company(db) -> Merchant:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Tok {suffix}",
        email=f"tok-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        profile={},
    )
    db.add(merchant)
    db.flush()
    db.add(
        MerchantUser(
            merchant_id=merchant.id,
            clerk_user_id=f"user_{suffix}",
            email=f"owner-{suffix}@test.local",
            role=MerchantRole.OWNER.value,
            is_active=True,
        )
    )
    db.commit()
    return merchant


def _shop(db, settings: Settings, **fields) -> ShopifyShop:
    token = fields.pop("token", "shpat_legacy")
    refresh = fields.pop("refresh", None)
    row = ShopifyShop(
        merchant_id=_company(db).id,
        shop_domain=f"tk-{uuid4().hex[:8]}.myshopify.com",
        installed_at=datetime.now(UTC),
        encrypted_access_token=shopify._encrypt(token, settings),
        encrypted_refresh_token=shopify._encrypt(refresh, settings),
        **fields,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _expiring(db, settings: Settings, minutes_left: float, **fields) -> ShopifyShop:
    now = datetime.now(UTC)
    return _shop(
        db,
        settings,
        token="shpat_old",
        refresh="shprt_old",
        scopes="write_shipping",
        token_status=tokens.STATUS_EXPIRING,
        access_token_expires_at=now + timedelta(minutes=minutes_left),
        refresh_token_expires_at=now + timedelta(days=80),
        **fields,
    )


# ------------------------------------------------------------- grant params


def test_every_grant_asks_for_an_expiring_offline_token(monkeypatch) -> None:
    settings = _settings()
    rec = _Recorder(_pair(), _pair(), _pair())
    monkeypatch.setattr(tokens, "_token_request", rec)

    tokens.exchange_id_token("demo.myshopify.com", "id-token", settings)
    tokens.migrate_legacy_token("demo.myshopify.com", "shpat_legacy", settings)
    tokens.refresh_access_token("demo.myshopify.com", "shprt_1", settings)

    id_token, migrate, refresh = rec.calls
    creds = {"client_id": "cid", "client_secret": "shpss_test"}
    assert id_token == {
        "shop": "demo.myshopify.com",
        **creds,
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": "id-token",
        "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
        "requested_token_type": "urn:shopify:params:oauth:token-type:offline-access-token",
        "expiring": "1",
    }
    assert migrate == {
        "shop": "demo.myshopify.com",
        **creds,
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": "shpat_legacy",
        "subject_token_type": "urn:shopify:params:oauth:token-type:offline-access-token",
        "requested_token_type": "urn:shopify:params:oauth:token-type:offline-access-token",
        "expiring": "1",
    }
    assert refresh == {
        "shop": "demo.myshopify.com",
        **creds,
        "grant_type": "refresh_token",
        "refresh_token": "shprt_1",
    }


def test_token_request_posts_form_and_reads_shopify_error() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(400, json={"error": "invalid_subject_token"})

    def client(**kwargs):
        return _REAL_HTTPX_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    with patch.object(tokens.httpx, "Client", side_effect=client):
        with pytest.raises(tokens.ShopifyTokenError) as err:
            _REAL_TOKEN_REQUEST("demo.myshopify.com", {"code": "c", "expiring": "1"})
    assert err.value.status == 400
    assert err.value.error == "invalid_subject_token"
    assert err.value.transient is False
    assert str(seen[0].url) == "https://demo.myshopify.com/admin/oauth/access_token"
    assert seen[0].headers["content-type"] == "application/x-www-form-urlencoded"
    assert parse_qs(seen[0].content.decode()) == {"code": ["c"], "expiring": ["1"]}


def test_refresh_retries_once_after_transient_failure(monkeypatch) -> None:
    rec = _Recorder(tokens.ShopifyTokenError(503, "http_503"), _pair(2))
    monkeypatch.setattr(tokens, "_token_request", rec)
    body = tokens.refresh_access_token("demo.myshopify.com", "shprt_1", _settings())
    assert body["access_token"] == "shpat_new_2"
    assert [c["refresh_token"] for c in rec.calls] == ["shprt_1", "shprt_1"]


# ------------------------------------------------------------------ storage


def test_store_token_response_keeps_expiry_and_encrypted_refresh_token() -> None:
    settings = _settings()
    row = SimpleNamespace(scopes=None)
    before = datetime.now(UTC)
    assert tokens.store_token_response(row, _pair(), settings) == "shpat_new_1"
    assert row.encrypted_access_token != "shpat_new_1"
    assert shopify._decrypt(row.encrypted_access_token, settings) == "shpat_new_1"
    assert row.encrypted_refresh_token != "shprt_new_1"
    assert shopify._decrypt(row.encrypted_refresh_token, settings) == "shprt_new_1"
    assert before + timedelta(minutes=59) < row.access_token_expires_at <= before + timedelta(hours=1, seconds=5)
    assert row.refresh_token_expires_at - row.access_token_expires_at > timedelta(days=89)
    assert row.token_status == tokens.STATUS_EXPIRING
    assert row.scopes == "write_shipping,read_orders"


def test_managed_install_stores_the_expiring_pair(db, monkeypatch) -> None:
    settings = _settings()
    domain = f"tk-{uuid4().hex[:8]}.myshopify.com"
    rec = _Recorder(_pair(7))
    monkeypatch.setattr(tokens, "_token_request", rec)
    with (
        patch.object(shopify, "_admin_get", return_value={"shop": {"id": 42}}),
        patch("porterchain_api.merchant_engine.shopify_fulfillment_service._register_webhooks"),
        patch(f"{_GQL}.carrier_service_create", return_value=_GID) as create,
    ):
        row = install_from_session_token(
            db, settings, shop_domain=domain, id_token="session-token"
        )
    assert rec.calls[0]["subject_token"] == "session-token"
    assert rec.calls[0]["expiring"] == "1"
    assert len(rec.calls) == 1  # fresh token: carrier registration did not refresh
    assert create.call_args.args[1] == "shpat_new_7"
    db.expire_all()
    saved = db.get(ShopifyShop, row.id)
    assert shopify._decrypt(saved.encrypted_access_token, settings) == "shpat_new_7"
    assert shopify._decrypt(saved.encrypted_refresh_token, settings) == "shprt_new_7"
    assert saved.access_token_expires_at is not None
    assert saved.refresh_token_expires_at is not None
    assert saved.token_status == tokens.STATUS_EXPIRING


# ------------------------------------------------------------------ refresh


def test_fresh_token_is_used_without_refreshing(db, monkeypatch) -> None:
    settings = _settings()
    shop = _expiring(db, settings, minutes_left=50)
    rec = _Recorder()
    monkeypatch.setattr(tokens, "_token_request", rec)
    assert tokens.access_token_for(shop, settings) == "shpat_old"
    assert rec.calls == []


def test_token_is_refreshed_before_it_expires_and_rotation_is_saved(db, monkeypatch) -> None:
    settings = _settings()
    shop = _expiring(db, settings, minutes_left=2)
    rec = _Recorder(_pair(3))
    monkeypatch.setattr(tokens, "_token_request", rec)
    assert tokens.access_token_for(shop, settings) == "shpat_new_3"
    assert rec.calls[0]["grant_type"] == "refresh_token"
    assert rec.calls[0]["refresh_token"] == "shprt_old"
    db.expire_all()
    saved = db.get(ShopifyShop, shop.id)
    assert shopify._decrypt(saved.encrypted_access_token, settings) == "shpat_new_3"
    assert shopify._decrypt(saved.encrypted_refresh_token, settings) == "shprt_new_3"
    assert saved.access_token_expires_at > datetime.now(UTC) + timedelta(minutes=55)
    # Next call reuses the stored token.
    assert tokens.access_token_for(saved, settings) == "shpat_new_3"
    assert len(rec.calls) == 1


def test_another_worker_already_refreshed_so_no_second_refresh(db, monkeypatch) -> None:
    settings = _settings()
    shop = _expiring(db, settings, minutes_left=2)
    # Another process refreshed the row after we loaded it.
    db.connection().exec_driver_sql(
        "UPDATE shopify_shops SET encrypted_access_token = %(tok)s, "
        "access_token_expires_at = now() + interval '1 hour' WHERE id = %(id)s",
        {"tok": shopify._encrypt("shpat_other_worker", settings), "id": shop.id},
    )
    rec = _Recorder()
    monkeypatch.setattr(tokens, "_token_request", rec)
    assert tokens.access_token_for(shop, settings) == "shpat_other_worker"
    assert rec.calls == []


def test_refused_refresh_marks_shop_for_reauth(db, monkeypatch) -> None:
    settings = _settings()
    shop = _expiring(db, settings, minutes_left=-1)
    monkeypatch.setattr(
        tokens, "_token_request", _Recorder(tokens.ShopifyTokenError(401, "invalid_request"))
    )
    assert tokens.access_token_for(shop, settings) is None
    db.expire_all()
    assert db.get(ShopifyShop, shop.id).token_status == tokens.TOKEN_REAUTH_REQUIRED
    with pytest.raises(RuntimeError, match="token_reauth_required"):
        ops._register_carrier_service(db.get(ShopifyShop, shop.id), settings)


def test_shopify_outage_keeps_a_still_valid_token(db, monkeypatch) -> None:
    settings = _settings()
    shop = _expiring(db, settings, minutes_left=3)
    monkeypatch.setattr(
        tokens,
        "_token_request",
        _Recorder(tokens.ShopifyTokenError(None, "ConnectError"), tokens.ShopifyTokenError(None, "ConnectError")),
    )
    assert tokens.access_token_for(shop, settings) == "shpat_old"
    assert shop.token_status == tokens.STATUS_EXPIRING


def test_expired_refresh_token_needs_reauth_without_calling_shopify(db, monkeypatch) -> None:
    settings = _settings()
    shop = _expiring(db, settings, minutes_left=-5)
    shop.refresh_token_expires_at = datetime.now(UTC) - timedelta(days=1)
    db.commit()
    rec = _Recorder()
    monkeypatch.setattr(tokens, "_token_request", rec)
    assert tokens.access_token_for(shop, settings) is None
    assert rec.calls == []
    assert shop.token_status == tokens.TOKEN_REAUTH_REQUIRED


# ------------------------------------------------------- legacy migration


def test_legacy_token_is_migrated_once_on_first_use(db, monkeypatch) -> None:
    settings = _settings()
    shop = _shop(db, settings, token="shpat_legacy", scopes="write_shipping")
    rec = _Recorder(_pair(5))
    monkeypatch.setattr(tokens, "_token_request", rec)
    with patch(f"{_GQL}.carrier_service_create", return_value=_GID) as create:
        assert ops._register_carrier_service(shop, settings) == _GID
    assert rec.calls[0]["subject_token"] == "shpat_legacy"
    assert rec.calls[0]["subject_token_type"] == tokens.TOKEN_TYPE_OFFLINE
    assert create.call_args.args[1] == "shpat_new_5"
    db.expire_all()
    saved = db.get(ShopifyShop, shop.id)
    assert saved.token_status == tokens.STATUS_EXPIRING
    assert shopify._decrypt(saved.encrypted_refresh_token, settings) == "shprt_new_5"
    assert tokens.access_token_for(saved, settings) == "shpat_new_5"
    assert len(rec.calls) == 1


def test_legacy_token_shopify_will_not_exchange_needs_reauth(db, monkeypatch) -> None:
    settings = _settings()
    shop = _shop(db, settings, token="shpat_legacy", scopes="write_shipping")
    monkeypatch.setattr(
        tokens, "_token_request", _Recorder(tokens.ShopifyTokenError(400, "invalid_subject_token"))
    )
    assert tokens.access_token_for(shop, settings) is None
    assert shop.token_status == tokens.TOKEN_REAUTH_REQUIRED


def test_custom_app_token_is_never_exchanged(monkeypatch) -> None:
    settings = _settings()
    row = SimpleNamespace(scopes="write_shipping", shop_domain="demo.myshopify.com")
    tokens.store_custom_app_token(row, "shpat_custom", settings)
    rec = _Recorder()
    monkeypatch.setattr(tokens, "_token_request", rec)
    assert tokens.access_token_for(row, settings) == "shpat_custom"
    assert rec.calls == []


def test_open_from_admin_reports_migration_then_ok(db, monkeypatch) -> None:
    settings = _settings()
    shop = _shop(db, settings, token="shpat_legacy", scopes="write_shipping")
    monkeypatch.setattr(tokens, "_token_request", _Recorder(_pair(6)))
    assert tokens.token_state_for_open(db, settings, shop.shop_domain) == "migrated"
    assert tokens.token_state_for_open(db, settings, shop.shop_domain) == "ok"


def test_open_from_admin_with_refused_token_is_unusable(db) -> None:
    settings = _settings()
    shop = _shop(db, settings, scopes="write_shipping", token_status=tokens.TOKEN_REAUTH_REQUIRED)
    assert tokens.token_state_for_open(db, settings, shop.shop_domain) == ""
    assert tokens.token_state_for_open(db, settings, "nobody.myshopify.com") == ""


# ------------------------------------------------------------- /install


def test_open_after_migration_reruns_install_hooks() -> None:
    from porterchain_api.merchant_engine import shopify_session as session

    row = SimpleNamespace(shop_domain="demo.myshopify.com", merchant_id="m1")
    with (
        patch.object(session, "verify_session_token", return_value="demo.myshopify.com"),
        patch(f"{tokens.__name__}.token_state_for_open", return_value="migrated"),
        patch.object(session, "ensure_carrier_rates", return_value="ready") as heal,
        patch.object(session, "_active_row", return_value=row),
        patch.object(session, "is_unclaimed_install_merchant", return_value=False),
    ):
        body = session.open_embedded(MagicMock(), _settings(), "session-token")
    assert body["rates"] == "ready"
    assert heal.call_args.kwargs == {"rehook": True}


# --------------------------------------------------------- error mapping


def _graphql_response(status: int, text: str):
    def client(**kwargs):
        transport = httpx.MockTransport(lambda request: httpx.Response(status, text=text))
        return _REAL_HTTPX_CLIENT(transport=transport, **kwargs)

    return patch(f"{_GQL}.httpx.Client", side_effect=client)


def test_non_expiring_403_is_a_token_problem_not_a_missing_scope() -> None:
    with _graphql_response(403, _NON_EXPIRING_BODY):
        with pytest.raises(ShopifyAdminError) as err:
            admin_graphql("demo.myshopify.com", "shpat_legacy", _settings(), "{ shop { id } }")
    assert str(err.value) == "http_403:token_non_expiring"
    assert ops.carrier_error_code(err.value) == tokens.TOKEN_REAUTH_REQUIRED


def test_invalid_token_401_maps_to_reauth() -> None:
    with _graphql_response(401, '{"errors":"[API] Invalid API key or access token"}'):
        with pytest.raises(ShopifyAdminError) as err:
            admin_graphql("demo.myshopify.com", "shpat_x", _settings(), "{ shop { id } }")
    assert ops.carrier_error_code(err.value) == tokens.TOKEN_REAUTH_REQUIRED


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ("create:http_403:token_non_expiring", "token_reauth_required"),
        ("create:http_401:token_invalid", "token_reauth_required"),
        ("graphql_errors:ACCESS_DENIED", "carrier_scope_missing"),
        ("http_403", "carrier_scope_missing"),
        ("http_500", "carrier_register_failed"),
    ],
)
def test_carrier_error_codes(message: str, code: str) -> None:
    assert ops.carrier_error_code(message) == code


def test_refused_token_during_carrier_setup_flags_reauth(db) -> None:
    settings = _settings()
    shop = _expiring(db, settings, minutes_left=50, carrier_service_gid=_GID)
    refused = ShopifyAdminError("http_403:token_non_expiring")
    with (
        patch(f"{_GQL}.carrier_service_update", side_effect=refused),
        patch(f"{_GQL}.carrier_service_create", side_effect=refused),
        patch(f"{_GQL}.carrier_service_find", side_effect=refused),
        patch.object(shopify, "_admin_post", return_value=None),
    ):
        with pytest.raises(RuntimeError, match="token_reauth_required"):
            ops._register_carrier_service(shop, settings)
    db.expire_all()
    saved = db.get(ShopifyShop, shop.id)
    assert saved.token_status == tokens.TOKEN_REAUTH_REQUIRED
    assert saved.carrier_service_gid == _GID  # unknown, not proven gone


def test_go_live_blocks_on_reauth(db) -> None:
    from porterchain_api.merchant_engine.shopify_one_click import connection_payload

    settings = _settings()
    shop = _expiring(db, settings, minutes_left=50)
    shop.token_status = tokens.TOKEN_REAUTH_REQUIRED
    db.commit()
    payload = connection_payload(db, shop.merchant_id, settings)
    assert payload["go_live"]["checks"]["token_valid"] is False
    assert "token_reauth_required" in payload["go_live"]["blocking"]


def test_disconnect_clears_refresh_token_too() -> None:
    row = SimpleNamespace(
        encrypted_access_token="a",
        access_token_expires_at=datetime.now(UTC),
        encrypted_refresh_token="r",
        refresh_token_expires_at=datetime.now(UTC),
        token_status=tokens.STATUS_EXPIRING,
    )
    tokens.clear_tokens(row)
    assert all(getattr(row, attr) is None for attr in tokens._TOKEN_ATTRS)
