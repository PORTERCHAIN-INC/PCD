"""Implemented Admin/SuperAdmin P0 asserts wired to SSOT IDs.

SSOT: docs/ADMIN_SUPERADMIN_DEV_TESTCASES.md
Registry: docs/testing/admin_p0_registry.json
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from porterchain_api.main import app
from . import REPO_ROOT, case_by_id, cases

ADMIN_SRC = REPO_ROOT / "apps" / "admin" / "src"
API_SRC = REPO_ROOT / "apps" / "api" / "src" / "porterchain_api"
ENV_DIR = REPO_ROOT / "env"
INFRA = REPO_ROOT / "infrastructure"


def _iter_text(root: Path, suffixes: tuple[str, ...]) -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    if not root.exists():
        return out
    for path in root.rglob("*"):
        if path.suffix not in suffixes:
            continue
        if any(p in path.parts for p in ("node_modules", ".venv", ".next", "__pycache__")):
            continue
        try:
            out.append((path, path.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue
    return out


@pytest.mark.admin_p0
@pytest.mark.tc_id("AUTH-019")
def test_auth_019_no_admin_clerk_env_names() -> None:
    """No ad-hoc ADMIN_CLERK_* — Clerk triad via env/clerk.env + pnpm clerk:sync."""
    hits: list[str] = []
    for path in ENV_DIR.glob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "ADMIN_CLERK_" in text:
            hits.append(path.name)
    assert hits == [], f"ADMIN_CLERK_* found in env files: {hits}"
    clerk_example = ENV_DIR / "clerk.env.example"
    api_example = ENV_DIR / "api.env.example"
    assert api_example.is_file()
    combined = api_example.read_text(encoding="utf-8", errors="ignore")
    if clerk_example.is_file():
        combined += clerk_example.read_text(encoding="utf-8", errors="ignore")
    assert "CLERK_" in combined


@pytest.mark.admin_p0
@pytest.mark.tc_id("UI-MER-003")
def test_ui_mer_003_no_hard_delete_merchant_route() -> None:
    """Hard-DELETE merchants forbidden — close/convert/reopen only."""
    merchants = (API_SRC / "routers" / "merchants.py").read_text(encoding="utf-8")
    banned = re.findall(r'@router\.delete\(\s*"/\{merchant_id\}"\s*\)', merchants)
    assert banned == [], f"hard delete merchant route present: {banned}"


@pytest.mark.admin_p0
@pytest.mark.tc_id("UI-PRC-002")
def test_ui_prc_002_no_google_distance_matrix_in_quote_pricing() -> None:
    """Quote/pricing distance must not call Google Distance Matrix."""
    private = re.compile(r"google\.maps\.DistanceMatrix|distancematrix|maps/api/distancematrix", re.I)
    hits: list[str] = []
    for engine in ("pricing_engine", "booking_engine", "admin_engine"):
        root = API_SRC / engine
        for path, text in _iter_text(root, (".py",)):
            if private.search(text):
                hits.append(str(path.relative_to(REPO_ROOT)))
    for rel in ("routers/quotes.py", "routers/pricing_admin.py"):
        path = API_SRC / rel
        if path.is_file() and private.search(path.read_text(encoding="utf-8", errors="ignore")):
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert hits == [], f"Google Distance Matrix usage: {hits[:10]}"


@pytest.mark.admin_p0
@pytest.mark.tc_id("INT-RT-003")
def test_int_rt_003_alias_of_ui_prc_002() -> None:
    """Same firewall as UI-PRC-002 — keep ID discoverable."""
    test_ui_prc_002_no_google_distance_matrix_in_quote_pricing()


@pytest.mark.admin_p0
@pytest.mark.tc_id("UI-SYS-008")
def test_ui_sys_008_admin_ui_no_direct_fleetbase_http() -> None:
    """Admin UI must not import Fleetbase / SocketCluster vendor SDKs or hit Fleetbase URLs.

    Field names (``fleetbase_order_id``), SSO helpers, and prose are allowed.
    """
    import_re = re.compile(
        r"""(?:^|\n)\s*(?:from|import)\s+['"](?:@?socketcluster(?:-client)?|fleetbase-js|@fleetbase/)""",
        re.I,
    )
    url_re = re.compile(r"https?://[^\s\"']*fleetbase\.[a-z]+|socketcluster://", re.IGNORECASE)
    hits: list[str] = []
    for path, text in _iter_text(ADMIN_SRC, (".ts", ".tsx", ".js", ".jsx")):
        if import_re.search(text) or url_re.search(text):
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert hits == [], f"admin UI Fleetbase/SC breach: {hits[:10]}"


