"""P2 — Ontario abstract rules + compliance expiry revocation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_engine.abstract_service import DriverAbstractService
from porterchain_api.driver_engine.compliance_expiry_service import (
    DriverComplianceExpiryService,
)


def _driver(db: Session) -> Driver:
    suffix = uuid4().hex[:8]
    row = Driver(
        email=f"abs-{suffix}@test.porterchain.com",
        full_name=f"Abstract Driver {suffix}",
        status=DriverStatus.PENDING.value,
        clerk_user_id=f"clerk_abs_{suffix}",
        license_verified=True,
        insurance_verified=True,
        vehicle_verified=True,
        documents={},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_abstract_g_class_passes(db: Session, settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "driver_abstract_verification_enabled", True)
    driver = _driver(db)
    result = DriverAbstractService().submit(
        db,
        settings,
        driver,
        file_url="https://example.com/abstract.pdf",
        license_class="G",
        demerit_points=2,
        has_active_suspension=False,
        expires_at=(datetime.now(UTC) + timedelta(days=365)).date().isoformat(),
    )
    db.commit()
    db.refresh(driver)
    assert result["verified"] is True
    assert (driver.documents.get("abstract") or {}).get("verified") is True


def test_abstract_g2_rejected(db: Session, settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "driver_abstract_verification_enabled", True)
    driver = _driver(db)
    result = DriverAbstractService().submit(
        db,
        settings,
        driver,
        file_url="https://example.com/abstract.pdf",
        license_class="G2",
        demerit_points=0,
        has_active_suspension=False,
    )
    assert result["verified"] is False
    assert "license_class_graduated_or_learner" in (result.get("failure_reasons") or [])


def test_abstract_demerits_and_suspension(
    db: Session, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "driver_abstract_verification_enabled", True)
    monkeypatch.setattr(settings, "driver_abstract_max_demerits", 8)
    svc = DriverAbstractService()
    driver = _driver(db)

    high = svc.submit(
        db,
        settings,
        driver,
        file_url="https://example.com/a.pdf",
        license_class="G",
        demerit_points=12,
        has_active_suspension=False,
    )
    assert "demerit_points_exceeded" in (high.get("failure_reasons") or [])

    suspended = svc.submit(
        db,
        settings,
        driver,
        file_url="https://example.com/a.pdf",
        license_class="G",
        demerit_points=0,
        has_active_suspension=True,
    )
    assert "active_suspension" in (suspended.get("failure_reasons") or [])


def test_expiry_revokes_insurance_flag(db: Session) -> None:
    driver = _driver(db)
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    driver.documents = {
        "insurance": {
            "status": "verified",
            "verified": True,
            "expires_at": past,
            "url": "https://example.com/ins.pdf",
        }
    }
    db.commit()

    changed = DriverComplianceExpiryService().refresh_driver(db, driver)
    db.commit()
    db.refresh(driver)

    assert "insurance" in changed
    assert driver.insurance_verified is False
    assert (driver.documents.get("insurance") or {}).get("status") == "expired"


def test_compliance_sweep_updates_multiple(db: Session) -> None:
    d1 = _driver(db)
    d2 = _driver(db)
    past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    d1.documents = {"vehicle_registration": {"verified": True, "expires_at": past, "status": "verified"}}
    d1.vehicle_verified = True
    d2.documents = {"insurance": {"verified": True, "expires_at": future, "status": "verified"}}
    db.commit()

    result = DriverComplianceExpiryService().sweep(db, limit=50)
    db.refresh(d1)
    db.refresh(d2)

    assert result["updated"] >= 1
    assert d1.vehicle_verified is False
    assert d2.insurance_verified is True
