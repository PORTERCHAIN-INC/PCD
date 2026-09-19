"""Ontario driver abstract attestation — rule evaluation (no MTO scrape).

Drivers submit structured abstract fields + file URL. Rules decide pass/fail.
MTO Authorized Requester / partner API can replace attestation later.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from porterchain_api.admin_engine.driver_documents import sync_portal_doc_status
from porterchain_api.admin_models import Driver
from porterchain_api.config import Settings

logger = logging.getLogger(__name__)

PROVIDER = "ontario_abstract"
PORTAL_KEY = "abstract"

# Full G + commercial classes commonly used for capacity work. Graduated G1/G2 rejected.
_DEFAULT_ALLOWED_CLASSES = frozenset({"G", "A", "B", "C", "D", "E", "F"})
_REJECTED_CLASSES = frozenset({"G1", "G2", "M1", "M2", "L", "N"})


class DriverAbstractService:
    def status(self, driver: Driver, settings: Settings) -> dict[str, Any]:
        docs = driver.documents or {}
        entry = docs.get(PORTAL_KEY) if isinstance(docs, dict) else {}
        if not isinstance(entry, dict):
            entry = {}
        return {
            "enabled": bool(settings.driver_abstract_verification_enabled),
            "verified": bool(entry.get("verified")),
            "status": entry.get("status") or ("verified" if entry.get("verified") else "missing"),
            "license_class": entry.get("license_class"),
            "demerit_points": entry.get("demerit_points"),
            "has_active_suspension": entry.get("has_active_suspension"),
            "file_url": entry.get("url") or entry.get("file_url"),
            "expires_at": entry.get("expires_at"),
            "failure_reasons": entry.get("failure_reasons") or [],
            "provider": entry.get("provider"),
            "max_demerits": settings.driver_abstract_max_demerits,
            "allowed_classes": sorted(self._allowed_classes(settings)),
        }

    def submit(
        self,
        db: Session,
        settings: Settings,
        driver: Driver,
        *,
        file_url: str,
        license_class: str,
        demerit_points: int,
        has_active_suspension: bool,
        expires_at: str | None = None,
        issued_at: str | None = None,
        reference_number: str | None = None,
    ) -> dict[str, Any]:
        if not settings.driver_abstract_verification_enabled:
            raise PermissionError("abstract_verification_disabled")
        if not (file_url or "").strip():
            raise ValueError("abstract_file_url_required")

        normalized_class = _normalize_class(license_class)
        points = max(0, int(demerit_points))
        suspended = bool(has_active_suspension)
        reasons = self.evaluate_rules(
            settings,
            license_class=normalized_class,
            demerit_points=points,
            has_active_suspension=suspended,
        )
        verified = len(reasons) == 0
        status = "verified" if verified else "rejected"
        now = datetime.now(UTC).isoformat()

        docs = dict(driver.documents or {})
        entry = dict(docs.get(PORTAL_KEY) or {}) if isinstance(docs.get(PORTAL_KEY), dict) else {}
        entry.update(
            {
                "provider": PROVIDER,
                "verification_source": "rules",
                "status": status,
                "verified": verified,
                "url": file_url.strip(),
                "file_url": file_url.strip(),
                "license_class": normalized_class,
                "demerit_points": points,
                "has_active_suspension": suspended,
                "expires_at": expires_at,
                "issued_at": issued_at,
                "reference_number": reference_number,
                "failure_reasons": reasons,
                "uploaded_at": now,
                "updated_at": now,
            }
        )
        if verified:
            entry["verified_at"] = now
        docs[PORTAL_KEY] = entry
        driver.documents = docs
        flag_modified(driver, "documents")
        sync_portal_doc_status(driver, PORTAL_KEY, verified=verified, status=status)
        # Mirror class onto license block for ops visibility.
        license_entry = dict(docs.get("license") or {}) if isinstance(docs.get("license"), dict) else {}
        if normalized_class:
            license_entry["class"] = normalized_class
            docs["license"] = license_entry
            driver.documents = docs
            flag_modified(driver, "documents")
        db.flush()
        return self.status(driver, settings)

    def evaluate_rules(
        self,
        settings: Settings,
        *,
        license_class: str,
        demerit_points: int,
        has_active_suspension: bool,
    ) -> list[str]:
        reasons: list[str] = []
        allowed = self._allowed_classes(settings)
        if not license_class:
            reasons.append("license_class_missing")
        elif license_class in _REJECTED_CLASSES:
            reasons.append("license_class_graduated_or_learner")
        elif license_class not in allowed:
            reasons.append("license_class_not_allowed")
        if demerit_points > int(settings.driver_abstract_max_demerits):
            reasons.append("demerit_points_exceeded")
        if has_active_suspension:
            reasons.append("active_suspension")
        return reasons

    @staticmethod
    def _allowed_classes(settings: Settings) -> frozenset[str]:
        raw = (settings.driver_abstract_allowed_classes or "").strip()
        if not raw:
            return _DEFAULT_ALLOWED_CLASSES
        return frozenset(_normalize_class(part) for part in raw.split(",") if part.strip())


def _normalize_class(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]", "", (value or "").upper())
    return token