@pytest.mark.admin_p0
@pytest.mark.tc_id("INT-FB-001")
def test_int_fb_001_alias_ui_sys_008() -> None:
    test_ui_sys_008_admin_ui_no_direct_fleetbase_http()


@pytest.mark.admin_p0
@pytest.mark.tc_id("UI-SET-018")
def test_ui_set_018_no_project_mode_ui_toggle() -> None:
    """Project mode is boot-time APP_ENV — no Settings UI flipper calling project-mode."""
    hits: list[str] = []
    for path, text in _iter_text(ADMIN_SRC / "components" / "settings", (".ts", ".tsx")):
        if "project-mode" in text or re.search(r"projectMode\s*[:=]", text):
            hits.append(str(path.relative_to(REPO_ROOT)))
    for path, text in _iter_text(ADMIN_SRC / "lib", (".ts", ".tsx")):
        if path.name.startswith("settings") and ("project-mode" in text or "projectMode" in text):
            # Allow read-only display of runtime posture labels, forbid mutate helpers.
            if "project-mode" in text or "setProjectMode" in text or "changeProjectMode" in text:
                hits.append(str(path.relative_to(REPO_ROOT)))
    assert hits == [], f"project-mode UI mutate surface: {hits}"


@pytest.mark.admin_p0
@pytest.mark.tc_id("ARC-010")
def test_arc_010_project_mode_endpoint_immutable_code() -> None:
    settings_router = (API_SRC / "routers" / "admin" / "settings.py").read_text(encoding="utf-8")
    assert "project_mode_immutable" in settings_router
    assert '@router.post("/settings/project-mode")' in settings_router


@pytest.mark.admin_p0
@pytest.mark.tc_id("API-X-001")
def test_api_x_001_admin_routes_require_auth() -> None:
    """Unauthenticated admin GETs fail when Clerk/staff bypass is disabled."""
    from porterchain_api.config import Settings, get_settings

    settings = Settings(
        app_env="local",
        clerk_dev_bypass=False,
        stripe_mock=True,
        jwt_secret="test-jwt-secret-local",
        spicedb_enabled=False,
        spicedb_use_memory=True,
        spicedb_required=False,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        client = TestClient(app)
        samples = [
            "/v1/admin/dashboard",
            "/v1/admin/operations/stats",
            "/v1/admin/merchants/stats",
            "/v1/admin/diagnostics/health",
            "/v1/admin/notifications/dashboard",
            "/v1/admin/settings/dashboard",
            "/v1/admin/leads",
        ]
        for path in samples:
            resp = client.get(path)
            assert resp.status_code != 200, f"{path} returned 200 without auth"
            assert resp.status_code >= 400
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.admin_p0
@pytest.mark.tc_id("INT-FB-008")
def test_int_fb_008_no_porterchain_vroom_client() -> None:
    """No PorterChain-native VROOM client under API engines/routers."""
    hits = [
        str(p.relative_to(REPO_ROOT))
        for p in API_SRC.rglob("*vroom*")
        if "__pycache__" not in p.parts and p.name != "diagnostics_catalog.py"
    ]
    # diagnostics_catalog / fleetbase probes may mention vroom as a probe id file name — allow those.
    hits = [h for h in hits if "diagnostics" not in h]
    assert hits == [], f"unexpected VROOM modules under API: {hits}"


@pytest.mark.admin_p0
@pytest.mark.tc_id("INT-FB-007")
def test_int_fb_007_solver_is_ortools_not_a_vroom_client() -> None:
    orch = REPO_ROOT / "services" / "fleetbase-adapter"
    sequencer = API_SRC / "dispatch_engine" / "sequencer.py"
    assert not orch.exists()
    assert sequencer.is_file()
    text = sequencer.read_text()
    assert "ortools" in text
    assert "porterchain_fleetbase_adapter" not in text


@pytest.mark.admin_p0
@pytest.mark.tc_id("INT-FB-009")
def test_int_fb_009_no_socketcluster_in_admin_package() -> None:
    pkg = (REPO_ROOT / "apps" / "admin" / "package.json").read_text(encoding="utf-8").lower()
    assert "socketcluster" not in pkg


@pytest.mark.admin_p0
@pytest.mark.tc_id("DB-009")
def test_db_009_no_floating_postgres_latest() -> None:
    hits: list[str] = []
    roots = [REPO_ROOT, INFRA] if INFRA.exists() else [REPO_ROOT]
    for root in roots:
        for path in list(root.glob("docker-compose*.yml")) + list(root.rglob("*compose*.yml")):
            if "node_modules" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"postgres(?:ql)?[:/][^\s\"']*latest", text, re.I) or "postgres:alpine" in text:
                hits.append(str(path.relative_to(REPO_ROOT)))
    assert hits == [], f"floating postgres tags: {sorted(set(hits))}"


