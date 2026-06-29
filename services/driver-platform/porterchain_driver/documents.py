"""Driver documents — upload, list, compliance."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


_REQUIRED_DOCS = ("license", "insurance", "vehicle_registration")


class DocumentsService:
    def pending_count(self, driver: Any) -> int:
        docs = driver.documents or {}
        return sum(1 for key in _REQUIRED_DOCS if not docs.get(key, {}).get("verified"))

    def list_documents(self, driver: Any) -> list[dict]:
        docs = driver.documents or {}
        result = []
        for doc_type in _REQUIRED_DOCS + ("background_check", "training_certificate"):
            entry = docs.get(doc_type, {})
            result.append(
                {
                    "type": doc_type,
                    "status": entry.get("status", "missing"),
                    "verified": entry.get("verified", False),
                    "url": entry.get("url"),
                    "uploaded_at": entry.get("uploaded_at"),
                    "expires_at": entry.get("expires_at"),
                }
            )
        return result

    def upload_document(
        self,
        db: Session,
        driver: Any,
        *,
        doc_type: str,
        file_url: str,
        metadata: dict | None = None,
    ) -> dict:
        docs = dict(driver.documents or {})
        docs[doc_type] = {
            "status": "pending_review",
            "verified": False,
            "url": file_url,
            "uploaded_at": datetime.now(UTC).isoformat(),
            **(metadata or {}),
        }
        driver.documents = docs
        db.flush()
        return docs[doc_type]
