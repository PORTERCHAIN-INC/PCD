"""Driver app Settings sync, PIPEDA request, and the lite document list."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from porterchain_api.routers.driver import shift
from porterchain_driver.documents import DocumentsService


def _ctx(**driver):
    base = dict(id="d1", performance={}, documents={}, license_verified=False,
                insurance_verified=False, vehicle_verified=False)
    return SimpleNamespace(driver=SimpleNamespace(**{**base, **driver}))


def test_settings_merge_and_drop_bad_values():
    ctx = _ctx(performance={"rating_avg": 4.9})
    with patch.object(shift, "db_transaction", lambda db: nullcontext()):
        out = shift.put_app_settings(
            {"settings": {"nav_app": "waze", "voice": False, "language": "de", "text_scale": 9, "evil": 1}},
            ctx, db=MagicMock())
    assert out == {"settings": {"nav_app": "waze", "voice": False}}
    assert ctx.driver.performance["rating_avg"] == 4.9  # other performance data kept
    with patch.object(shift, "db_transaction", lambda db: nullcontext()):
        out = shift.put_app_settings({"battery_saver_pct": 25}, ctx, db=MagicMock())
    assert out["settings"] == {"nav_app": "waze", "voice": False, "battery_saver_pct": 25}
    assert shift.get_app_settings(ctx) == out


def test_privacy_request_opens_a_ticket():
    ctx = _ctx()
    with patch.object(shift, "db_transaction", lambda db: nullcontext()), patch.object(
        shift.svc.platform.support, "create_ticket", return_value={"id": "T-1"}
    ) as ct:
        out = shift.privacy_request({"kind": "access"}, ctx, db=MagicMock())
    assert out == {"status": "received", "kind": "access", "reference": "T-1", "sla_days": 30}
    assert ct.call_args.kwargs["category"] == "privacy"
    with pytest.raises(HTTPException) as e:
        shift.privacy_request({"kind": "nope"}, ctx, db=MagicMock())
    assert e.value.status_code == 422


def test_lite_list_drops_inline_bytes_and_includes_work_permit():
    driver = _ctx(documents={
        "license": {"url": "data:image/jpeg;base64," + "A" * 5000, "status": "pending_review", "expires_at": "2027-01-01"},
        "insurance": {"url": "https://files.example/ins.pdf", "status": "verified", "verified": True},
    }).driver
    docs = {d["type"]: d for d in DocumentsService().list_documents_lite(driver)}
    assert docs["license"]["url"] is None and docs["license"]["has_file"] is True
    assert docs["license"]["expires_at"] == "2027-01-01"
    assert docs["insurance"]["url"].startswith("https://")
    assert docs["work_permit"]["status"] == "missing" and docs["work_permit"]["has_file"] is False
