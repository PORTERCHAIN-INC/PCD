"""OAuth 2.0 third-party access for merchant API partners."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from porterchain_shared.redis_client import get_redis_client

_TOKEN_PREFIX = "oat_"
_CLIENT_PREFIX = "pc_oauth_"
_CODE_PREFIX = "oac_"
_TOKEN_TTL_SECONDS = 3600
_CODE_TTL_SECONDS = 300


class OAuthService:
    def list_clients(self, merchant_profile: dict[str, Any] | None) -> list[dict[str, Any]]:
        return [self._public_client(c) for c in self._clients(merchant_profile)]

    def create_client(
        self,
        merchant_profile: dict[str, Any] | None,
        *,
        merchant_id: str,
        name: str,
        scopes: list[str],
        environment: str,
        redirect_uris: list[str] | None = None,
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        profile = dict(merchant_profile or {})
        integrations = dict(profile.get("integrations") or {})
        clients = list(integrations.get("oauth_clients") or [])
        raw_secret = secrets.token_urlsafe(32)
        client_id = f"{_CLIENT_PREFIX}{environment}_{secrets.token_urlsafe(12)}"
        record = {
            "client_id": client_id,
            "name": name,
            "scopes": scopes,
            "environment": environment,
            "redirect_uris": redirect_uris or [],
            "client_secret_hash": hashlib.sha256(raw_secret.encode()).hexdigest(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        clients.append(record)
        integrations["oauth_clients"] = clients
        profile["integrations"] = integrations
        get_redis_client().set(f"oauth:client:{client_id}", merchant_id)
        return self._public_client(record), raw_secret, profile

    def issue_authorization_code(
        self,
        merchant_profile: dict[str, Any] | None,
        *,
        client_id: str,
        merchant_id: str,
        redirect_uri: str,
        scope: str | None = None,
    ) -> str:
        client = self.require_client(merchant_profile, client_id)
        allowed_redirects = client.get("redirect_uris") or []
        if allowed_redirects and redirect_uri not in allowed_redirects:
            raise ValueError("redirect_uri_mismatch")
        scopes = self._resolve_scopes(client, scope)
        code = f"{_CODE_PREFIX}{secrets.token_urlsafe(24)}"
        payload = {
            "client_id": client_id,
            "merchant_id": merchant_id,
            "scopes": scopes,
            "redirect_uri": redirect_uri,
            "environment": client.get("environment") or "sandbox",
        }
        get_redis_client().setex(f"oauth:code:{code}", _CODE_TTL_SECONDS, json.dumps(payload))
        return code

    def client_credentials_token(
        self,
        merchant_profile: dict[str, Any] | None,
        *,
        merchant_id: str,
        client_id: str,
        client_secret: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        client = self.require_client(merchant_profile, client_id)
        self._verify_secret(client, client_secret)
        scopes = self._resolve_scopes(client, scope)
        return self._issue_access_token(
            merchant_id=merchant_id,
            client_id=client_id,
            scopes=scopes,
            environment=str(client.get("environment") or "sandbox"),
        )

    def authorization_code_token(
        self,
        merchant_profile: dict[str, Any] | None,
        *,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str | None = None,
    ) -> dict[str, Any]:
        client = self.require_client(merchant_profile, client_id)
        self._verify_secret(client, client_secret)
        raw = get_redis_client().get(f"oauth:code:{code}")
        if not raw:
            raise ValueError("invalid_grant")
        payload = json.loads(raw)
        if payload.get("client_id") != client_id:
            raise ValueError("invalid_grant")
        if redirect_uri and payload.get("redirect_uri") != redirect_uri:
            raise ValueError("redirect_uri_mismatch")
        get_redis_client().delete(f"oauth:code:{code}")
        return self._issue_access_token(
            merchant_id=str(payload["merchant_id"]),
            client_id=client_id,
            scopes=list(payload.get("scopes") or []),
            environment=str(payload.get("environment") or "sandbox"),
        )

    def resolve_bearer_token(self, token: str) -> dict[str, Any] | None:
        if not token.startswith(_TOKEN_PREFIX):
            return None
        raw = get_redis_client().get(f"oauth:token:{token}")
        if not raw:
            return None
        return json.loads(raw)

    def api_key_shim(self, payload: dict[str, Any], merchant_id: str) -> Any:
        return SimpleNamespace(
            id="oauth",
            merchant_id=merchant_id,
            scopes=payload.get("scopes") or [],
            environment=payload.get("environment") or "sandbox",
        )

    def metadata(self, api_base_url: str) -> dict[str, Any]:
        base = api_base_url.rstrip("/")
        return {
            "issuer": base,
            "authorization_endpoint": f"{base}/v1/oauth/authorize",
            "token_endpoint": f"{base}/v1/oauth/token",
            "grant_types_supported": ["client_credentials", "authorization_code"],
            "token_endpoint_auth_methods_supported": ["client_secret_post"],
            "scopes_supported": [
                "shipments:read",
                "shipments:write",
                "tracking:read",
                "webhooks:manage",
            ],
        }

    def find_client(self, merchant_profile: dict[str, Any] | None, client_id: str) -> dict[str, Any] | None:
        for client in self._clients(merchant_profile):
            if client.get("client_id") == client_id:
                return client
        return None

    def require_client(self, merchant_profile: dict[str, Any] | None, client_id: str) -> dict[str, Any]:
        client = self.find_client(merchant_profile, client_id)
        if not client:
            raise ValueError("invalid_client")
        return client

    def _issue_access_token(
        self,
        *,
        merchant_id: str,
        client_id: str,
        scopes: list[str],
        environment: str,
    ) -> dict[str, Any]:
        token = f"{_TOKEN_PREFIX}{environment}_{secrets.token_urlsafe(32)}"
        payload = {
            "merchant_id": merchant_id,
            "client_id": client_id,
            "scopes": scopes,
            "environment": environment,
        }
        get_redis_client().setex(f"oauth:token:{token}", _TOKEN_TTL_SECONDS, json.dumps(payload))
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": _TOKEN_TTL_SECONDS,
            "scope": " ".join(scopes),
        }

    def _clients(self, merchant_profile: dict[str, Any] | None) -> list[dict[str, Any]]:
        profile = merchant_profile or {}
        integrations = profile.get("integrations") if isinstance(profile.get("integrations"), dict) else {}
        clients = integrations.get("oauth_clients")
        if not isinstance(clients, list):
            return []
        return [c for c in clients if isinstance(c, dict)]

    @staticmethod
    def _public_client(client: dict[str, Any]) -> dict[str, Any]:
        return {
            "client_id": client.get("client_id"),
            "name": client.get("name"),
            "scopes": client.get("scopes") or [],
            "environment": client.get("environment") or "sandbox",
            "redirect_uris": client.get("redirect_uris") or [],
            "created_at": client.get("created_at"),
        }

    def _verify_secret(self, client: dict[str, Any], client_secret: str) -> None:
        expected = client.get("client_secret_hash")
        if not expected:
            raise ValueError("invalid_client")
        actual = hashlib.sha256(client_secret.encode()).hexdigest()
        if actual != expected:
            raise ValueError("invalid_client")

    def _resolve_scopes(self, client: dict[str, Any], scope: str | None) -> list[str]:
        allowed = list(client.get("scopes") or [])
        if not scope:
            return allowed
        requested = [part for part in scope.split() if part]
        for item in requested:
            if item not in allowed:
                raise ValueError(f"invalid_scope:{item}")
        return requested
