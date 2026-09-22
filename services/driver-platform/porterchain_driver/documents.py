"""Driver documents — upload, list, compliance."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_REQUIRED_DOCS = ("license", "insurance", "vehicle_registration")
_UPLOADABLE_DOCS = _REQUIRED_DOCS + (
    "background_check",
    "training_certificate",
    "vehicle_photo",
    "abstract",
)
_FILE_ALIASES: dict[str, frozenset[str]] = {
    "license": frozenset({"license", "driver_license", "drivers_license"}),
    "insurance": frozenset({"insurance", "insurance_certificate"}),
    "vehicle_registration": frozenset({"vehicle_registration", "vehicle_reg", "registration"}),
}
_VERIFIED_FLAGS = {
    "license": "license_verified",
    "insurance": "insurance_verified",
    "vehicle_registration": "vehicle_verified",
}
_MAX_FILE_URL_CHARS = 380_000
_REUPLOAD_STATUSES = frozenset({"pending_review", "rejected", "expired"})


def _validate_file_url(file_url: str) -> str:
    url = (file_url or "").strip()
    if not url or len(url) > _MAX_FILE_URL_CHARS:
        raise ValueError("file_too_large" if url else "file_url_required")
    if url.startswith("data:image/") or url.startswith("https://") or url.startswith("http://"):
        return url
    raise ValueError("file_url_not_allowed")


def _clear_verified_flag(driver: Any, doc_type: str) -> None:
    flag = _VERIFIED_FLAGS.get(doc_type)
    if flag and hasattr(driver, flag):
        setattr(driver, flag, False)
    if doc_type == "background_check" and hasattr(driver, "background_check_status"):
        driver.background_check_status = "pending"


def _file_entry(docs: dict[str, Any], doc_type: str) -> dict[str, Any]:
    files = docs.get("files") or []
    aliases = _FILE_ALIASES.get(doc_type, frozenset({doc_type}))
    if not isinstance(files, list):
        return {}
    for file_entry in files:
        if not isinstance(file_entry, dict):
            continue
        found = str(file_entry.get("doc_type") or "").lower()
        if found not in aliases and not any(alias in found for alias in aliases):
            continue
        url = file_entry.get("file_url") or file_entry.get("url")
        if not url:
            continue
        return {
            "url": url,
            "status": file_entry.get("status") or "uploaded",
            "verified": bool(file_entry.get("verified")),
        }
    return {}


class DocumentsService:
    def pending_count(self, driver: Any) -> int:
        docs = driver.documents or {}
        count = sum(1 for key in _REQUIRED_DOCS if not docs.get(key, {}).get("verified"))
        now = datetime.now(UTC)
        for key in _REQUIRED_DOCS + ("background_check",):
            entry = docs.get(key, {})
            if isinstance(entry, dict) and entry.get("expires_at"):
                try:
                    exp = datetime.fromisoformat(entry["expires_at"].replace("Z", "+00:00"))
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=UTC)
                    if exp < now:
                        count += 1
                except ValueError:
                    pass
        return count

    def list_documents(self, driver: Any) -> list[dict]:
        docs = driver.documents or {}
        result = []
        for doc_type in _REQUIRED_DOCS + ("background_check", "training_certificate", "abstract"):
            entry = docs.get(doc_type, {})
            if not isinstance(entry, dict):
                entry = {}
            if not (entry.get("url") or entry.get("file_url")):
                entry = {**_file_entry(docs, doc_type), **entry}
            flag = _VERIFIED_FLAGS.get(doc_type)
            status = str(entry.get("status") or "")
            if flag and bool(getattr(driver, flag, False)) and status not in _REUPLOAD_STATUSES:
                entry = {**entry, "verified": True, "status": status or "verified"}
            if doc_type == "abstract" and isinstance(docs.get("abstract"), dict):
                abstract = docs["abstract"]
                if abstract.get("verified"):
                    entry = {**entry, "verified": True, "status": abstract.get("status") or "verified"}
            result.append(self._serialize_doc(doc_type, entry))
        return result

    def list_vehicle_photos(self, driver: Any) -> list[dict]:
        docs = driver.documents or {}
        photos = docs.get("vehicle_photos") or []
        if not isinstance(photos, list):
            return []
        return [
            {
                "id": p.get("id") or str(i),
                "url": p.get("url"),
                "status": p.get("status", "pending_review"),
                "uploaded_at": p.get("uploaded_at"),
                "label": p.get("label") or f"Vehicle photo {i + 1}",
            }
            for i, p in enumerate(photos)
            if isinstance(p, dict)
        ]

    def upload_document(
        self,
        db: Session,
        driver: Any,
        *,
        doc_type: str,
        file_url: str,
        metadata: dict | None = None,
    ) -> dict:
        if doc_type not in _UPLOADABLE_DOCS:
            raise ValueError(f"invalid_doc_type:{doc_type}")
        file_url = _validate_file_url(file_url)
        if doc_type == "vehicle_photo":
            return self.upload_vehicle_photo(db, driver, file_url=file_url, metadata=metadata)

        docs = dict(driver.documents or {})
        meta = metadata or {}
        docs[doc_type] = {
            "status": "pending_review",
            "verified": False,
            "url": file_url,
            "uploaded_at": datetime.now(UTC).isoformat(),
            **meta,
        }
        _clear_verified_flag(driver, doc_type)
        driver.documents = docs
        db.flush()
        return self._serialize_doc(doc_type, docs[doc_type])

    def upload_vehicle_photo(
        self,
        db: Session,
        driver: Any,
        *,
        file_url: str,
        metadata: dict | None = None,
    ) -> dict:
        file_url = _validate_file_url(file_url)
        docs = dict(driver.documents or {})
        photos = list(docs.get("vehicle_photos") or [])
        meta = metadata or {}
        photo = {
            "id": str(uuid.uuid4()),
            "url": file_url,
            "status": "pending_review",
            "uploaded_at": datetime.now(UTC).isoformat(),
            **meta,
        }
        photos.append(photo)
        docs["vehicle_photos"] = photos
        driver.documents = docs
        db.flush()
        return photo

    @staticmethod
    def _serialize_doc(doc_type: str, entry: dict) -> dict:
        labels = {
            "license": "Driver License",
            "insurance": "Insurance Certificate",
            "vehicle_registration": "Vehicle Registration",
            "background_check": "Background Check",
            "training_certificate": "Training Certificate",
            "abstract": "Ontario Driver Abstract",
        }
        return {
            "type": doc_type,
            "label": labels.get(doc_type, doc_type.replace("_", " ").title()),
            "status": entry.get("status") or ("verified" if entry.get("verified") else "missing"),
            "verified": entry.get("verified", False),
            "url": entry.get("url") or entry.get("file_url"),
            "uploaded_at": entry.get("uploaded_at"),
            "expires_at": entry.get("expires_at"),
            "rejection_reason": entry.get("rejection_reason"),
            "policy_number": entry.get("policy_number"),
            "provider": entry.get("provider"),
            "plate_number": entry.get("plate_number"),
        }
