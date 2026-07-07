"""Standardized API response envelope contract.

Errors must expose the platform envelope ``{"success": false, "error":
{"code", "message"}}`` while keeping the legacy ``detail`` field for backward
compatibility during the incremental migration.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from porterchain_api.main import create_app
from porterchain_api.responses import error, error_payload, success


def test_success_envelope_helper() -> None:
    assert success({"id": 1}) == {"success": True, "data": {"id": 1}}


def test_error_envelope_helper() -> None:
    assert error("quote_not_found", "Quote not found") == {
        "success": False,
        "error": {"code": "quote_not_found", "message": "Quote not found"},
    }


def test_error_payload_preserves_detail() -> None:
    payload = error_payload("quote_not_found", "Quote not found", detail="quote_not_found")
    assert payload["success"] is False
    assert payload["error"] == {"code": "quote_not_found", "message": "Quote not found"}
    assert payload["detail"] == "quote_not_found"  # backward-compatible


def test_validation_error_uses_standard_envelope() -> None:
    with TestClient(create_app()) as client:
        # Missing required body fields -> RequestValidationError.
        resp = client.post("/v1/quotes", json={})
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"
    # Legacy structured detail array is preserved for existing clients.
    assert isinstance(body["detail"], list)


def test_http_exception_uses_standard_envelope() -> None:
    with TestClient(create_app()) as client:
        # Unauthenticated public tracking for a nonexistent order -> 404 with a
        # deterministic string code (independent of dev-bypass/auth config).
        resp = client.get("/v1/orders/PC-DOES-NOT-EXIST")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "order_not_found"
    assert body["detail"] == "order_not_found"  # string detail mirrored as code
    assert body["error"]["message"]
