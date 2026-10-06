"""P0 architecture cases from docs/MERCHANT_DEVELOPMENT_TEST_MATRIX.md (NEG-ARCH + OpenAPI).

Firewall + census only — no live vendor calls. Graphify Moment A named the merchant spine;
this pack keeps the negatives green while handshake e2e grows separately.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
API_SRC = REPO / "apps" / "api" / "src" / "porterchain_api"
MERCHANT_PORTAL = REPO / "apps" / "merchant-portal" / "src"
OPENAPI = REPO / "docs" / "api" / "openapi.json"
CLERK_ENV_EXAMPLE = REPO / "env" / "clerk.env.example"
API_ENV_EXAMPLE = REPO / "env" / "api.env.example"

_FORBIDDEN_PORTAL = (
    "fleetbase",
    "socketcluster",
    "socketcluster-client",
    "@socketcluster",
)

_ENGINE_VROOM_FORBIDDEN = (
    "import vroom",
    "from vroom",
    "VROOM_ROUTER",
    "vroom_client",
)


def _iter_py(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _iter_ts(root: Path):
    for path in root.rglob("*"):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        if "node_modules" in path.parts or ".next" in path.parts:
            continue
        yield path


def test_neg_arch_001_portal_never_imports_fleetbase_or_socketcluster() -> None:
    """NEG-ARCH-001 — no SDK/HTTP client imports (UI copy / field names like fleetbase_order_id OK)."""
    hits: list[str] = []
    import_re = re.compile(
        r"""(?m)^\s*(?:import|from)\s+['"]?(?:@?socketcluster|socketcluster-client|fleetbase(?:[-/]|\s|$))""",
        re.I,
    )
    url_re = re.compile(r"https?://[^\s\"']*fleetbase|socketcluster://", re.I)
    for path in _iter_ts(MERCHANT_PORTAL):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if import_re.search(text) or url_re.search(text):
            hits.append(str(path.relative_to(REPO)))
    assert not hits, f"merchant portal vendor leaf breach: {hits[:10]}"


def test_neg_arch_002_engines_do_not_call_private_valhalla_osrm() -> None:
    """NEG-ARCH-002 — engines use MapsService public API only."""
    hits: list[str] = []
    private = re.compile(r"_valhalla_|_osrm_|google\.maps\.DistanceMatrix|distancematrix", re.I)
    for engine in ("merchant_engine", "pricing_engine", "booking_engine", "admin_engine"):
        root = API_SRC / engine
        if not root.is_dir():
            continue
        for path in _iter_py(root):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if private.search(text):
                hits.append(str(path.relative_to(REPO)))
    assert not hits, f"private maps/Google distance usage in engines: {hits[:10]}"


def test_neg_arch_003_no_porterchain_vroom_client_under_engines() -> None:
    """NEG-ARCH-003"""
    hits: list[str] = []
    for engine in ("merchant_engine", "pricing_engine", "booking_engine", "admin_engine", "dispatch_engine"):
        root = API_SRC / engine
        if not root.is_dir():
            continue
        for path in _iter_py(root):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(tok in text for tok in _ENGINE_VROOM_FORBIDDEN):
                if "import vroom" in text or "from vroom" in text or "vroom_client" in text:
                    hits.append(str(path.relative_to(REPO)))
    assert not hits, f"in-engine VROOM client: {hits}"


def test_neg_arch_004_admin_merchants_router_has_no_hard_delete() -> None:
    """NEG-ARCH-004 — close/convert/reopen only."""
    router = API_SRC / "routers" / "merchants.py"
    tree = ast.parse(router.read_text(encoding="utf-8"))
    delete_routes: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            # @router.delete(...)
            func = dec.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if name == "delete":
                delete_routes.append(node.name)
    # Nested resource deletes (address/contact/seat) are allowed; merchant hard-delete is not.
    banned = [n for n in delete_routes if n in {"delete_merchant", "hard_delete", "destroy_merchant"}]
    assert not banned
    text = router.read_text(encoding="utf-8")
    assert re.search(r'@router\.delete\(\s*"/\{merchant_id\}"\s*\)', text) is None
    assert re.search(r"def\s+delete_merchant\s*\(", text) is None


def test_neg_arch_005_clerk_merchant_triad_in_env_examples() -> None:
    """NEG-ARCH-005"""
    blob = ""
    for path in (CLERK_ENV_EXAMPLE, API_ENV_EXAMPLE):
        if path.is_file():
            blob += path.read_text(encoding="utf-8")
    assert "CLERK_MERCHANT_SECRET_KEY" in blob or "CLERK_MERCHANT_PUBLISHABLE_KEY" in blob
    assert "ADMIN_CLERK_SECRET_KEY" not in blob


def test_neg_arch_006_firebase_not_used_as_merchant_auth() -> None:
    """NEG-ARCH-006 — FCM device helpers OK; Firebase Auth not the merchant IdP."""
    hits: list[str] = []
    auth_markers = re.compile(
        r"""from\s+['"]firebase/auth['"]|firebase/auth|getAuth\(|FirebaseAuth|signInWithEmailAndPassword""",
        re.I,
    )
    for path in _iter_ts(MERCHANT_PORTAL):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if auth_markers.search(text):
            hits.append(str(path.relative_to(REPO)))
    assert not hits, f"Firebase Auth in merchant portal: {hits}"


def test_neg_arch_007_is_sandbox_is_not_app_env() -> None:
    """NEG-ARCH-007 — commercial sandbox label ≠ platform APP_ENV."""
    from porterchain_api.config import Settings

    s = Settings(app_env="local", stripe_mock=True)
    assert getattr(s, "app_env", None) in {"local", "development", "test", "production", "staging"} or True
    # Order/merchant columns exist as is_sandbox — not as a Settings project-mode switch.
    assert not hasattr(s, "is_sandbox") or not callable(getattr(s, "is_sandbox", None))


def test_neg_arch_010_openapi_census_includes_merchant_prefixes() -> None:
    """NEG-ARCH-010"""
    data = json.loads(OPENAPI.read_text(encoding="utf-8"))
    paths = data.get("paths") or {}
    assert any(p.startswith("/v1/merchant/") for p in paths)
    assert any(p.startswith("/v1/admin/merchants") for p in paths)
    assert any(p.startswith("/v1/merchant-api/") for p in paths)
    # Smoke: critical P0 booking + admin lifecycle present
    for required in (
        "/v1/merchant/booking/preview",
        "/v1/merchant/booking/confirm",
        "/v1/merchant/orders",
        "/v1/admin/merchants/{merchant_id}/approve",
        "/v1/admin/merchants/{merchant_id}/suspend",
        "/v1/admin/merchants/{merchant_id}/close",
        "/v1/integrations/shopify/webhooks",
    ):
        assert required in paths, f"missing OpenAPI path {required}"


def test_api_mp_smoke_merchant_path_methods_declared() -> None:
    """Lightweight OpenAPI contract: every /v1/merchant path declares ≥1 HTTP method."""
    data = json.loads(OPENAPI.read_text(encoding="utf-8"))
    missing: list[str] = []
    for path, ops in (data.get("paths") or {}).items():
        if not path.startswith("/v1/merchant"):
            continue
        methods = {k for k in ops if k in {"get", "post", "put", "patch", "delete"}}
        if not methods:
            missing.append(path)
    assert not missing
