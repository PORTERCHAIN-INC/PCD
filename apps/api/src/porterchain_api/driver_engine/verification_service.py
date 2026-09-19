"""Driver identity verification — Stripe Identity adapter into existing license flags.

Buy commodity IDV; PorterChain owns verification state via sync_portal_doc_status.
Does not auto-approve DriverStatus — admin_approval stays human.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from porterchain_api.admin_engine.driver_documents import sync_portal_doc_status
from porterchain_api.admin_models import Driver
from porterchain_api.config import Settings

logger = logging.getLogger(__name__)

PROVIDER = "stripe_identity"
PURPOSE = "driver_license"


class DriverVerificationService:
    def start_identity_session(
        self,
        db: Session,
        settings: Settings,
        driver: Driver,
    ) -> dict[str, Any]:
        if not settings.driver_identity_verification_enabled:
            raise PermissionError("identity_verification_disabled")

        return_url = settings.driver_identity_return_url or (
            f"{settings.driver_portal_url.rstrip('/')}/profile?identity=return"
        )

        if settings.allow_stripe_mock:
            session_id = f"vs_mock_{uuid.uuid4().hex[:16]}"
            self._store_license_session(
                driver,
                session_id=session_id,
                status="requires_input",
                verified=False,
            )
            db.flush()
            return {
                "session_id": session_id,
                "url": None,
                "client_secret": None,
                "status": "requires_input",
                "mock": True,
                "enabled": True,
            }

        if not settings.stripe_secret:
            raise RuntimeError("stripe_not_configured")

        from porterchain_api.services.stripe_service import create_identity_verification_session

        session = create_identity_verification_session(
            settings,
            driver_id=driver.id,
            return_url=return_url,
        )
        self._store_license_session(
            driver,
            session_id=session["id"],
            status=str(session.get("status") or "requires_input"),
            verified=False,
        )
        db.flush()
        return {
            "session_id": session["id"],
            "url": session.get("url"),
            "client_secret": session.get("client_secret"),
            "status": session.get("status"),
            "mock": False,
            "enabled": True,
        }

    def complete_mock_identity(
        self,
        db: Session,
        settings: Settings,
        driver: Driver,
        *,
        session_id: str | None = None,
        verified: bool = True,
    ) -> dict[str, Any]:
        if not settings.driver_identity_verification_enabled:
            raise PermissionError("identity_verification_disabled")
        if not settings.allow_stripe_mock:
            raise PermissionError("stripe_mock_not_allowed")

        docs = driver.documents or {}
        license_entry = docs.get("license") if isinstance(docs, dict) else None
        pending_id = None
        if isinstance(license_entry, dict):
            pending_id = license_entry.get("stripe_verification_session_id")
        sid = session_id or pending_id or f"vs_mock_{uuid.uuid4().hex[:16]}"
        if not str(sid).startswith("vs_mock_"):
            raise ValueError("mock_session_required")

        self.apply_identity_session(
            db,
            driver,
            session_id=str(sid),
            verified=verified,
            status="verified" if verified else "requires_input",
            failure_reason=None if verified else "mock_rejected",
        )
        return {
            "session_id": sid,
            "verified": verified,
            "license_verified": bool(driver.license_verified),
            "mock": True,
        }

    def apply_identity_session(
        self,
        db: Session,
        driver: Driver,
        *,
        session_id: str,
        verified: bool,
        status: str,
        failure_reason: str | None = None,
        document_summary: dict[str, Any] | None = None,
    ) -> Driver:
        """Map provider result onto Driver.license_verified + portal docs (no commit)."""
        driver.license_verified = verified
        sync_portal_doc_status(
            driver,
            "license",
            verified=verified,
            status="verified" if verified else (status or "pending_review"),
        )
        self._store_license_session(
            driver,
            session_id=session_id,
            status="verified" if verified else status,
            verified=verified,
            failure_reason=failure_reason,
            document_summary=document_summary,
        )
        db.flush()
        return driver

    def apply_stripe_identity_event(self, db: Session, session_obj: dict[str, Any]) -> bool:
        """Handle identity.verification_session.* payload. Returns True if a driver was updated."""
        meta = session_obj.get("metadata") or {}
        if meta.get("purpose") and meta.get("purpose") != PURPOSE:
            return False
        driver_id = meta.get("porterchain_driver_id")
        session_id = session_obj.get("id")
        if not driver_id or not session_id:
            logger.warning("identity_session_missing_driver_or_id session=%s", session_id)
            return False

        driver = db.get(Driver, driver_id)
        if not driver:
            logger.warning("identity_session_driver_not_found driver_id=%s", driver_id)
            return False

        status = str(session_obj.get("status") or "requires_input")
        verified = status == "verified"
        last_error = session_obj.get("last_error") or {}
        failure_reason = None
        if isinstance(last_error, dict):
            failure_reason = last_error.get("reason") or last_error.get("code")
        elif last_error:
            failure_reason = str(last_error)

        doc_summary = None
        verified_outputs = session_obj.get("verified_outputs") or {}
        if isinstance(verified_outputs, dict) and verified_outputs.get("document"):
            document = verified_outputs["document"]
            if isinstance(document, dict):
                doc_summary = {
                    "type": document.get("type"),
                    "number": document.get("number"),
                    "expiration_date": document.get("expiration_date"),
                    "issued_date": document.get("issued_date"),
                    "issuing_country": document.get("issuing_country"),
                }

        self.apply_identity_session(
            db,
            driver,
            session_id=str(session_id),
            verified=verified,
            status=status,
            failure_reason=None if verified else failure_reason,
            document_summary=doc_summary,
        )
        return True

    def status(self, driver: Driver, settings: Settings) -> dict[str, Any]:
        docs = driver.documents or {}
        license_entry = docs.get("license") if isinstance(docs, dict) else {}
        if not isinstance(license_entry, dict):
            license_entry = {}
        return {
            "enabled": bool(settings.driver_identity_verification_enabled),
            "mock_allowed": bool(settings.allow_stripe_mock),
            "license_verified": bool(driver.license_verified),
            "provider": license_entry.get("provider"),
            "verification_source": license_entry.get("verification_source"),
            "session_id": license_entry.get("stripe_verification_session_id"),
            "status": license_entry.get("status") or ("verified" if driver.license_verified else "pending"),
            "failure_reason": license_entry.get("failure_reason"),
        }

    @staticmethod
    def _store_license_session(
        driver: Driver,
        *,
        session_id: str,
        status: str,
        verified: bool,
        failure_reason: str | None = None,
        document_summary: dict[str, Any] | None = None,
    ) -> None:
        docs = dict(driver.documents or {})
        entry = dict(docs.get("license") or {}) if isinstance(docs.get("license"), dict) else {}
        now = datetime.now(UTC).isoformat()
        entry.update(
            {
                "provider": PROVIDER,
                "verification_source": "auto" if verified else "auto_pending",
                "stripe_verification_session_id": session_id,
                "status": status,
                "verified": verified,
                "failure_reason": failure_reason,
                "updated_at": now,
            }
        )
        if verified:
            entry["verified_at"] = now
        if document_summary:
            entry["document"] = document_summary
            if document_summary.get("number"):
                entry["reference_number"] = document_summary["number"]
            exp = document_summary.get("expiration_date")
            if isinstance(exp, dict):
                y, m, d = exp.get("year"), exp.get("month"), exp.get("day")
                if y and m and d:
                    entry["expires_at"] = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            elif isinstance(exp, str):
                entry["expires_at"] = exp
        docs["license"] = entry
        driver.documents = docs
        flag_modified(driver, "documents")
