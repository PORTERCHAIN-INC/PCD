"""Global PermissionError → 403 JSON envelope (require_module and peers)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from porterchain_api.main import app
from porterchain_api.platform.middleware import REQUEST_ID_HEADER

client = TestClient(app, raise_server_exceptions=False)


def test_permission_error_maps_to_403_json_envelope() -> None:
    async def _boom() -> None:
        raise PermissionError("admin_forbidden:crm")

    app.add_api_route("/__test_permission_403", _boom, methods=["GET"])
    try:
        response = client.get(
            "/__test_permission_403",
            headers={REQUEST_ID_HEADER: "perm-403-req"},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["detail"] == "admin_forbidden:crm"
        assert body["request_id"] == "perm-403-req"
        # Middleware may append the same id; body is the SoT for clients.
        assert "perm-403-req" in (response.headers.get(REQUEST_ID_HEADER) or "")
    finally:
        app.router.routes = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) != "/__test_permission_403"
        ]


def test_permission_error_empty_message_defaults_forbidden() -> None:
    async def _boom() -> None:
        raise PermissionError()

    app.add_api_route("/__test_permission_403_empty", _boom, methods=["GET"])
    try:
        response = client.get("/__test_permission_403_empty")
        assert response.status_code == 403
        body = response.json()
        assert body["detail"] == "forbidden"
        assert "request_id" in body
    finally:
        app.router.routes = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) != "/__test_permission_403_empty"
        ]
