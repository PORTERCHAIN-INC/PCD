"""Driver profile — compliance snapshot, expiries, contract (read-only)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_EXPIRY_WARNING_DAYS = 30
_EXPIRY_URGENT_DAYS = 7

_DOC_LABELS = {
    "license": "Driver License",
    "insurance": "Insurance Certificate",
    "vehicle_registration": "Vehicle Registration",
    "background_check": "Background Check",
    "training_certificate": "Training Certificate",
    "abstract": "Ontario Driver Abstract",
}


class ProfileService:
    def snapshot(self, db: Session, driver: Any) -> dict[str, Any]:
        from porterchain_driver.documents import DocumentsService
        from porterchain_driver.insurance import InsuranceService
        from porterchain_driver.vehicle import VehicleService

        docs = driver.documents or {}
        vehicle = VehicleService().profile_vehicle(db, driver)
        insurance = InsuranceService().status(db, driver)
        documents = DocumentsService().list_documents(driver)
        vehicle_photos = DocumentsService().list_vehicle_photos(driver)
        expiry_dates = self._expiry_dates(driver, vehicle, docs)
        expiry_notifications = self._expiry_notifications(expiry_dates)
        abstract = docs.get("abstract") if isinstance(docs.get("abstract"), dict) else {}

        return {
            "profile": self._profile_block(driver),
            "verification": {
                "license_verified": bool(driver.license_verified),
                "insurance_verified": bool(driver.insurance_verified),
                "vehicle_verified": bool(driver.vehicle_verified),
                "background_check_status": driver.background_check_status,
                "abstract_verified": bool(abstract.get("verified")),
            },
            "license": self._license_block(driver, docs),
            "insurance": insurance,
            "registration": self._registration_block(docs),
            "background_check": self._background_block(driver, docs),
            "abstract": {
                "status": abstract.get("status")
                or ("verified" if abstract.get("verified") else "missing"),
                "verified": bool(abstract.get("verified")),
                "license_class": abstract.get("license_class"),
                "demerit_points": abstract.get("demerit_points"),
                "has_active_suspension": abstract.get("has_active_suspension"),
                "url": abstract.get("url") or abstract.get("file_url"),
                "expires_at": abstract.get("expires_at"),
                "failure_reasons": abstract.get("failure_reasons") or [],
            },
            "vehicle": vehicle,
            "maintenance_status": vehicle.get("maintenance") if vehicle else self._default_maintenance(),
            "vehicle_photos": vehicle_photos,
            "documents": documents,
            "expiry_dates": expiry_dates,
            "expiry_notifications": expiry_notifications,
            "contract": self._contract_block(driver),
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def _profile_block(self, driver: Any) -> dict[str, Any]:
        docs = driver.documents or {}
        address = docs.get("address") if isinstance(docs.get("address"), dict) else {}
        return {
            "id": driver.id,
            "full_name": driver.full_name,
            "email": driver.email,
            "phone": driver.phone,
            "status": driver.status,
            "rating": driver.rating,
            "photo_url": docs.get("photo_url"),
            "license_class": docs.get("license_class"),
            "license_number": docs.get("license_number"),
            "service_area": docs.get("service_area"),
            "province": address.get("province") or docs.get("province"),
            "city": address.get("city") or docs.get("city"),
            "fleetbase_driver_id": driver.fleetbase_driver_id,
        }

    def _license_block(self, driver: Any, docs: dict) -> dict[str, Any]:
        entry = docs.get("license") or {}
        if not isinstance(entry, dict):
            entry = {}
        return {
            "verified": bool(driver.license_verified),
            "class": docs.get("license_class"),
            "number": docs.get("license_number"),
            "status": entry.get("status", "missing"),
            "url": entry.get("url"),
            "expires_at": entry.get("expires_at"),
            "uploaded_at": entry.get("uploaded_at"),
        }

    def _registration_block(self, docs: dict) -> dict[str, Any]:
        entry = docs.get("vehicle_registration") or {}
        if not isinstance(entry, dict):
            entry = {}
        return {
            "status": entry.get("status", "missing"),
            "verified": entry.get("verified", False),
            "url": entry.get("url"),
            "plate_number": entry.get("plate_number"),
            "expires_at": entry.get("expires_at"),
            "uploaded_at": entry.get("uploaded_at"),
        }

    def _background_block(self, driver: Any, docs: dict) -> dict[str, Any]:
        entry = docs.get("background_check") or {}
        if not isinstance(entry, dict):
            entry = {}
        status = driver.background_check_status or "pending"
        passed = status in ("passed", "cleared", "approved")
        return {
            "status": status,
            "passed": passed,
            "url": entry.get("url"),
            "completed_at": entry.get("completed_at") or entry.get("uploaded_at"),
            "expires_at": entry.get("expires_at"),
        }

    def _contract_block(self, driver: Any) -> dict[str, Any]:
        docs = driver.documents or {}
        perf = driver.performance or {}
        raw = docs.get("contract") if isinstance(docs.get("contract"), dict) else None
        if not raw:
            raw = perf.get("contract") if isinstance(perf.get("contract"), dict) else {}
        if not raw:
            return {
                "has_contract": False,
                "read_only": True,
                "message": "No active contractor agreement on file. Contact support for contract details.",
            }
        return {
            "has_contract": True,
            "read_only": True,
            "contract_name": raw.get("contract_name") or raw.get("name"),
            "contract_type": raw.get("contract_type", "independent_contractor"),
            "effective_from": raw.get("effective_from"),
            "effective_to": raw.get("effective_to"),
            "pay_model": raw.get("pay_model"),
            "minimum_guarantee_cents": raw.get("minimum_guarantee_cents"),
            "terms_url": raw.get("terms_url"),
            "notes": raw.get("notes"),
        }

    def _expiry_dates(self, driver: Any, vehicle: dict | None, docs: dict) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for doc_type, label in _DOC_LABELS.items():
            entry = docs.get(doc_type)
            if isinstance(entry, dict) and entry.get("expires_at"):
                items.append(
                    self._expiry_item(label, entry["expires_at"], category=doc_type, reference_id=doc_type)
                )
        if vehicle and vehicle.get("compliance_expires_at"):
            items.append(
                self._expiry_item(
                    "Vehicle compliance",
                    vehicle["compliance_expires_at"],
                    category="vehicle_compliance",
                    reference_id=vehicle.get("id"),
                )
            )
        maintenance = (vehicle or {}).get("maintenance") or docs.get("vehicle_maintenance") or {}
        if isinstance(maintenance, dict) and maintenance.get("next_service_due"):
            items.append(
                self._expiry_item(
                    "Vehicle maintenance",
                    maintenance["next_service_due"],
                    category="maintenance",
                    reference_id=vehicle.get("id") if vehicle else None,
                )
            )
        contract = self._contract_block(driver)
        if contract.get("has_contract") and contract.get("effective_to"):
            items.append(
                self._expiry_item(
                    "Contract",
                    contract["effective_to"],
                    category="contract",
                    reference_id="contract",
                )
            )
        return sorted(items, key=lambda x: (x["days_until"] if x["days_until"] is not None else 9999))

    def _expiry_item(
        self, label: str, expires_at: str, *, category: str, reference_id: str | None
    ) -> dict[str, Any]:
        days = self._days_until(expires_at)
        severity = "ok"
        if days is not None:
            if days < 0:
                severity = "expired"
            elif days <= _EXPIRY_URGENT_DAYS:
                severity = "urgent"
            elif days <= _EXPIRY_WARNING_DAYS:
                severity = "warning"
        return {
            "label": label,
            "category": category,
            "reference_id": reference_id,
            "expires_at": expires_at,
            "days_until": days,
            "severity": severity,
        }

    def _expiry_notifications(self, expiry_dates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                **item,
                "message": self._notification_message(item),
            }
            for item in expiry_dates
            if item.get("severity") in ("expired", "urgent", "warning")
        ]

    @staticmethod
    def _notification_message(item: dict[str, Any]) -> str:
        label = item.get("label", "Document")
        days = item.get("days_until")
        if days is not None and days < 0:
            return f"{label} expired {abs(days)} day(s) ago — upload renewal immediately."
        if days == 0:
            return f"{label} expires today — renew before your next shift."
        if days is not None and days <= _EXPIRY_URGENT_DAYS:
            return f"{label} expires in {days} day(s) — renewal required soon."
        return f"{label} expires in {days} day(s) — plan renewal."

    @staticmethod
    def _days_until(iso: str) -> int | None:
        try:
            exp = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            now = datetime.now(UTC)
            return (exp.date() - now.date()).days
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _default_maintenance() -> dict[str, Any]:
        return {
            "status": "unknown",
            "last_service_at": None,
            "next_service_due": None,
            "odometer_km": None,
            "notes": None,
        }
