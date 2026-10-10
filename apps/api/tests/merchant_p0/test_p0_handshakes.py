"""Merchant P0 handshakes from CodeGraph + Ripwire (non-duplicate of test_merchant_*).

CodeGraph: MapsService, MerchantBookingPreviewResponse, MODULE_PERMISSIONS, ShopifyShop
Ripwire: booking_preview, shopify thin router, confirm_booking, MapsService.route_with_source
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.auth.clerk_registry import clerk_app_configs, clerk_app_for_kind
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import MODULE_PERMISSIONS
from porterchain_api.schemas_merchant import MerchantBookingPreviewResponse
from porterchain_api.services.routing import resolve_route_distance
from porterchain_pricing import GeoPoint
from porterchain_services.maps.service import MapsService

from . import REPO_ROOT

API_SRC = REPO_ROOT / "apps" / "api" / "src" / "porterchain_api"
NAV_TS = REPO_ROOT / "apps" / "merchant-portal" / "src" / "lib" / "merchant-nav.ts"


@pytest.fixture(autouse=True)
def _clear_clerk_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("CLERK_"):
            monkeypatch.delenv(key, raising=False)


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-VAL-001")
def test_hs_val_maps_route_with_source_labels() -> None:
    """MapsService.route_with_source returns (leg, 'valhalla'|'osrm')."""
    svc = MapsService()
    svc.ctx = SimpleNamespace(
        settings=SimpleNamespace(
            routing_engine="valhalla",
            valhalla_url="http://valhalla.test",
            osrm_url="http://osrm.test",
            osrm_allow_public_demo=False,
        )
    )
    with (
        patch.object(svc, "_valhalla_route", return_value={"distance": 1000, "time": 120}),
        patch.object(svc, "_osrm_route", return_value=None),
    ):
        leg, source = svc.route_with_source((43.65, -79.38), (43.66, -79.39))
    assert leg is not None
    assert source == "valhalla"


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-OSRM-001")
def test_hs_osrm_fallback_when_valhalla_none() -> None:
    svc = MapsService()
    svc.ctx = SimpleNamespace(
        settings=SimpleNamespace(
            routing_engine="valhalla",
            valhalla_url="http://valhalla.test",
            osrm_url="http://osrm.test",
            osrm_allow_public_demo=False,
        )
    )
    with (
        patch.object(svc, "_valhalla_route", return_value=None),
        patch.object(svc, "_osrm_route", return_value={"distance": 900, "time": 100}),
    ):
        leg, source = svc.route_with_source((43.65, -79.38), (43.66, -79.39))
    assert leg is not None
    assert source == "osrm"


@pytest.mark.merchant_p0
@pytest.mark.tc_id("MP-RTE-002")
def test_neg_no_google_distance_in_routing_facade() -> None:
    """resolve_route_distance never labels source as google."""
    with patch("porterchain_api.services.routing.MapsService") as maps_cls:
        maps = MagicMock()
        maps.route_distance_meters.return_value = (1200, 180, "valhalla")
        maps_cls.return_value = maps
        _m, _s, source = resolve_route_distance(
            GeoPoint(lat=43.65, lng=-79.38),
            GeoPoint(lat=43.66, lng=-79.39),
        )
    assert source in {"valhalla", "osrm", "haversine"}
    assert "google" not in source.lower()

    text = (REPO_ROOT / "apps/api/src/porterchain_api/services/routing.py").read_text(encoding="utf-8")
    assert "google" not in text.lower()
    assert "DistanceMatrix" not in text


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-CLERK-001")
def test_hs_clerk_merchant_slot() -> None:
    settings = Settings(
        _env_file=None,
        jwt_secret="a" * 32,
        clerk_unified_mode=False,
        clerk_merchant_secret_key="sk_test_merchant",
        clerk_merchant_jwks_url="https://merchant.clerk.accounts.dev/.well-known/jwks.json",
        clerk_merchant_publishable_key="pk_test_merchant",
        clerk_customer_secret_key="sk_test_customer",
        clerk_customer_jwks_url="https://customer.clerk.accounts.dev/.well-known/jwks.json",
        clerk_customer_publishable_key="pk_test_customer",
        clerk_admin_secret_key="sk_test_admin",
        clerk_admin_jwks_url="https://admin.clerk.accounts.dev/.well-known/jwks.json",
        clerk_admin_publishable_key="pk_test_admin",
        clerk_driver_secret_key="sk_test_driver",
        clerk_driver_jwks_url="https://driver.clerk.accounts.dev/.well-known/jwks.json",
        clerk_driver_publishable_key="pk_test_driver",
        clerk_secret_key="",
        clerk_jwks_url="",
        clerk_publishable_key="",
    )
    apps = {a.kind: a for a in clerk_app_configs(settings)}
    assert "merchant" in apps
    merchant = clerk_app_for_kind(settings, "merchant")
    assert merchant is not None
    assert merchant.secret_key == "sk_test_merchant"
    assert "jwks" in merchant.jwks_url


@pytest.mark.merchant_p0
@pytest.mark.tc_id("API-SCHEMA-PREVIEW")
def test_preview_schema_contract() -> None:
    """CodeGraph contract: preview response carries distance + cents fields."""
    fields = set(MerchantBookingPreviewResponse.model_fields)
    for required in (
        "valid",
        "amount_cents",
        "currency",
        "distance_meters",
        "estimated_duration_minutes",
        "routing_source",
        "pricing_breakdown",
        "warnings",
        "error",
    ):
        assert required in fields
    sample = MerchantBookingPreviewResponse(
        valid=True,
        amount_cents=2500,
        distance_meters=5400,
        estimated_duration_minutes=18,
        routing_source="valhalla",
    )
    dumped = sample.model_dump()
    assert dumped["amount_cents"] == 2500
    assert dumped["distance_meters"] == 5400
    assert dumped["routing_source"] == "valhalla"


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-BOOK-ROUTER")
def test_thin_booking_preview_router() -> None:
    """Ripwire: booking_preview only delegates to _booking_flow.preview."""
    path = API_SRC / "routers" / "merchant" / "dashboard_booking.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "booking_preview")
    calls: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                calls.add(func.attr)
            elif isinstance(func, ast.Name):
                calls.add(func.id)
    assert "preview" in calls
    assert "require_module" in calls
    # No inline pricing / maps / Fleetbase in the thin router body.
    src = ast.get_source_segment(path.read_text(encoding="utf-8"), fn) or ""
    assert "MapsService" not in src
    assert "fleetbase" not in src.lower()
    assert "httpx" not in src


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-SHOP-ROUTER")
def test_thin_shopify_router() -> None:
    """Ripwire: merchant/shopify.py calls shopify_service, no webhook HMAC inline."""
    path = API_SRC / "routers" / "merchant" / "shopify.py"
    text = path.read_text(encoding="utf-8")
    assert "shopify_service" in text or "as shopify" in text
    assert "hmac" not in text.lower()
    assert "httpx" not in text
    assert text.count('require_module(ctx, "api_keys")') >= 3
    # Handlers stay thin: no SQLAlchemy query construction in this file.
    assert "db.query(" not in text
    assert "SessionLocal" not in text


@pytest.mark.merchant_p0
@pytest.mark.tc_id("MP-TEAM-002")
def test_mp_rbac_module_matrix_jobs() -> None:
    """Viewer/readonly cannot book; finance cannot manage api_keys; ops can book."""
    assert MerchantRole.READONLY not in MODULE_PERMISSIONS["book"]
    assert MerchantRole.FINANCE not in MODULE_PERMISSIONS["book"]
    assert MerchantRole.OPS in MODULE_PERMISSIONS["book"]
    assert MerchantRole.FINANCE not in MODULE_PERMISSIONS["api_keys"]
    assert MerchantRole.OWNER in MODULE_PERMISSIONS["api_keys"]
    assert MerchantRole.FINANCE in MODULE_PERMISSIONS["billing"]
    assert MerchantRole.OPS not in MODULE_PERMISSIONS["billing"]


@pytest.mark.merchant_p0
@pytest.mark.tc_id("NAV-JOB-PARITY")
def test_nav_module_keys_exist_in_rbac() -> None:
    """Portal NAV_MODULE_BY_HREF keys must exist in MODULE_PERMISSIONS (no UI drift)."""
    text = NAV_TS.read_text(encoding="utf-8")
    # Match string values in NAV_MODULE_BY_HREF object.
    keys = set(re.findall(r'NAV_MODULE_BY_HREF[\s\S]*?\};', text))
    assert keys, "NAV_MODULE_BY_HREF block not found"
    block = next(iter(keys))
    modules = set(re.findall(r':\s*"([a-z_]+)"', block))
    missing = sorted(m for m in modules if m not in MODULE_PERMISSIONS)
    assert not missing, f"nav modules missing from MODULE_PERMISSIONS: {missing}"
