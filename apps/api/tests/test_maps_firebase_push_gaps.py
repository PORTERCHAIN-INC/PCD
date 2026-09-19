"""GAP board tests — Maps / Firebase / Push (MAPS_FIREBASE_PUSH_NOTIF_DEV_TEST_CASES).

Covers:
  GAP-02 InvalidFcmToken / is_fcm_registration_token
  GAP-04 push_health contract keys (PushHealthStrip)
  GAP-01 client gate parity for registerBrowserPush (isFcmRegistrationToken ↔ Python)
  GAP-03 FCMService soft-fail when unconfigured
  GAP-05 polyline SSOT (@porterchain/maps; portal shims re-export only)
  GAP-06 chaos ↔ FAILURE_SCENARIOS naming aliases
  GAP-07 merchant NotificationCenter → registerBrowserPush
  GAP-08 mobile-driver collectPush FCM gate + Android channels
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from porterchain_api.notification_engine.device_service import (
    DeviceService,
    InvalidFcmToken,
    is_fcm_registration_token,
)

ROOT = Path(__file__).resolve().parents[3]


def _valid_fcm_token(suffix: str = "gap") -> str:
    # FCM instance tokens: <sender>:APA91...
    return f"430248198034:APA91{suffix}" + ("x" * 120)


# --- GAP-02 -----------------------------------------------------------------


@pytest.mark.parametrize(
    "token",
    [
        None,
        "",
        "short",
        "web-00000000-0000-0000-0000-000000000001",
        "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
        "ExponentPushToken[abc]",
        "no-apa91-prefix-but-long-enough-aaaaaaaaaaaaaaaa",
    ],
)
def test_gap02_is_fcm_registration_token_rejects_non_fcm(token: str | None) -> None:
    assert is_fcm_registration_token(token) is False


def test_gap02_is_fcm_registration_token_accepts_apa91() -> None:
    assert is_fcm_registration_token(_valid_fcm_token()) is True


def test_gap02_device_register_raises_invalid_fcm_token(db) -> None:
    svc = DeviceService()
    with pytest.raises(InvalidFcmToken, match="fcm_token_invalid"):
        svc.register(
            db,
            user_role="admin",
            user_id="admin-gap-02",
            fcm_token="web-deadbeef-dead-beef-dead-beefdeadbeef",
            platform="web",
        )
    with pytest.raises(InvalidFcmToken, match="fcm_token_invalid"):
        svc.register(
            db,
            user_role="driver",
            user_id="driver-gap-02",
            fcm_token="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            platform="expo",
        )
    db.rollback()


def test_gap02_device_register_accepts_valid_fcm(db) -> None:
    svc = DeviceService()
    device = svc.register(
        db,
        user_role="admin",
        user_id="admin-gap-02-ok",
        fcm_token=_valid_fcm_token("ok"),
        platform="web",
        notification_permission="granted",
    )
    assert device.id
    assert device.is_active is True
    assert ":APA91" in device.fcm_token
    active = svc.list_active(db, user_role="admin", user_id="admin-gap-02-ok")
    assert len(active) >= 1
    db.rollback()


# --- GAP-01 (registerBrowserPush client gate parity) ------------------------


def test_gap01_client_token_gate_matches_server_contract() -> None:
    """registerBrowserPush calls isFcmRegistrationToken before POST register.

    Portal TS (apps/*/src/lib/firebase-public.ts):
      token.includes(":APA91") && !token.startsWith("web-")
    Server is stricter (length, Expo). Client must never POST tokens the
    server will 400 — these samples must agree on reject/accept.
    """

    def ts_is_fcm_registration_token(token: str) -> bool:
        return ":APA91" in token and not token.startswith("web-")

    samples = [
        _valid_fcm_token(),
        "web-00000000-0000-0000-0000-000000000001",
        "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
        "short",
        "430248198034:APA91" + ("y" * 140),
    ]
    for tok in samples:
        server = is_fcm_registration_token(tok)
        client = ts_is_fcm_registration_token(tok)
        if client:
            assert server is True, f"client would POST rejected token: {tok[:40]}"
        if tok.startswith("web-"):
            assert client is False and server is False


def test_gap01_web_push_exposes_playwright_test_hook() -> None:
    """ADMIN_RUN_LIVE Playwright uses window.__PC_TEST_FCM_TOKEN__ (no VAPID)."""
    for rel in (
        "apps/admin/src/lib/web-push.ts",
        "apps/merchant-portal/src/lib/web-push.ts",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "__PC_TEST_FCM_TOKEN__" in text
        assert "registerBrowserPush" in text
        assert "isFcmRegistrationToken" in text


# --- GAP-04 -----------------------------------------------------------------


def test_gap04_push_health_contract_keys(db) -> None:
    from porterchain_api.notification_engine.admin_service import NotificationAdminService

    snap = NotificationAdminService().push_health(db)
    assert snap["tone"] in ("ok", "warn", "danger")
    assert isinstance(snap["issues"], list)

    fcm = snap["fcm"]
    for key in (
        "sdk_available",
        "credentials_configured",
        "production_ready",
        "production_ready_reason",
        "project_id",
        "push_enabled",
        "push_send",
        "app_env",
    ):
        assert key in fcm, f"missing fcm.{key}"

    devices = snap["devices"]
    for key in ("admin_active", "admin_users", "driver_active"):
        assert key in devices, f"missing devices.{key}"
        assert isinstance(devices[key], int)

    crit = snap["critical_24h"]
    for key in ("total", "delivered", "failed"):
        assert key in crit, f"missing critical_24h.{key}"
        assert isinstance(crit[key], int)

    assert "last_urgent_push" in snap
    if snap["last_urgent_push"] is not None:
        for key in ("id", "template_key", "priority", "status", "created_at"):
            assert key in snap["last_urgent_push"]


def test_gap04_push_health_warns_when_no_admin_devices(db) -> None:
    from porterchain_api.notification_engine.admin_service import NotificationAdminService

    snap = NotificationAdminService().push_health(db)
    if snap["devices"]["admin_users"] == 0:
        assert snap["tone"] in ("warn", "danger")
        assert any("admin" in i.lower() for i in snap["issues"])


# --- GAP-03 -----------------------------------------------------------------


@patch("porterchain_api.notification_engine.fcm_service.get_platform_settings")
@patch("porterchain_api.notification_engine.fcm_service._get_firebase_app", return_value=None)
def test_gap03_fcm_send_unconfigured_log_only(_mock_app, mock_settings) -> None:
    from porterchain_api.notification_engine.fcm_service import FCMService

    mock_settings.return_value = SimpleNamespace(
        push_enabled=True,
        push_send=True,
        firebase_project_id="proj",
    )
    ok, err, invalid = FCMService().send(
        _valid_fcm_token("fcm"),
        title="gap03",
        body="log-only",
        priority="high",
        category="orders",
    )
    assert ok is True
    assert err is None
    assert invalid is False


# --- GAP-05 -----------------------------------------------------------------


def test_gap05_portal_polyline_shims_reexport_shared_package() -> None:
    """Portal libs must re-export @porterchain/maps — no local decodePolyline body."""
    ssot = (ROOT / "packages/maps/src/polyline.ts").read_text(encoding="utf-8")
    assert "export function decodePolyline" in ssot
    assert 'encoding: "google" | "valhalla"' in ssot

    shims = [
        ROOT / "apps/driver-portal/src/lib/navigation-map.ts",
        ROOT / "apps/merchant-portal/src/lib/tracking-map.ts",
    ]
    for path in shims:
        text = path.read_text(encoding="utf-8")
        assert "@porterchain/maps" in text, path
        assert "export function decodePolyline" not in text, f"clone still in {path}"
        assert "decodePolyline" in text


def test_gap05_python_polyline_roundtrip_still_green() -> None:
    from porterchain_services.maps.polyline import decode_polyline, encode_polyline

    coords = [(43.6532, -79.3832), (43.6487, -79.3817)]
    encoded = encode_polyline(coords, precision=5)
    decoded = decode_polyline(encoded, precision=5)
    assert len(decoded) == 2
    assert abs(decoded[0][0] - coords[0][0]) < 1e-4


# --- GAP-06 -----------------------------------------------------------------


def test_gap06_canonical_chaos_matches_admin_ts() -> None:
    from porterchain_api.admin_engine.diagnostics_chaos import CANONICAL_CHAOS_SCENARIOS

    ts = (ROOT / "apps/admin/src/lib/diagnostics.ts").read_text(encoding="utf-8")
    block = re.search(r"CHAOS_SCENARIOS\s*=\s*\[(.*?)]\s*as const", ts, re.S)
    assert block, "CHAOS_SCENARIOS not found in diagnostics.ts"
    admin_ids = re.findall(r'"([a-z0-9_]+)"', block.group(1))
    assert tuple(admin_ids) == CANONICAL_CHAOS_SCENARIOS


def test_gap06_failure_scenario_aliases_resolve() -> None:
    from porterchain_api.admin_engine.diagnostics_chaos import (
        CANONICAL_CHAOS_SCENARIOS,
        CHAOS_ALIASES,
        resolve_chaos_scenario,
    )
    from porterchain_api.admin_engine.e2e_validation_catalog import FAILURE_SCENARIOS

    for name in (
        "fleetbase_offline",
        "google_maps_failure",
        "osrm_failure",
        "valhalla_failure",
        "redis_restart",
        "postgresql_restart",
        "websocket_failure",
        "vehicle_breakdown",
    ):
        assert name in FAILURE_SCENARIOS
        assert resolve_chaos_scenario(name) == name
        assert name in CANONICAL_CHAOS_SCENARIOS

    for failure_name, canonical in CHAOS_ALIASES.items():
        assert failure_name in FAILURE_SCENARIOS
        assert resolve_chaos_scenario(failure_name) == canonical
        assert canonical in CANONICAL_CHAOS_SCENARIOS

    assert resolve_chaos_scenario("firebase_failure") == "firebase_offline"
    assert resolve_chaos_scenario("driver_rejects") == "driver_reject"
    assert resolve_chaos_scenario("notification_failure") == "firebase_offline"


def test_gap06_chaos_test_accepts_failure_aliases(db, settings) -> None:
    from porterchain_api.admin_engine.diagnostics_service import AdminDiagnosticsService

    svc = AdminDiagnosticsService()
    for alias in ("firebase_failure", "driver_rejects", "fleetbase_adapter_failure"):
        out = svc.chaos_test(alias, db, settings)
        assert "Unknown scenario" not in " ".join(out.get("logs") or [])
        assert out.get("canonical_scenario")
        assert out["status"] in ("healthy", "warning", "critical", "ok", "warn", "danger")


# --- GAP-07 -----------------------------------------------------------------


def test_gap07_merchant_notification_center_wires_register_browser_push() -> None:
    path = ROOT / "apps/merchant-portal/src/components/dashboard/NotificationCenter.tsx"
    text = path.read_text(encoding="utf-8")
    assert "enablePush" in text
    assert 'import("@/lib/web-push")' in text
    assert "registerBrowserPush" in text
    web = (ROOT / "apps/merchant-portal/src/lib/web-push.ts").read_text(encoding="utf-8")
    assert "registerBrowserPush" in web
    assert "registerDevice" in web
    assert "__PC_TEST_FCM_TOKEN__" in web
    assert "orgId" in web
    e2e = (ROOT / "apps/merchant-portal/e2e/push.p0.spec.ts").read_text(encoding="utf-8")
    assert "MP-NTF-002" in e2e
    assert "__PC_TEST_FCM_TOKEN__" in e2e


# --- GAP-08 -----------------------------------------------------------------


def test_gap08_mobile_driver_collect_push_fcm_gate_and_channels() -> None:
    path = ROOT / "apps/mobile-driver/src/push.ts"
    text = path.read_text(encoding="utf-8")
    assert "export async function collectPush" in text
    assert "isFcmToken" in text
    assert ":APA91" in text
    assert "ops_critical" in text
    assert "assignments" in text
    assert "tracking" in text
    assert "registerPush" in text
