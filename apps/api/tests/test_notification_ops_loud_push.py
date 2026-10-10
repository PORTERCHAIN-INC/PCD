"""FCM OS urgency + staff risk push budget (Jeff Dean P0)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.notification_engine.event_router import _specs_for_event
from porterchain_api.notification_engine.fcm_service import (
    CHANNEL_OPS_CRITICAL,
    CHANNEL_TRACKING,
    build_fcm_platform_config,
    resolve_channel_id,
)
from porterchain_api.notification_engine.preference_service import PreferenceService
from porterchain_shared.events.catalog import DomainEventType


STAFF_PUSH_EVENTS = {
    DomainEventType.DRIVER_REJECTED,
    DomainEventType.EXCEPTION_OPENED,
    DomainEventType.ORDER_DELAYED,
    DomainEventType.SLA_BREACHED,
    DomainEventType.ORDER_TEMP_EXCURSION,
    "driver.emergency",
    "incident.reported",
}

ROUTINE_NO_STAFF_PUSH = {
    DomainEventType.PARCEL_PICKED_UP,
    DomainEventType.PARCEL_DELIVERED,
    DomainEventType.DRIVER_ASSIGNED,
}


def _payload() -> dict:
    return {
        "customer_id": "cust-1",
        "merchant_id": "merch-1",
        "driver_id": "drv-1",
        "email": "c@example.com",
        "order_number": "ORD-1",
        "tracking_number": "TRK-1",
        "message": "x",
        "exception_type": "failed_attempt",
        "celsius": 12.5,
    }


@pytest.mark.parametrize("event_type", sorted(STAFF_PUSH_EVENTS, key=str))
def test_staff_risk_events_emit_push(event_type: str) -> None:
    specs = _specs_for_event(event_type, _payload())
    staff_push = [
        s
        for s in specs
        if s["channel"] == "push" and (s["recipient_type"] == "admin" or str(s["recipient_id"]).startswith("__staff:"))
    ]
    assert staff_push, f"expected staff push for {event_type}"


@pytest.mark.parametrize("event_type", sorted(ROUTINE_NO_STAFF_PUSH, key=str))
def test_routine_parcel_events_do_not_staff_push(event_type: str) -> None:
    specs = _specs_for_event(event_type, _payload())
    staff_push = [
        s
        for s in specs
        if s["channel"] == "push" and (s["recipient_type"] == "admin" or str(s["recipient_id"]).startswith("__staff:"))
    ]
    assert not staff_push, f"unexpected staff push for {event_type}: {staff_push}"


def test_driver_assigned_rings_driver_phone() -> None:
    """Assign must offer a high-priority job_assigned push so the phone rings for accept."""
    specs = _specs_for_event(DomainEventType.DRIVER_ASSIGNED, _payload())
    driver_push = [
        s
        for s in specs
        if s["channel"] == "push"
        and s["recipient_type"] == "driver"
        and s["recipient_id"] == "drv-1"
        and s["template_key"] == "job_assigned"
    ]
    assert len(driver_push) == 1, driver_push
    assert driver_push[0]["priority"] == "high"
    assert driver_push[0]["category"] == "orders"
    assert resolve_channel_id(priority="high", category="orders") == CHANNEL_OPS_CRITICAL


def test_job_assigned_push_carries_order_id_and_deep_link() -> None:
    """Lock-screen Accept needs order_id (+ optional /jobs/{id} deep link) in the push context."""
    from porterchain_api.notification_engine.fcm_service import JOB_OFFER_CATEGORY_ID

    payload = {
        **_payload(),
        "order_id": "ord-lock-1",
        "driver_deep_link": "/jobs/ord-lock-1",
    }
    specs = _specs_for_event(DomainEventType.DRIVER_ASSIGNED, payload)
    driver_push = next(
        s
        for s in specs
        if s["channel"] == "push" and s["template_key"] == "job_assigned"
    )
    ctx = driver_push["context"]
    assert ctx.get("order_id") == "ord-lock-1"
    assert (driver_push.get("deep_link") or ctx.get("driver_deep_link") or "").endswith(
        "ord-lock-1"
    )
    assert "job_assigned" in __import__(
        "porterchain_api.notification_engine.fcm_service", fromlist=["JOB_OFFER_TEMPLATES"]
    ).JOB_OFFER_TEMPLATES
    assert JOB_OFFER_CATEGORY_ID == "job_offer"


def test_build_fcm_job_offer_category() -> None:
    from porterchain_api.notification_engine.fcm_service import (
        JOB_OFFER_CATEGORY_ID,
        build_fcm_platform_config,
    )

    messaging = SimpleNamespace(
        AndroidConfig=MagicMock(side_effect=lambda **kw: ("android", kw)),
        AndroidNotification=MagicMock(side_effect=lambda **kw: ("android_notif", kw)),
        APNSConfig=MagicMock(side_effect=lambda **kw: ("apns", kw)),
        APNSPayload=MagicMock(side_effect=lambda **kw: ("apns_payload", kw)),
        Aps=MagicMock(side_effect=lambda **kw: ("aps", kw)),
    )
    build_fcm_platform_config(
        messaging,
        priority="high",
        channel_id=CHANNEL_OPS_CRITICAL,
        notification_category=JOB_OFFER_CATEGORY_ID,
    )
    notif_kwargs = messaging.AndroidNotification.call_args.kwargs
    assert notif_kwargs.get("click_action") == JOB_OFFER_CATEGORY_ID
    aps_kwargs = messaging.Aps.call_args.kwargs
    assert aps_kwargs.get("category") == JOB_OFFER_CATEGORY_ID


def test_resolve_channel_id_urgent() -> None:
    assert resolve_channel_id(priority="critical", category="orders") == CHANNEL_OPS_CRITICAL
    assert resolve_channel_id(priority="high", category="orders") == CHANNEL_OPS_CRITICAL
    assert resolve_channel_id(priority="normal", category="tracking") == CHANNEL_TRACKING


def test_build_fcm_platform_config_urgent() -> None:
    messaging = SimpleNamespace(
        AndroidConfig=MagicMock(side_effect=lambda **kw: ("android", kw)),
        AndroidNotification=MagicMock(side_effect=lambda **kw: ("android_notif", kw)),
        APNSConfig=MagicMock(side_effect=lambda **kw: ("apns", kw)),
        APNSPayload=MagicMock(side_effect=lambda **kw: ("apns_payload", kw)),
        Aps=MagicMock(side_effect=lambda **kw: ("aps", kw)),
    )
    android, apns = build_fcm_platform_config(
        messaging, priority="critical", channel_id=CHANNEL_OPS_CRITICAL
    )
    assert android[0] == "android"
    assert android[1]["priority"] == "high"
    assert apns[1]["headers"]["apns-priority"] == "10"
    aps_kwargs = messaging.Aps.call_args.kwargs
    assert aps_kwargs.get("custom_data", {}).get("interruption-level") == "time-sensitive"


def test_active_job_sticky_notification_wired_in_mobile_push() -> None:
    """D8 — ongoing/sticky active-job notification (no Apple Live Activity entitlement required)."""
    from pathlib import Path

    push = Path(__file__).resolve().parents[2] / "mobile-driver/src/push.ts"
    text = push.read_text()
    assert "setActiveJobNotification" in text
    assert "sticky: true" in text
    assert "porterchain-active-job" in text
    assert "Job in progress" in text


def test_admin_cannot_mute_critical_push(db) -> None:
    prefs = PreferenceService()
    uid = "admin-mute-test"
    prefs.upsert(
        db,
        user_role="admin",
        user_id=uid,
        category="orders",
        push_enabled=False,
        email_enabled=True,
        in_app_enabled=True,
    )
    db.commit()
    assert prefs.is_enabled(
        db, user_role="admin", user_id=uid, category="orders", channel="push", priority="critical"
    )
    assert prefs.is_enabled(
        db, user_role="admin", user_id=uid, category="orders", channel="push", priority="high"
    )
    assert not prefs.is_enabled(
        db, user_role="admin", user_id=uid, category="orders", channel="push", priority="normal"
    )


def test_staff_push_fanout_device_aware_email_fallback(db) -> None:
    """Push only to device-registered admins; high/critical without device → email."""
    import uuid

    from porterchain_api.admin_models import AdminUser
    from porterchain_api.notification_engine.device_service import DeviceService
    from porterchain_api.notification_engine.staff_fanout import expand_staff_specs, staff_sentinel

    with_device = AdminUser(
        clerk_user_id=f"clerk_{uuid.uuid4().hex[:12]}",
        email=f"dev-{uuid.uuid4().hex[:6]}@porterchain.test",
        role="dispatcher",
        is_active=True,
    )
    no_device = AdminUser(
        clerk_user_id=f"clerk_{uuid.uuid4().hex[:12]}",
        email=f"mail-{uuid.uuid4().hex[:6]}@porterchain.test",
        role="dispatcher",
        is_active=True,
    )
    db.add_all([with_device, no_device])
    db.flush()
    DeviceService().register(
        db,
        user_role="admin",
        user_id=with_device.id,
        fcm_token="430248198034:APA91" + ("x" * 140),
        platform="web",
    )
    db.flush()

    with patch(
        "porterchain_api.notification_engine.staff_fanout.ops_watch_emails",
        return_value={no_device.email.strip().lower()},
    ):
        expanded = expand_staff_specs(
            db,
            [
                {
                    "template_key": "sla_breached",
                    "channel": "push",
                    "recipient_type": "admin",
                    "recipient_id": staff_sentinel("ops"),
                    "context": {"title": "SLA"},
                    "search_tags": {},
                    "priority": "critical",
                    "category": "orders",
                }
            ],
        )
    by_id = {s["recipient_id"]: s for s in expanded}
    assert by_id[with_device.id]["channel"] == "push"
    assert by_id[with_device.id]["context"].get("email") == with_device.email
    assert by_id[no_device.id]["channel"] == "email"
    assert by_id[no_device.id]["recipient_address"] == no_device.email
    assert by_id[no_device.id]["search_tags"].get("fallback_reason") == "no_active_push_device"
    db.rollback()


@patch("porterchain_api.notification_engine.fcm_service.get_platform_settings")
@patch("porterchain_api.notification_engine.fcm_service._get_firebase_app", return_value=None)
def test_fcm_send_accepts_priority_kwargs(_mock_app, mock_settings) -> None:
    from porterchain_api.notification_engine.fcm_service import FCMService

    mock_settings.return_value = SimpleNamespace(
        push_enabled=True,
        push_send=True,
        firebase_project_id="proj",
    )
    ok, err, invalid = FCMService().send(
        "x" * 40 + ":APA91test",
        title="t",
        body="b",
        priority="critical",
        category="orders",
    )
    # no credentials app → log-only success
    assert ok is True
    assert err is None
    assert invalid is False


def test_staff_contact_uses_admin_phone(db) -> None:
    import uuid

    from porterchain_api.admin_models import AdminUser
    from porterchain_api.notification_engine.delivery_service import DeliveryService

    admin = AdminUser(
        clerk_user_id=f"clerk_{uuid.uuid4().hex[:12]}",
        email=f"sms-{uuid.uuid4().hex[:6]}@porterchain.test",
        phone="+14165550100",
        role="dispatcher",
        is_active=True,
    )
    db.add(admin)
    db.flush()
    email, phone = DeliveryService()._staff_contact(db, admin.id)
    assert email == admin.email
    assert phone == "+14165550100"
    db.rollback()


def test_push_health_snapshot(db) -> None:
    from porterchain_api.notification_engine.admin_service import NotificationAdminService

    snap = NotificationAdminService().push_health(db)
    assert snap["tone"] in ("ok", "warn", "danger")
    assert "admin_users" in snap["devices"]
    assert "delivered" in snap["critical_24h"]
    assert "credentials_configured" in snap["fcm"]
