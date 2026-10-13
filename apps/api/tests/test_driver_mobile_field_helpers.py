"""Driver mobile field helpers — checklist order, maps policy, job-offer category pin."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MOBILE = ROOT / "apps/mobile-driver/src"
FCM = ROOT / "apps/api/src/porterchain_api/notification_engine/fcm_service.py"


def test_stop_checklist_ordered_steps() -> None:
    """One action at a time: Arrive → Scan → Proof → Complete (stop/stopFlow.ts)."""
    text = (MOBILE / "stop/stopFlow.ts").read_text()
    assert "export function deriveStop" in text
    for step in ("arrive", "scan", "proof", "complete"):
        assert f'"{step}"' in text
    assert text.index('"arrive"') < text.index('"scan"') < text.index('"proof"') < text.index('"complete"')

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
    """Earnings glance on Today reads /earnings/today; full wallet/statements live on the web portal."""
    today = (MOBILE / "screens/TodayScreen.tsx").read_text()
    api = (MOBILE / "api.ts").read_text()
    assert "fetchEarningsToday" in today and "today_cents" in today
    assert "/earnings/today" in api
    for field in ("today_cents", "week_cents", "month_cents"):
        assert field in api

def test_field_copy_hides_corelocation_and_apns_stacks() -> None:
    text = (MOBILE / "errorCopy.ts").read_text()
    assert "export function humanError" in text
    assert "kCLErrorDomain" in text
    for key in ("not_at_stop", "pretrip_required", "shift_required"):
        assert f"{key}:" in text
    push = (MOBILE / "push.ts").read_text()
    assert "iOS Expo Go yields APNs" not in push
    job = (MOBILE / "screens/JobScreen.tsx").read_text()
    assert "h.navigationUrl || h.destLat" in job
    today = (MOBILE / "screens/TodayScreen.tsx").read_text()
    assert 'testID="pretrip-check"' in today
    kit = (MOBILE / "ui/kit.tsx").read_text()
    assert "StatusBar.currentHeight" in kit

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
    job = (MOBILE / "screens/JobScreen.tsx").read_text()
    assert "Code under the barcode" in job

def test_handshake_proves_auth_before_dashboard() -> None:
    """Dashboard 403 (onboarding) must not drop Bearer-dev auth."""
    text = (MOBILE / "handshake.ts").read_text()
    assert "export function isOnboardingBlocked" in text
    compact = "".join(text.split())
    assert "Promise.all([fetchMe(),collectPush()" in compact
    assert text.index("fetchMe()") < text.index("fetchDashboard()")
    gate = (MOBILE / "gate.ts").read_text()
    assert "isOnboardingBlocked" in gate

def test_route_screen_offline_banner_and_checklist() -> None:
    """Job screen: offline banner, dispatch-route card with pickup checklist, navigation."""
    job = (MOBILE / "screens/JobScreen.tsx").read_text()
    banners = (MOBILE / "ui/SyncBanners.tsx").read_text()
    card = (MOBILE / "ui/RouteStopCard.tsx").read_text()
    assert "SyncBanners" in job and "offline-banner" in banners
    assert "RouteStopCard" in job
    assert "fetchDispatchChecklist" in card and 'testID="dispatch-stop"' in card
    assert "navigationUrl" in job and "openTurnByTurn" in card
