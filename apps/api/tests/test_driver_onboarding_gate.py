"""Local driver ops gate — compliance complete vs blocked."""

from __future__ import annotations

from uuid import uuid4

import pytest

from porterchain_api.admin_models import Driver
from porterchain_api.auth.dev import DEV_BYPASS_DRIVER_EMAIL, resolve_dev_bypass_driver
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_engine.onboarding_service import (
    evaluate_driver_onboarding,
    require_fully_onboarded_driver,
)


def _driver(**overrides: object) -> Driver:
    suffix = uuid4().hex[:8]
    row = Driver(
        email=f"gate-{suffix}@porterchain.test",
        full_name=f"Gate {suffix}",
        status=DriverStatus.APPROVED.value,
        clerk_user_id=f"clerk_gate_{suffix}",
        license_verified=False,
        insurance_verified=False,
        vehicle_verified=False,
        background_check_status="pending",
        documents={},
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def test_incomplete_driver_blocked_when_abstract_required(settings) -> None:
    settings.driver_abstract_verification_enabled = True
    driver = _driver()
    snap = evaluate_driver_onboarding(driver, settings=settings)
    assert snap["ready"] is False
    for key in ("documents_uploaded", "vehicle_verified", "abstract_verified"):
        assert key in snap["blockers"]
    with pytest.raises(PermissionError, match="driver_onboarding_blocked:"):
        require_fully_onboarded_driver(driver, settings=settings)


def test_cleared_seed_driver_ready_with_abstract(settings) -> None:
    settings.driver_abstract_verification_enabled = True
    driver = _driver(
        license_verified=True,
        insurance_verified=True,
        vehicle_verified=True,
        background_check_status="cleared",
        documents={
            "files": [
                {"doc_type": "driver_license", "file_url": "https://example.test/l.pdf"},
                {"doc_type": "insurance", "file_url": "https://example.test/i.pdf"},
                {"doc_type": "vehicle_registration", "file_url": "https://example.test/r.pdf"},
            ],
            "abstract": {"verified": True, "status": "complete"},
        },
    )
    snap = evaluate_driver_onboarding(driver, settings=settings)
    assert snap["ready"] is True
    assert snap["blockers"] == []
    require_fully_onboarded_driver(driver, settings=settings)


def test_dev_bypass_prefers_seeded_marco(db) -> None:
    junk = _driver(email=f"junk-{uuid4().hex[:8]}@svc.test")
    db.add(junk)
    db.flush()
    marco = db.query(Driver).filter(Driver.email == DEV_BYPASS_DRIVER_EMAIL).first()
    if marco is None:
        pytest.skip("seed marco@porterchain.com is not in this database")
    picked = resolve_dev_bypass_driver(db)
    assert picked is not None
    assert picked.email == DEV_BYPASS_DRIVER_EMAIL
    assert picked.id == marco.id


def test_expired_insurance_clears_ready(db, settings) -> None:
    from datetime import UTC, datetime, timedelta

    from porterchain_api.driver_engine.compliance_expiry_service import DriverComplianceExpiryService

    settings.driver_abstract_verification_enabled = False
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    driver = _driver(
        license_verified=True,
        insurance_verified=True,
        vehicle_verified=True,
        background_check_status="cleared",
        documents={
            "files": [
                {"doc_type": "driver_license", "file_url": "https://example.test/l.pdf"},
                {"doc_type": "insurance", "file_url": "https://example.test/i.pdf"},
                {"doc_type": "vehicle_registration", "file_url": "https://example.test/r.pdf"},
            ],
            "insurance": {
                "verified": True,
                "status": "verified",
                "expires_at": past,
                "url": "https://example.test/i.pdf",
            },
        },
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    DriverComplianceExpiryService().refresh_and_commit(db, driver)
    snap = evaluate_driver_onboarding(driver, settings=settings)
    assert snap["ready"] is False
    assert "insurance_verified" in snap["blockers"]
