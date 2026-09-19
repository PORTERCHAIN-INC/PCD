"""Merchant API gateway documentation — scopes and documentation bundle (§7.1.9)."""

from __future__ import annotations

from porterchain_api.gateway_engine import merchant_api


def test_documentation_bundle_includes_scopes() -> None:
    bundle = merchant_api.documentation_bundle(api_base_url="http://localhost:8001")

    assert bundle["auth_header"] == "X-Api-Key"
    assert bundle["default_scopes"] == ["shipments:read", "shipments:write"]
    assert len(bundle["scopes"]) >= 2
    scope_ids = {row["id"] for row in bundle["scopes"]}
    assert scope_ids == {"shipments:read", "shipments:write"}
    assert "scope_endpoint_map" in bundle
    assert bundle["scope_endpoint_map"]["shipments:read"]
    assert bundle["scope_endpoint_map"]["shipments:write"]


def test_api_documentation_rows_reference_known_scopes() -> None:
    known = {row["id"] for row in merchant_api.MERCHANT_API_SCOPES}
    for row in merchant_api.API_DOCUMENTATION:
        assert row["scope"] in known
