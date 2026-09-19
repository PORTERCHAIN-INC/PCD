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


def test_route_screen_offline_banner_and_checklist() -> None:
    route = (MOBILE / "screens/RouteScreen.tsx").read_text()
    assert "offline-banner" in route
    assert "stop-checklist" in route
    assert "buildStopChecklist" in route
    assert "navigationUrl" in route
