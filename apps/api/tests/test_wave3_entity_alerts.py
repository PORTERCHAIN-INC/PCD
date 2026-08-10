"""Wave 3 entity alerts + job_assigned template."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from porterchain_api.admin_engine.notification_admin_service import NotificationAdminService
from porterchain_api.notification_engine.templates import TEMPLATES, template_meta


def test_job_assigned_template_exists() -> None:
    assert "job_assigned" in TEMPLATES
    assert template_meta("job_assigned").get("category") == "tracking"
    body = TEMPLATES["job_assigned"]["body"]
    assert "job" in body.lower()
    assert "{order_number}" in body or "{tracking_number}" in body


def test_entity_alerts_rejects_bad_type() -> None:
    svc = NotificationAdminService()
    try:
        svc.entity_alerts(MagicMock(), recipient_type="staff", recipient_id="x")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "invalid_recipient_type" in str(exc)


def test_entity_alerts_bundle_shape() -> None:
    svc = NotificationAdminService()
    db = MagicMock()
    svc.list_records = MagicMock(return_value=[])  # type: ignore[method-assign]
    svc._care_counts = MagicMock(  # type: ignore[method-assign]
        return_value={"open_exceptions": 1, "open_support_tickets": 0, "open_claims": 0}
    )

    # PreferenceService.get_all → empty
    pref_q = MagicMock()
    pref_q.filter.return_value.all.return_value = []
    # UserSettingsService.get → None; DeviceService → empty
    settings_q = MagicMock()
    settings_q.filter.return_value.first.return_value = None
    device_q = MagicMock()
    device_q.filter.return_value.order_by.return_value.all.return_value = []

    def query_side_effect(model):
        name = getattr(model, "__name__", str(model))
        if "Preference" in name:
            return pref_q
        if "UserSettings" in name or "NotificationUserSettings" in name:
            return settings_q
        if "Device" in name:
            return device_q
        return MagicMock()

    db.query.side_effect = query_side_effect
    db.get.return_value = None

    out = svc.entity_alerts(db, recipient_type="driver", recipient_id="d1", limit=5)
    assert out["recipient_type"] == "driver"
    assert out["recipient_id"] == "d1"
    assert out["recent"] == []
    assert out["care"]["open_exceptions"] == 1
    assert "tracking" in [p["category"] for p in out["preferences"]]
    assert out["settings"]["quiet_hours_enabled"] is False
    assert out["links"]["notifications_history"].endswith("history")
