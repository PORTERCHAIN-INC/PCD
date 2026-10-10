"""Driver compliance expiry — revoke verification flags when docs lapse.

Called lazily from profile reads and periodically from the worker sweep.
Does not touch the driver's online state.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from porterchain_api.admin_engine.driver_documents import sync_portal_doc_status
from porterchain_api.admin_models import Driver

logger = logging.getLogger(__name__)

_DOC_FLAG_MAP = {
    "insurance": "insurance_verified",
    "vehicle_registration": "vehicle_verified",
    "license": "license_verified",
    "abstract": None,  # JSON-only verified flag
}


def _parse_expiry(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value


def is_expired(raw: str | None, *, now: datetime | None = None) -> bool:
    exp = _parse_expiry(raw)
    if exp is None:
        return False
    return exp < (now or datetime.now(UTC))


class DriverComplianceExpiryService:
    def refresh_driver(self, db: Session, driver: Driver, *, now: datetime | None = None) -> list[str]:
        """Revoke verified flags for expired insurance/registration/license/abstract."""
        clock = now or datetime.now(UTC)
        docs = dict(driver.documents or {})
        changed: list[str] = []

        for doc_key, flag_name in _DOC_FLAG_MAP.items():
            entry = docs.get(doc_key)
            if not isinstance(entry, dict):
                continue
            if not is_expired(entry.get("expires_at"), now=clock):
                continue

            already_expired = entry.get("status") == "expired" and not entry.get("verified")
            if already_expired:
                if flag_name and getattr(driver, flag_name, False):
                    setattr(driver, flag_name, False)
                    changed.append(f"{doc_key}:flag_cleared")
                continue

            entry = {**entry, "status": "expired", "verified": False, "expired_at": clock.isoformat()}
            docs[doc_key] = entry
            if flag_name and getattr(driver, flag_name, False):
                setattr(driver, flag_name, False)
            changed.append(doc_key)

        if not changed:
            return []

        driver.documents = docs
        flag_modified(driver, "documents")
        for doc_key in [c.split(":")[0] for c in changed]:
            if doc_key in _DOC_FLAG_MAP:
                sync_portal_doc_status(driver, doc_key, verified=False, status="expired")
        db.flush()
        return changed

    def sweep(self, db: Session, *, limit: int = 500) -> dict[str, Any]:
        """Periodic worker: refresh expiry flags for recently updated drivers."""
        scanned = 0
        updated = 0
        actions: list[dict[str, Any]] = []
        rows = (
            db.query(Driver)
            .order_by(Driver.updated_at.desc())
            .limit(limit)
            .all()
        )
        for driver in rows:
            scanned += 1
            changed = self.refresh_driver(db, driver)
            if changed:
                updated += 1
                actions.append({"driver_id": driver.id, "changed": changed})
        if updated:
            db.commit()
        return {"scanned": scanned, "updated": updated, "actions": actions[:50]}

    def refresh_and_commit(self, db: Session, driver: Driver) -> list[str]:
        changed = self.refresh_driver(db, driver)
        if changed:
            db.commit()
            db.refresh(driver)
        return changed
