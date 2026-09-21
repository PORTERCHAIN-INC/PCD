"""Driver mobile field helpers — checklist order, maps policy, job-offer category pin."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MOBILE = ROOT / "apps/mobile-driver/src"
FCM = ROOT / "apps/api/src/porterchain_api/notification_engine/fcm_service.py"


def test_stop_checklist_ordered_steps() -> None:
    text = (MOBILE / "stopChecklist.ts").read_text()
    assert "buildStopChecklist" in text
    for step in ("arrive", "scan", "pod", "leave"):
        assert f'"{step}"' in text or f"'{step}'" in text
    assert text.index('"arrive"') < text.index('"scan"')
    assert text.index('"scan"') < text.index('"pod"')
    assert text.index('"pod"') < text.index('"leave"')


def test_maps_prefers_valhalla_url_no_google_dir() -> None:
    text = (MOBILE / "maps.ts").read_text()
    assert "navigationUrl" in text
    assert "google.com/maps/dir" not in text
    assert "geo:" in text


def test_job_offer_category_matches_fcm_and_push() -> None:
    push = (MOBILE / "push.ts").read_text()
    fcm = FCM.read_text()
    assert 'JOB_OFFER_CATEGORY = "job_offer"' in push
    assert 'JOB_OFFER_CATEGORY_ID = "job_offer"' in fcm
    assert "JOB_OFFER_ACCEPT" in push and "JOB_OFFER_DECLINE" in push
    assert "setActiveJobNotification" in push
    assert 'sound: "default"' not in push


def test_soft_offline_stale_constant() -> None:
    text = (MOBILE / "location.ts").read_text()
    assert "STALE_LOCATION_MS" in text
    assert "maybeSoftOfflineOnStale" in text
    assert "setAvailability" in text


def test_money_screen_reads_wallet_and_earnings_contract() -> None:
    """D7 — MoneyScreen fields must stay aligned with api.ts earnings/wallet paths."""
    money = (MOBILE / "screens/MoneyScreen.tsx").read_text()
    api = (MOBILE / "api.ts").read_text()
    types = (MOBILE / "types.ts").read_text()
    assert "fetchWallet" in money and "fetchEarnings" in money
    assert "refreshToken" in money
    assert "/wallet" in api and "/earnings" in api
    assert "/earnings/statements" in api
    for field in ("balance_cents", "today_cents", "week_cents", "month_cents"):
        assert field in types or field in money


def test_field_copy_hides_corelocation_and_apns_stacks() -> None:
    text = (MOBILE / "fieldCopy.ts").read_text()
    assert "export function humanFieldCopy" in text
    assert "export function fieldWarning" in text
    assert "kCLErrorDomain" in text
    assert 'key === "not_at_stop"' in text
    assert 'key === "pretrip_required"' in text
    assert 'key === "shift_required"' in text
    push = (MOBILE / "push.ts").read_text()
    assert "iOS Expo Go yields APNs" not in push
    route = (MOBILE / "screens/RouteScreen.tsx").read_text()
    assert "handshake.navigationUrl || handshake.destLat" in route
    assert "includeBottomSafeArea={false}" in route
    assert "PretripRow" in route
    assert 'testID="pretrip-check"' in route
    screen = (MOBILE / "ui/Screen.tsx").read_text()
    assert "StatusBar.currentHeight" in screen


def test_pretrip_checklist_keys_match_api() -> None:
    text = (MOBILE / "pretrip.ts").read_text()
    for key in ("lights", "tires", "plates", "leaks", "winter_kit"):
        assert f'id: "{key}"' in text
    api = (MOBILE / "api.ts").read_text()
    compact = "".join(api.split())
    assert "pretrip:pretrip??null" in compact


def test_package_scan_camera_is_qr_and_code128_only() -> None:
    scanner = (MOBILE / "ui/BarcodeScannerModal.tsx").read_text()
    assert 'barcodeTypes: ["qr", "code128"]' in scanner
    assert "ean13" not in scanner
    field = (MOBILE / "ui/FieldOpsPanel.tsx").read_text()
    assert "PorterChain QR or tracking line" in field


def test_handshake_proves_auth_before_dashboard() -> None:
    """Dashboard 403 (onboarding) must not drop Bearer-dev auth."""
    text = (MOBILE / "handshake.ts").read_text()
    assert "export function isOnboardingBlocked" in text
    compact = "".join(text.split())
    assert "Promise.all([fetchMe(),collectPush()])" in compact
    assert text.index("fetchMe()") < text.index("fetchDashboard()")
    gate = (MOBILE / "gate.ts").read_text()
    assert "isOnboardingBlocked" in gate


def test_route_screen_offline_banner_and_checklist() -> None:
    route = (MOBILE / "screens/RouteScreen.tsx").read_text()
    assert "offline-banner" in route
    assert "stop-checklist" in route
    assert "buildStopChecklist" in route
    assert "navigationUrl" in route
