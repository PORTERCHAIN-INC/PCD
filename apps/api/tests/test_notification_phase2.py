"""Phase 2 — prefs binding, retry sweeper, defaults."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.preference_service import PreferenceService
from porterchain_api.notification_engine.retry_sweeper import sweep_notification_retries


def test_defaults_sms_off_marketing_off(db) -> None:
    prefs = PreferenceService()
    uid = f"u-{uuid.uuid4().hex[:8]}"
    assert prefs.is_enabled(db, user_role="customer", user_id=uid, category="booking", channel="email")
    assert not prefs.is_enabled(db, user_role="customer", user_id=uid, category="booking", channel="sms")
    assert not prefs.is_enabled(db, user_role="customer", user_id=uid, category="marketing", channel="email")
    db.rollback()


def test_merchant_portal_sync_blocks_booking_email(db) -> None:
    prefs = PreferenceService()
    mid = f"merch-{uuid.uuid4().hex[:8]}"
    prefs.sync_merchant_portal_prefs(
        db,
        merchant_id=mid,
        portal_prefs={
            "order_booked": True,
            "order_delivered": True,
            "order_failed": True,
            "invoice_generated": True,
            "payment_received": True,
            "claim_updates": True,
            "support_replies": True,
            "weekly_summary": False,
            "channels": {"email": False, "in_app": True},
        },
    )
    # CASL: booking email is transactional and locked on, even with the email channel off.
    assert prefs.is_enabled(
        db, user_role="merchant", user_id=mid, category="booking", channel="email"
    )
    assert not prefs.is_enabled(
        db, user_role="merchant", user_id=mid, category="marketing", channel="email"
    )
    assert prefs.is_enabled(
        db, user_role="merchant", user_id=mid, category="booking", channel="in_app"
    )

    prefs.sync_merchant_portal_prefs(
        db,
        merchant_id=mid,
        portal_prefs={
            "order_booked": False,
            "channels": {"email": True, "in_app": True},
        },
    )
    # Transactional email stays locked on (CASL); the bell copy is what the toggle mutes.
    assert prefs.is_enabled(
        db, user_role="merchant", user_id=mid, category="booking", channel="email"
    )
    db.rollback()


def test_retry_sweeper_requeues_due(db) -> None:
    engine = get_notification_engine()
    rec = engine.dispatch(
        db,
        event_type="test.retry",
        template_key="system_alert",
        channel="email",
        recipient_type="customer",
        recipient_id=f"c-{uuid.uuid4().hex[:8]}",
        recipient_address="retry@example.com",
        context={"message": "retry me", "title": "Retry", "body": "retry"},
    )
    assert rec is not None
    rec.status = "failed"
    rec.next_retry_at = datetime.now(UTC) - timedelta(seconds=5)
    rec.retry_count = 1
    db.flush()

    result = sweep_notification_retries(db)
    assert result["requeued"] >= 1
    db.refresh(rec)
    assert rec.status == "queued"
    db.rollback()
