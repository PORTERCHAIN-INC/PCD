"""Open MF-HS / UI seeds — Maps·Firebase·Push catalog (continue open batch).

Covers:
  MF-HS-07  TEST_CATALOG handshake probes (config / non-live)
  MF-HS-12  layered_architecture (no UI→Fleetbase)
  NA-02 / GAP-04 UI  PushHealthStrip + operations page wiring
  NOTIF-005 SW       admin firebase-messaging-sw.js background handler
  ARCH         portals must not hardcode Fleetbase :8000 / SocketCluster
"""

from __future__ import annotations

from pathlib import Path

import pytest

from porterchain_api.admin_engine.diagnostics_catalog import TEST_BY_ID, TEST_CATALOG, TEST_IDS
from porterchain_api.admin_engine.diagnostics_service import AdminDiagnosticsService
from porterchain_shared.config.settings import get_platform_settings

ROOT = Path(__file__).resolve().parents[3]

MF_HS_PROBE_IDS = (
    "firebase",
    "google_maps",
    "osrm",
    "valhalla",
    "notification_engine",
    "mailpit",
    "email_smtp",
    "layered_architecture",
)

_HEALTH = frozenset({"healthy", "warning", "critical"})


def test_mf_hs07_catalog_contains_handshake_probe_ids() -> None:
    ids = set(TEST_IDS)
    missing = [i for i in MF_HS_PROBE_IDS if i not in ids]
    assert not missing, f"TEST_CATALOG missing MF-HS probes: {missing}"
    for tid in MF_HS_PROBE_IDS:
        assert TEST_BY_ID[tid]["category"] in {
            "integrations",
            "engines",
            "infrastructure",
            "observability",
        }


def test_mf_hs07_non_live_probes_return_health_shape(settings) -> None:
    """Config-only / non-live probes — must not raise; status is HealthClass."""
    svc = AdminDiagnosticsService()
    platform = get_platform_settings()

    probes = {
        "firebase": svc._probe_firebase(platform),
        "google_maps": svc._probe_google_maps(platform, live=False, app_env=settings.app_env),
        "osrm": svc._probe_osrm(platform, live=False),
        "valhalla": svc._probe_valhalla(platform, live=False),
    }
    for name, probe in probes.items():
        assert "status" in probe, name
        assert probe["status"] in _HEALTH, f"{name}={probe['status']}"


def test_mf_hs07_run_test_safe_ids(db, settings) -> None:
    """run_test for ids that do not require external live HTTP (or degrade honestly)."""
    svc = AdminDiagnosticsService()
    for tid in ("firebase", "notification_engine", "layered_architecture", "mailpit", "email_smtp"):
        out = svc.run_test(tid, db, settings)
        assert out["id"] == tid
        assert out["status"] in _HEALTH
        assert "execution_ms" in out or "logs" in out
        assert isinstance(out.get("logs"), list)


def test_mf_hs07_notification_engine_probe(db) -> None:
    svc = AdminDiagnosticsService()
    probe = svc._engine_notifications(db)
    assert probe["status"] in _HEALTH
    assert "details" in probe
    assert "total" in probe["details"] or "active_devices" in probe["details"] or isinstance(
        probe["details"], dict
    )


def test_na02_push_health_strip_wires_api_and_operations_page() -> None:
    strip = (ROOT / "apps/admin/src/components/operations/PushHealthStrip.tsx").read_text(
        encoding="utf-8"
    )
    assert "notificationsApi.pushHealth" in strip
    assert 'data-testid="ops-push-health"' in strip
    assert "data.devices.admin_users" in strip
    assert "data.critical_24h" in strip
    assert "data.fcm.credentials_configured" in strip

    ops = (ROOT / "apps/admin/src/components/operations/OpsTowerShell.tsx").read_text(encoding="utf-8")
    assert "PushHealthStrip" in ops

    types = (ROOT / "apps/admin/src/lib/notifications.ts").read_text(encoding="utf-8")
    assert "export type PushHealth" in types
    for key in (
        "credentials_configured",
        "admin_users",
        "driver_active",
        "critical_24h",
        "last_urgent_push",
    ):
        assert key in types


def test_notif005_admin_firebase_messaging_sw_background_handler() -> None:
    sw = (ROOT / "apps/admin/public/firebase-messaging-sw.js").read_text(encoding="utf-8")
    assert "firebase-messaging-compat" in sw
    assert "onBackgroundMessage" in sw
    assert "showNotification" in sw
    assert "requireInteraction" in sw
    # FCM only — no Auth SDK.
    assert "firebase-auth" not in sw


def test_arch_portals_no_fleetbase_http_or_socketcluster() -> None:
    """MF-HS / ARCH: portals must not import SocketCluster or call Fleetbase HTTP for ops data.

    Admin may list Fleetbase console/API URLs in system-links (SSO / adapter target labels).
    Educational comments that ban SC are allowed.
    """
    for app, pkg in (
        ("admin", ROOT / "apps/admin/package.json"),
        ("merchant-portal", ROOT / "apps/merchant-portal/package.json"),
        ("driver-portal", ROOT / "apps/driver-portal/package.json"),
        ("customer", ROOT / "apps/customer/package.json"),
    ):
        if pkg.is_file():
            text = pkg.read_text(encoding="utf-8").lower()
            assert "socketcluster" not in text, f"{app} package.json depends on SocketCluster"

    # Business code: merchant / driver / customer must not hardcode Fleetbase API.
    strict_roots = [
        ROOT / "apps/merchant-portal/src",
        ROOT / "apps/driver-portal/src",
        ROOT / "apps/customer/src",
    ]
    hits: list[str] = []
    for portal in strict_roots:
        if not portal.is_dir():
            continue
        for path in portal.rglob("*"):
            if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            lowered = text.lower()
            for needle in ("localhost:8000", ":8000/api", "socketcluster-client", 'from "socketcluster'):
                if needle in lowered:
                    hits.append(f"{path.relative_to(ROOT)}: {needle}")

    # Admin: ban SC SDK imports only (console link may mention :8000 in system-links).
    admin_src = ROOT / "apps/admin/src"
    for path in admin_src.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        if path.name == "system-links.ts":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lowered = text.lower()
        for needle in ("socketcluster-client", 'from "socketcluster', "from 'socketcluster"):
            if needle in lowered:
                hits.append(f"{path.relative_to(ROOT)}: {needle}")

    assert not hits, "Portal Fleetbase/SC leaks:\n" + "\n".join(hits[:20])


def test_mf_hs12_layered_architecture_run_test(db, settings) -> None:
    out = AdminDiagnosticsService().run_test("layered_architecture", db, settings)
    assert out["status"] in _HEALTH
    # healthy = no frontend violations found
    if out["status"] == "critical":
        pytest.fail(f"layered_architecture critical: {out.get('logs')}")
