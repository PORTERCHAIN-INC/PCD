"""P0 — Stripe Identity → driver license_verified via existing portal doc sync."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.booking_engine.stripe_webhook_service import StripeWebhookService
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_engine.verification_service import DriverVerificationService


def _driver(db: Session, *, license_verified: bool = False) -> Driver:
    suffix = uuid4().hex[:8]
    row = Driver(
        email=f"identity-{suffix}@test.porterchain.com",
        full_name=f"Identity Driver {suffix}",
        status=DriverStatus.PENDING.value,
        clerk_user_id=f"clerk_identity_{suffix}",
        license_verified=license_verified,
        documents={},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_apply_identity_session_sets_license_verified(db: Session) -> None:
    driver = _driver(db)
    svc = DriverVerificationService()
    svc.apply_identity_session(
        db,
        driver,
        session_id="vs_test_1",
        verified=True,
        status="verified",
        document_summary={"type": "driving_license", "number": "D1234567"},
    )
    db.commit()
    db.refresh(driver)

    assert driver.license_verified is True
    license_doc = driver.documents.get("license") or {}
    assert license_doc.get("verified") is True
    assert license_doc.get("provider") == "stripe_identity"
    assert license_doc.get("verification_source") == "auto"
    assert license_doc.get("stripe_verification_session_id") == "vs_test_1"
    assert license_doc.get("reference_number") == "D1234567"


def test_stripe_webhook_identity_verified_updates_driver(db: Session, settings: Settings) -> None:
    driver = _driver(db)
    event = {
        "id": str(uuid4()),
        "type": "identity.verification_session.verified",
        "data": {
            "object": {
                "id": "vs_live_test",
                "status": "verified",
                "metadata": {
                    "porterchain_driver_id": driver.id,
                    "purpose": "driver_license",
                },
                "verified_outputs": {
                    "document": {
                        "type": "driving_license",
                        "number": "ON998877",
                        "expiration_date": {"year": 2028, "month": 6, "day": 15},
                    }
                },
            }
        },
    }

    result = StripeWebhookService().handle(db, settings, event)
    db.refresh(driver)

    assert result == {"status": "ok"}
    assert driver.license_verified is True
    license_doc = driver.documents.get("license") or {}
    assert license_doc.get("expires_at") == "2028-06-15"
    assert license_doc.get("reference_number") == "ON998877"


def test_mock_identity_complete_local_only(db: Session, settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "driver_identity_verification_enabled", True)
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "stripe_mock", True)
    monkeypatch.setattr(settings, "stripe_secret", "")

    driver = _driver(db)
    svc = DriverVerificationService()
    started = svc.start_identity_session(db, settings, driver)
    assert started["mock"] is True
    completed = svc.complete_mock_identity(db, settings, driver, session_id=started["session_id"])
    db.commit()
    db.refresh(driver)

    assert completed["verified"] is True
    assert driver.license_verified is True


def test_identity_disabled_blocks_start(db: Session, settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "driver_identity_verification_enabled", False)
    driver = _driver(db)
    with pytest.raises(PermissionError, match="identity_verification_disabled"):
        DriverVerificationService().start_identity_session(db, settings, driver)
