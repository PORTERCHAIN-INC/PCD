"""OAuth service unit tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.oauth_engine.oauth_service import OAuthService


@pytest.fixture
def oauth_service() -> OAuthService:
    return OAuthService()


def test_create_client_and_client_credentials_token(oauth_service: OAuthService) -> None:
    redis = MagicMock()
    redis.get.return_value = "merchant-1"
    with patch("porterchain_api.oauth_engine.oauth_service.get_redis_client", return_value=redis):
        public, secret, profile = oauth_service.create_client(
            {},
            merchant_id="merchant-1",
            name="ERP",
            scopes=["shipments:read"],
            environment="sandbox",
        )
        assert public["client_id"].startswith("pc_oauth_sandbox_")
        token = oauth_service.client_credentials_token(
            profile,
            merchant_id="merchant-1",
            client_id=public["client_id"],
            client_secret=secret,
            scope=None,
        )
    assert token["token_type"] == "Bearer"
    assert token["access_token"].startswith("oat_sandbox_")
    stored = redis.setex.call_args_list[-1]
    assert stored[0][0].startswith("oauth:token:")


def test_authorization_code_exchange(oauth_service: OAuthService) -> None:
    redis = MagicMock()
    code_payload = {
        "client_id": "pc_oauth_sandbox_test",
        "merchant_id": "merchant-1",
        "scopes": ["shipments:read"],
        "redirect_uri": "https://partner.example/callback",
        "environment": "sandbox",
    }
    redis.get.return_value = json.dumps(code_payload)
    profile = {
        "integrations": {
            "oauth_clients": [
                {
                    "client_id": "pc_oauth_sandbox_test",
                    "client_secret_hash": __import__("hashlib").sha256(b"secret").hexdigest(),
                    "scopes": ["shipments:read"],
                    "environment": "sandbox",
                    "redirect_uris": ["https://partner.example/callback"],
                }
            ]
        }
    }
    with patch("porterchain_api.oauth_engine.oauth_service.get_redis_client", return_value=redis):
        token = oauth_service.authorization_code_token(
            profile,
            client_id="pc_oauth_sandbox_test",
            client_secret="secret",
            code="oac_testcode",
            redirect_uri="https://partner.example/callback",
        )
    assert token["access_token"].startswith("oat_sandbox_")
    redis.delete.assert_called_once()
