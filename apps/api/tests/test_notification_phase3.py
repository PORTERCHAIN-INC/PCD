"""Phase 3 — quiet hours, event alias, delivery logs."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from porterchain_shared.events.catalog import DomainEventType

from porterchain_api.notification_engine.event_router import _specs_for_event
from porterchain_api.notification_engine.user_settings import (
    UserSettingsService,
    is_within_quiet_hours,
)


def test_quiet_hours_wraps_midnight() -> None:
    assert is_within_quiet_hours(
        now=datetime(2026, 8, 8, 23, 0, tzinfo=ZoneInfo("America/Toronto")),
        quiet_start_hour=22,
        quiet_end_hour=7,
        timezone="America/Toronto",
    )
    assert is_within_quiet_hours(
        now=datetime(2026, 8, 8, 3, 0, tzinfo=ZoneInfo("America/Toronto")),
        quiet_start_hour=22,
        quiet_end_hour=7,
        timezone="America/Toronto",
    )
    assert not is_within_quiet_hours(
        now=datetime(2026, 8, 8, 12, 0, tzinfo=ZoneInfo("America/Toronto")),
        quiet_start_hour=22,
        quiet_end_hour=7,
        timezone="America/Toronto",
    )


def test_quiet_hours_mutes_push_not_email(db) -> None:
    svc = UserSettingsService()
    uid = f"u-{uuid.uuid4().hex[:8]}"
    svc.upsert(
        db,
        user_role="customer",
        user_id=uid,
        quiet_hours_enabled=True,
        quiet_start_hour=0,
        quiet_end_hour=23,
        timezone="UTC",
    )
    # Hour 23 is outside [0, 23). Pin noon so the mute does not depend on the clock.
    noon = datetime(2026, 8, 8, 12, 0, tzinfo=ZoneInfo("UTC"))

    class _Noon(datetime):
        @classmethod
        def now(cls, tz=None):
            return noon if tz is None else noon.astimezone(tz)

    with patch("porterchain_api.notification_engine.user_settings.datetime", _Noon):
        assert svc.should_mute_channel(
            db,
            user_role="customer",
            user_id=uid,
            channel="push",
            priority="normal",
            category="tracking",
        )
        assert not svc.should_mute_channel(
            db,
            user_role="customer",
            user_id=uid,
            channel="email",
            priority="normal",
            category="tracking",
        )
        assert not svc.should_mute_channel(
            db,
            user_role="customer",
            user_id=uid,
            channel="push",
            priority="critical",
            category="tracking",
        )
    db.rollback()


def test_merchant_invoice_generated_alias_matches_billed() -> None:
    payload = {"merchant_id": "m1", "email": "m@example.com", "merchant_email": "m@example.com"}
    a = _specs_for_event(DomainEventType.MERCHANT_BILLED, payload)
    b = _specs_for_event("merchant.invoice_generated", payload)
    assert {s["template_key"] for s in a} == {s["template_key"] for s in b}
    assert {s["recipient_type"] for s in a} == {s["recipient_type"] for s in b}
