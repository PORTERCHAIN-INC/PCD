"""Driver background screening — Checkr adapter into background_check_status.

Does not auto-approve DriverStatus. Only Checkr `clear` maps to cleared/passed.
`consider` stays for ops review.
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

PROVIDER = "checkr"
_PASSED = frozenset({"passed", "cleared", "approved"})
_CHECKR_CLEAR = frozenset({"clear"})
_CHECKR_CONSIDER = frozenset({"consider"})
_CHECKR_FAIL = frozenset({"suspended", "canceled", "cancelled", "dispute"})


class DriverBackgroundCheckService:
    def status(self, driver: Driver, settings: Settings, db: Session | None = None) -> dict[str, Any]:
        docs = driver.documents or {}
        entry = docs.get("background_check") if isinstance(docs, dict) else {}
        if not isinstance(entry, dict):
            entry = {}
        bg = (driver.background_check_status or "pending").lower()
        policy_required = True
        if db is not None:
            from porterchain_api.admin_engine.platform_settings import background_check_required

            policy_required = background_check_required(db)
        return {
            "enabled": bool(settings.driver_background_check_enabled),
            "required": policy_required,
            "mock_allowed": self._allow_mock(settings),
            "background_check_status": bg,
            "passed": bg in _PASSED,
            "provider": entry.get("provider"),
            "verification_source": entry.get("verification_source"),
            "invitation_id": entry.get("checkr_invitation_id"),
            "candidate_id": entry.get("checkr_candidate_id"),
            "report_id": entry.get("checkr_report_id"),
            "invitation_url": entry.get("invitation_url"),
            "failure_reason": entry.get("failure_reason"),
            "requires_license": True,
            "license_verified": bool(driver.license_verified),
        }

    def start_screening(
        self,
        db: Session,
        settings: Settings,
        driver: Driver,
    ) -> dict[str, Any]:
        if not settings.driver_background_check_enabled:
            raise PermissionError("background_check_disabled")
        if not driver.license_verified:
            raise PermissionError("license_verification_required")

        bg = (driver.background_check_status or "").lower()
        if bg in _PASSED:
            return {
                "status": bg,
                "passed": True,
                "mock": False,
                "already_cleared": True,
                "invitation_url": None,
            }

        if self._allow_mock(settings):
            invitation_id = f"inv_mock_{uuid.uuid4().hex[:16]}"
            candidate_id = f"cand_mock_{uuid.uuid4().hex[:12]}"
            self._store_pending(
                driver,
                invitation_id=invitation_id,
                candidate_id=candidate_id,
                invitation_url=None,
                report_id=None,
                status="pending",
            )
            db.flush()
            return {
                "invitation_id": invitation_id,
                "candidate_id": candidate_id,
                "invitation_url": None,
                "status": "pending",
                "mock": True,
                "already_cleared": False,
            }

        if not settings.checkr_api_key:
            raise RuntimeError("checkr_not_configured")

        from porterchain_services.checkr.client import CheckrClient, CheckrClientError

        client = CheckrClient(
            api_key=settings.checkr_api_key,
            base_url=settings.checkr_api_base_url,
        )
        first, last = _split_name(driver.full_name)
        try:
            candidate = client.create_candidate(
                {
                    "email": driver.email,
                    "first_name": first,
                    "last_name": last,
                    "phone": driver.phone or None,
                    "work_locations": [{"country": "CA"}],
                    "custom_id": driver.id,
                }
            )
            invitation = client.create_invitation(
                {
                    "candidate_id": candidate["id"],
                    "package": settings.checkr_package_slug,
                    "work_locations": [{"country": "CA"}],
                }
            )
        except CheckrClientError as exc:
            logger.exception("checkr_start_failed driver=%s", driver.id)
            raise RuntimeError(str(exc)) from exc

        invitation_id = str(invitation.get("id") or "")
        candidate_id = str(candidate.get("id") or "")
        invitation_url = invitation.get("invitation_url") or invitation.get("url")
        self._store_pending(
            driver,
            invitation_id=invitation_id,
            candidate_id=candidate_id,
            invitation_url=str(invitation_url) if invitation_url else None,
            report_id=None,
            status="pending",
        )
        db.flush()
        return {
            "invitation_id": invitation_id,
            "candidate_id": candidate_id,
            "invitation_url": invitation_url,
            "status": "pending",
            "mock": False,
            "already_cleared": False,
        }

    def complete_mock(
        self,
        db: Session,
        settings: Settings,
        driver: Driver,
        *,
        invitation_id: str | None = None,
        result: str = "cleared",
    ) -> dict[str, Any]:
        if not settings.driver_background_check_enabled:
            raise PermissionError("background_check_disabled")
        if not self._allow_mock(settings):
            raise PermissionError("background_check_mock_not_allowed")

        docs = driver.documents or {}
        entry = docs.get("background_check") if isinstance(docs, dict) else {}
        pending_id = None
        if isinstance(entry, dict):
            pending_id = entry.get("checkr_invitation_id")
        inv_id = invitation_id or pending_id or f"inv_mock_{uuid.uuid4().hex[:16]}"
        if not str(inv_id).startswith("inv_mock_"):
            raise ValueError("mock_invitation_required")

        status = result.lower().strip() or "cleared"
        if status not in _PASSED | {"consider", "failed", "pending"}:
            status = "cleared" if status == "clear" else "failed"

        self.apply_result(
            db,
            driver,
            status=status,
            invitation_id=str(inv_id),
            candidate_id=(entry.get("checkr_candidate_id") if isinstance(entry, dict) else None),
            report_id=f"rep_mock_{uuid.uuid4().hex[:12]}",
            failure_reason=None if status in _PASSED else f"mock_{status}",
        )
        return {
            "invitation_id": inv_id,
            "status": driver.background_check_status,
            "passed": (driver.background_check_status or "").lower() in _PASSED,
            "mock": True,
        }

    def apply_result(
        self,
        db: Session,
        driver: Driver,
        *,
        status: str,
        invitation_id: str | None = None,
        candidate_id: str | None = None,
        report_id: str | None = None,
        failure_reason: str | None = None,
    ) -> Driver:
        normalized = status.lower().strip()
        driver.background_check_status = normalized
        passed = normalized in _PASSED
        sync_portal_doc_status(
            driver,
            "background_check",
            verified=passed,
            status="verified" if passed else normalized,
        )
        docs = dict(driver.documents or {})
        entry = dict(docs.get("background_check") or {}) if isinstance(docs.get("background_check"), dict) else {}
        now = datetime.now(UTC).isoformat()
        entry.update(
            {
                "provider": PROVIDER,
                "verification_source": "auto" if passed else "auto_pending",
                "status": "verified" if passed else normalized,
                "verified": passed,
                "failure_reason": failure_reason,
                "updated_at": now,
            }
        )
        if invitation_id:
            entry["checkr_invitation_id"] = invitation_id
        if candidate_id:
            entry["checkr_candidate_id"] = candidate_id
        if report_id:
            entry["checkr_report_id"] = report_id
        if passed:
            entry["completed_at"] = now
        docs["background_check"] = entry
        driver.documents = docs
        flag_modified(driver, "documents")
        db.flush()
        return driver

    def apply_checkr_webhook(self, db: Session, event: dict[str, Any]) -> bool:
        """Map Checkr webhook payload → driver background_check_status. Returns True if updated."""
        event_type = str(event.get("type") or event.get("event") or "")
        data = event.get("data") if isinstance(event.get("data"), dict) else event
        object_payload = data.get("object") if isinstance(data.get("object"), dict) else data
        if not isinstance(object_payload, dict):
            return False

        # Prefer report.completed / invitation events that carry report status.
        report = object_payload
        if "report" in object_payload and isinstance(object_payload["report"], dict):
            report = object_payload["report"]

        checkr_status = str(report.get("status") or object_payload.get("status") or "").lower()
        if event_type in {"invitation.completed", "invitation.expired"} and not checkr_status:
            checkr_status = "pending" if "completed" in event_type else "failed"

        candidate_id = report.get("candidate_id") or object_payload.get("candidate_id")
        candidate = object_payload.get("candidate")
        if isinstance(candidate, dict):
            candidate_id = candidate_id or candidate.get("id")
            custom_id = candidate.get("custom_id")
        else:
            custom_id = None

        report_id = report.get("id") if isinstance(report, dict) else None
        if object_payload.get("object") == "report":
            report_id = object_payload.get("id") or report_id

        driver = self._find_driver(db, candidate_id=candidate_id, custom_id=custom_id, report=report)
        if not driver:
            logger.warning(
                "checkr_webhook_driver_not_found type=%s candidate=%s",
                event_type,
                candidate_id,
            )
            return False

        mapped = self._map_checkr_status(checkr_status, report=report)
        invitation_id = None
        if object_payload.get("object") == "invitation":
            invitation_id = object_payload.get("id")
        self.apply_result(
            db,
            driver,
            status=mapped,
            invitation_id=str(invitation_id) if invitation_id else None,
            candidate_id=str(candidate_id) if candidate_id else None,
            report_id=str(report_id) if report_id else None,
            failure_reason=None if mapped in _PASSED else checkr_status or event_type,
        )
        return True

    def handle_webhook(
        self,
        db: Session,
        settings: Settings,
        *,
        payload: bytes,
        signature: str | None,
        event: dict[str, Any],
    ) -> dict[str, str]:
        if not settings.driver_background_check_enabled:
            return {"status": "disabled"}
        if settings.checkr_webhook_secret:
            from porterchain_services.checkr.client import verify_webhook_signature

            if not verify_webhook_signature(payload, signature, settings.checkr_webhook_secret):
                raise PermissionError("invalid_checkr_signature")
        updated = self.apply_checkr_webhook(db, event)
        return {"status": "ok" if updated else "ignored"}

    @staticmethod
    def _allow_mock(settings: Settings) -> bool:
        if settings.app_env != "local":
            return False
        return bool(settings.checkr_mock) or not settings.checkr_api_key

    @staticmethod
    def _map_checkr_status(checkr_status: str, *, report: dict[str, Any]) -> str:
        result = str(report.get("result") or "").lower()
        status = checkr_status.lower()
        if status in _CHECKR_CLEAR or result == "clear":
            return "cleared"
        if status in _CHECKR_CONSIDER or result == "consider":
            return "consider"
        if status in _CHECKR_FAIL:
            return "failed"
        if status in {"complete", "completed"} and result in {"clear", "consider"}:
            return "cleared" if result == "clear" else "consider"
        if status in _PASSED:
            return status
        return status or "pending"

    def _find_driver(
        self,
        db: Session,
        *,
        candidate_id: str | None,
        custom_id: str | None,
        report: dict[str, Any],
    ) -> Driver | None:
        if custom_id:
            row = db.get(Driver, str(custom_id))
            if row:
                return row
        # Scan recent docs for matching Checkr ids (JSON — fine at early volume).
        if candidate_id:
            for driver in db.query(Driver).order_by(Driver.updated_at.desc()).limit(500).all():
                docs = driver.documents or {}
                entry = docs.get("background_check") if isinstance(docs, dict) else None
                if isinstance(entry, dict) and entry.get("checkr_candidate_id") == candidate_id:
                    return driver
        report_id = report.get("id")
        if report_id:
            for driver in db.query(Driver).order_by(Driver.updated_at.desc()).limit(500).all():
                docs = driver.documents or {}
                entry = docs.get("background_check") if isinstance(docs, dict) else None
                if isinstance(entry, dict) and entry.get("checkr_report_id") == report_id:
                    return driver
        return None

    @staticmethod
    def _store_pending(
        driver: Driver,
        *,
        invitation_id: str,
        candidate_id: str,
        invitation_url: str | None,
        report_id: str | None,
        status: str,
    ) -> None:
        docs = dict(driver.documents or {})
        entry = dict(docs.get("background_check") or {}) if isinstance(docs.get("background_check"), dict) else {}
        now = datetime.now(UTC).isoformat()
        entry.update(
            {
                "provider": PROVIDER,
                "verification_source": "auto_pending",
                "checkr_invitation_id": invitation_id,
                "checkr_candidate_id": candidate_id,
                "checkr_report_id": report_id,
                "invitation_url": invitation_url,
                "status": status,
                "verified": False,
                "updated_at": now,
            }
        )
        docs["background_check"] = entry
        driver.documents = docs
        driver.background_check_status = status
        flag_modified(driver, "documents")
        sync_portal_doc_status(driver, "background_check", verified=False, status=status)


def _split_name(full_name: str) -> tuple[str, str]:
    parts = (full_name or "Driver").strip().split()
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], " ".join(parts[1:])
