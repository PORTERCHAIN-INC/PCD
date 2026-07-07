"""Driver documents — upload, list, compliance."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_REQUIRED_DOCS = ("license", "insurance", "vehicle_registration")
_UPLOADABLE_DOCS = _REQUIRED_DOCS + ("background_check", "training_certificate", "vehicle_photo")


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
        for doc_type in _REQUIRED_DOCS + ("background_check", "training_certificate"):
            entry = docs.get(doc_type, {})
            if not isinstance(entry, dict):
                entry = {}
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
        }
        return {
            "type": doc_type,
            "label": labels.get(doc_type, doc_type.replace("_", " ").title()),
            "status": entry.get("status", "missing"),
            "verified": entry.get("verified", False),
            "url": entry.get("url"),
            "uploaded_at": entry.get("uploaded_at"),
            "expires_at": entry.get("expires_at"),
            "policy_number": entry.get("policy_number"),
            "provider": entry.get("provider"),
            "plate_number": entry.get("plate_number"),
        }
