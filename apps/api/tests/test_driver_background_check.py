"""P1 — Checkr background screening → background_check_status."""

from __future__ import annotations

import hashlib
import hmac
import json
from uuid import uuid4

import pytest
from porterchain_services.checkr.client import verify_webhook_signature
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_engine.background_check_service import (
    DriverBackgroundCheckService,
)


def _driver(db: Session, *, license_verified: bool = True) -> Driver:
    suffix = uuid4().hex[:8]
    row = Driver(
        email=f"bg-{suffix}@test.porterchain.com",
        full_name=f"Background Driver {suffix}",
        status=DriverStatus.PENDING.value,
        clerk_user_id=f"clerk_bg_{suffix}",
        license_verified=license_verified,
        background_check_status="pending",
        documents={},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_apply_result_cleared(db: Session) -> None:
    driver = _driver(db)
    DriverBackgroundCheckService().apply_result(
        db,
        driver,
        status="cleared",
        invitation_id="inv_1",
        candidate_id="cand_1",
        report_id="rep_1",
    )
    db.commit()
    db.refresh(driver)

    assert driver.background_check_status == "cleared"
    entry = driver.documents.get("background_check") or {}
    assert entry.get("verified") is True
    assert entry.get("provider") == "checkr"
    assert entry.get("checkr_report_id") == "rep_1"


def test_consider_does_not_pass(db: Session) -> None:
    driver = _driver(db)
    DriverBackgroundCheckService().apply_result(db, driver, status="consider", report_id="rep_c")
    db.commit()
    db.refresh(driver)
    assert driver.background_check_status == "consider"
    assert (driver.documents.get("background_check") or {}).get("verified") is False


def test_webhook_report_completed_via_custom_id(db: Session, settings: Settings) -> None:
    driver = _driver(db)
    event = {
        "type": "report.completed",
        "data": {
            "object": {
                "id": "rep_live",
                "object": "report",
                "status": "complete",
                "result": "clear",
                "candidate_id": "cand_live",
                "candidate": {"id": "cand_live", "custom_id": driver.id},
            }
        },
    }
    ok = DriverBackgroundCheckService().apply_checkr_webhook(db, event)
    db.commit()
    db.refresh(driver)
    assert ok is True
    assert driver.background_check_status == "cleared"


def test_mock_screening_requires_license(db: Session, settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "driver_background_check_enabled", True)
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "checkr_mock", True)
    monkeypatch.setattr(settings, "checkr_api_key", "")

    driver = _driver(db, license_verified=False)
    with pytest.raises(PermissionError, match="license_verification_required"):
        DriverBackgroundCheckService().start_screening(db, settings, driver)


def test_mock_screening_clears(db: Session, settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "driver_background_check_enabled", True)
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "checkr_mock", True)
    monkeypatch.setattr(settings, "checkr_api_key", "")

    driver = _driver(db, license_verified=True)
    svc = DriverBackgroundCheckService()
    started = svc.start_screening(db, settings, driver)
    assert started["mock"] is True
    completed = svc.complete_mock(db, settings, driver, invitation_id=started["invitation_id"])
    db.commit()
    db.refresh(driver)
    assert completed["passed"] is True
    assert driver.background_check_status == "cleared"


def test_checkr_signature_helper() -> None:
    secret = "whsec_test"
    body = b'{"type":"report.completed"}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, sig, secret) is True
    assert verify_webhook_signature(body, f"sha256={sig}", secret) is True
    assert verify_webhook_signature(body, "bad", secret) is False
    assert verify_webhook_signature(body, None, secret) is False


def test_handle_webhook_rejects_bad_signature(
    db: Session, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "driver_background_check_enabled", True)
    monkeypatch.setattr(settings, "checkr_webhook_secret", "secret")
    payload = json.dumps({"type": "report.completed", "data": {"object": {}}}).encode()
    with pytest.raises(PermissionError, match="invalid_checkr_signature"):
        DriverBackgroundCheckService().handle_webhook(
            db,
            settings,
            payload=payload,
            signature="nope",
            event=json.loads(payload),
        )
