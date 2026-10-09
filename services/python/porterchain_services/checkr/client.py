"""Checkr HTTP client — the only PorterChain module that talks to Checkr.

Engines and routers must not call Checkr URLs directly.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.checkr.com"
HTTP_TIMEOUT_S = 30.0


class CheckrClientError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def verify_webhook_signature(payload: bytes, signature_header: str | None, secret: str) -> bool:
    """Checkr sends `X-Checkr-Signature` as hex HMAC-SHA256 of the raw body."""
    if not secret or not signature_header:
        return False
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    provided = signature_header.strip()
    if provided.startswith("sha256="):
        provided = provided[7:]
    return hmac.compare_digest(expected, provided)


class CheckrClient:
    def __init__(self, *, api_key: str, base_url: str = DEFAULT_BASE_URL) -> None:
        if not api_key:
            raise CheckrClientError("checkr_api_key_missing")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url,
            auth=(self._api_key, ""),
            timeout=HTTP_TIMEOUT_S,
            headers={"Accept": "application/json"},
        )

    def create_candidate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/v1/candidates", json=payload)

    def create_invitation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/v1/invitations", json=payload)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        with self._client() as client:
            response = client.request(method, path, **kwargs)
        if response.status_code >= 400:
            detail = response.text[:300]
            raise CheckrClientError(
                f"checkr_http_{response.status_code}:{detail}",
                status_code=response.status_code,
            )
        data = response.json()
        if not isinstance(data, dict):
            raise CheckrClientError("checkr_invalid_json")
        return data
