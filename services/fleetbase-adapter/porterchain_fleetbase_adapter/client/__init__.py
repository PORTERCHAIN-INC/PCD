"""HTTP client for Fleetbase consumable API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler
from porterchain_fleetbase_adapter.exceptions import FleetbaseApiError, FleetbaseNotConfiguredError, FleetbaseVersionError
from porterchain_fleetbase_adapter.retry import RetryPolicy

logger = logging.getLogger(__name__)


def extract_resource_id(data: dict[str, Any], *nested_keys: str) -> str | None:
    """Resolve Fleetbase resource id from varied response shapes."""
    if not data:
        return None
    for key in ("id", "uuid", "public_id"):
        if isinstance(data.get(key), str):
            return data[key]
    for nested in nested_keys:
        child = data.get(nested)
        if isinstance(child, dict):
            found = extract_resource_id(child)
            if found:
                return found
    order = data.get("order")
    if isinstance(order, dict):
        return extract_resource_id(order)
    inner = data.get("data")
    if isinstance(inner, dict):
        return extract_resource_id(inner, *nested_keys)
    return None


class FleetbaseClient:
    """Low-level Fleetbase REST client — server-side only."""

    def __init__(
        self,
        settings: FleetbaseSettings,
        *,
        client: httpx.Client | None = None,
        retry_policy: RetryPolicy | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self._client = client
        self.retry = retry_policy or RetryPolicy(
            max_retries=settings.max_retries,
            backoff_seconds=settings.retry_backoff_seconds,
        )
        self.errors = error_handler or ErrorHandler()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Fleetbase-Version": self.settings.api_version,
        }
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        return headers

    def _base_url(self) -> str:
        return self.settings.api_url.rstrip("/")

    def _ensure_ready(self) -> None:
        if not self.settings.is_enabled:
            raise FleetbaseNotConfiguredError("Fleetbase dispatch bridge is disabled")

    def _check_version(self, response: httpx.Response) -> None:
        server_version = response.headers.get("X-Fleetbase-Version")
        if server_version and server_version != self.settings.api_version:
            logger.warning(
                "Fleetbase API version mismatch: client=%s server=%s",
                self.settings.api_version,
                server_version,
            )

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        retry: bool = True,
    ) -> dict[str, Any]:
        self._ensure_ready()
        url = f"{self._base_url()}{path}"
        timeout = timeout or self.settings.request_timeout
        headers = self._headers()

        def _do() -> httpx.Response:
            if self._client is not None:
                return self._client.request(method, url, json=json, params=params, headers=headers, timeout=timeout)
            with httpx.Client(timeout=timeout) as ephemeral:
                return ephemeral.request(method, url, json=json, params=params, headers=headers)

        def _execute() -> dict[str, Any]:
            try:
                response = _do()
            except httpx.HTTPError as exc:
                raise FleetbaseApiError(str(exc)) from exc

            self._check_version(response)

            if response.status_code >= 400:
                raise FleetbaseApiError(
                    f"Fleetbase {method} {path} failed",
                    status_code=response.status_code,
                    body=response.text[:1000],
                )

            if not response.content:
                return {}
            try:
                payload = response.json()
            except ValueError:
                return {}
            return payload if isinstance(payload, dict) else {"data": payload}

        if retry:
            return self.retry.run(_execute, is_retryable=ErrorHandler.is_retryable)
        return _execute()

    def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("DELETE", path, **kwargs)