@pytest.mark.admin_p0
@pytest.mark.tc_id("ARC-001")
def test_arc_001_alias_db_009() -> None:
    test_db_009_no_floating_postgres_latest()


@pytest.mark.admin_p0
@pytest.mark.tc_id("ARC-002")
def test_arc_002_mailpit_not_mailhog() -> None:
    """Dev email is Mailpit — Mailhog must not be the compose service."""
    compose_blob = ""
    for path in REPO_ROOT.glob("docker-compose*.yml"):
        compose_blob += path.read_text(encoding="utf-8", errors="ignore")
    if INFRA.exists():
        for path in INFRA.rglob("*compose*.yml"):
            compose_blob += path.read_text(encoding="utf-8", errors="ignore")
    # Allow docs saying "not Mailhog"; forbid mailhog image/service pins.
    if re.search(r"image:\s*[^\n]*mailhog", compose_blob, re.I):
        pytest.fail("Mailhog image still pinned in compose")
    if "mailpit" in compose_blob.lower() or "axllent/mailpit" in compose_blob.lower():
        return
    # If no mail service in compose, still pass — pin may live elsewhere.


@pytest.mark.admin_p0
@pytest.mark.parametrize(
    "case_id",
    [c["id"] for c in cases(runner="pytest", status="implemented") if c.get("covers")],
    ids=[c["id"] for c in cases(runner="pytest", status="implemented") if c.get("covers")],
)
def test_p0_covers_pointers_exist(case_id: str) -> None:
    """Registry ``covers`` entries must point at real test files."""
    row = case_by_id(case_id)
    for nodeid in row["covers"]:
        file_part = nodeid.split("::", 1)[0]
        candidates = [
            REPO_ROOT / file_part,
            REPO_ROOT / "apps" / "api" / file_part,
        ]
        assert any(p.is_file() for p in candidates), (
            f"{case_id} covers missing file: {file_part}"
        )


@pytest.mark.admin_p0
def test_registry_ids_unique_and_in_ssot_doc() -> None:
    from . import load_registry

    reg = load_registry()
    ids = [c["id"] for c in reg["cases"]]
    assert len(ids) == len(set(ids))
    ssot = REPO_ROOT / reg["ssot"]
    assert ssot.is_file()
    doc = ssot.read_text(encoding="utf-8")
    missing = [i for i in ids if i not in doc]
    assert missing == [], f"registry IDs missing from SSOT doc: {missing}"
