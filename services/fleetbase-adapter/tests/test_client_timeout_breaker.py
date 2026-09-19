"""Phase 6: ops timeout 2s + circuit breaker on FleetbaseClient."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from porterchain_fleetbase_adapter.circuit_breaker import reset_shared_breaker
from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.exceptions import (
    FleetbaseApiError,
    FleetbaseCircuitOpenError,
    FleetbaseNotConfiguredError,
)


@pytest.fixture(autouse=True)
def _reset_breaker():
    reset_shared_breaker(failure_threshold=3, open_seconds=60.0)
    yield
    reset_shared_breaker()


def _settings(**kwargs) -> FleetbaseSettings:
    base = dict(
        api_url="http://fleetbase.test",
        api_key="key",
        dispatch_bridge=True,
        ops_timeout=2.0,
        request_timeout=15.0,
        max_retries=0,
        breaker_failure_threshold=3,
        breaker_open_seconds=60.0,
    )
    base.update(kwargs)
    return FleetbaseSettings(**base)


def test_disabled_bridge_raises_not_configured() -> None:
    """FB-HS-002 / HS-11: dispatch_bridge off → fail closed before HTTP."""
    http = httpx.Client(
        transport=httpx.MockTransport(lambda _r: httpx.Response(200, json={"ok": True}))
    )
    client = FleetbaseClient(_settings(dispatch_bridge=False), client=http)
    with pytest.raises(FleetbaseNotConfiguredError, match="disabled"):
        client.get("/v1/drivers")


def test_get_defaults_to_ops_timeout() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"ok": True})
    )
    http = httpx.Client(transport=transport)
    client = FleetbaseClient(_settings(), client=http)

    seen: list[float | httpx.Timeout] = []

    original = http.request

    def capture(method, url, **kwargs):
        seen.append(kwargs.get("timeout"))
        return original(method, url, **kwargs)

    http.request = capture  # type: ignore[method-assign]
    client.get("/v1/drivers")
    assert seen and float(seen[0]) == 2.0


def test_post_defaults_to_request_timeout() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"ok": True})
    )
    http = httpx.Client(transport=transport)
    client = FleetbaseClient(_settings(), client=http)

    seen: list[float | httpx.Timeout] = []
    original = http.request

    def capture(method, url, **kwargs):
        seen.append(kwargs.get("timeout"))
        return original(method, url, **kwargs)

    http.request = capture  # type: ignore[method-assign]
    client.post("/v1/orders", json={})
    assert seen and float(seen[0]) == 15.0


def test_circuit_opens_after_threshold_and_fails_fast() -> None:
    def boom(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    http = httpx.Client(transport=httpx.MockTransport(boom))
    client = FleetbaseClient(_settings(), client=http)

    for _ in range(3):
        with pytest.raises(FleetbaseApiError):
            client.get("/v1/drivers")

    with pytest.raises(FleetbaseCircuitOpenError):
        client.get("/v1/drivers")


def test_circuit_half_open_recovers_on_success() -> None:
    reset_shared_breaker(failure_threshold=2, open_seconds=0.0)
    calls = {"n": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            raise httpx.ConnectError("down")
        return httpx.Response(200, json={"ok": True})

    http = httpx.Client(transport=httpx.MockTransport(flaky))
    client = FleetbaseClient(
        _settings(breaker_failure_threshold=2, breaker_open_seconds=0.0),
        client=http,
    )

    for _ in range(2):
        with pytest.raises(FleetbaseApiError):
            client.get("/v1/drivers")

    # open_seconds=0 → immediate half-open; next success closes.
    assert client.get("/v1/drivers") == {"ok": True}
    assert client._breaker.state == "closed"  # noqa: SLF001


def test_client_4xx_does_not_trip_breaker() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, text="missing")
    )
    http = httpx.Client(transport=transport)
    client = FleetbaseClient(_settings(breaker_failure_threshold=2), client=http)

    for _ in range(5):
        with pytest.raises(FleetbaseApiError):
            client.get("/v1/missing")

    assert client._breaker.state == "closed"  # noqa: SLF001


def test_orchestrator_run_uses_request_timeout() -> None:
    from porterchain_fleetbase_adapter.orchestrator import OrchestratorService

    mock_client = MagicMock()
    mock_client.post.return_value = {"assignments": []}
    svc = OrchestratorService(_settings(), client=mock_client)
    svc.run(order_ids=["o1"], vehicle_ids=["vehicle_1"], driver_ids=["driver_1"])
    kwargs = mock_client.post.call_args.kwargs
    assert kwargs.get("timeout") == 15.0
    assert kwargs["json"]["vehicle_ids"] == ["vehicle_1"]
    assert kwargs["json"]["driver_ids"] == ["driver_1"]
