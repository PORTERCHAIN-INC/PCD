"""Driver personal profile (name, address, emergency contact, photo).

Stored on ``driver.performance["personal"]`` (same JSON pattern as app_settings, no migration).
Email and phone are NOT editable here: they change in Clerk with a verification code, then
``sync_identity`` copies the verified primary values onto the driver row.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

PROVINCES = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
_POSTAL = re.compile(r"^[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z] ?\d[ABCEGHJ-NPRSTV-Z]\d$", re.I)
_PHONE = re.compile(r"^\+[1-9]\d{7,14}$")
_PHOTO = re.compile(r"^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$")
MAX_PHOTO_CHARS = 700_000  # ~500 KB image; clients resize to 512px first
RELATIONSHIPS = {"spouse", "partner", "parent", "child", "sibling", "friend", "other"}


class ProfileValidationError(ValueError):
    def __init__(self, field: str, code: str):
        super().__init__(f"{field}:{code}")
        self.field = field
        self.code = code


def normalize_phone(raw: Any) -> str | None:
    if raw in (None, ""):
        return None
    digits = re.sub(r"[^\d+]", "", str(raw))
    if digits and not digits.startswith("+"):
        digits = "+1" + digits if len(digits) == 10 else "+" + digits
    return digits if _PHONE.match(digits) else None


def _text(raw: Any, field: str, *, max_len: int, required: bool = False) -> str | None:
    if raw is None:
        if required:
            raise ProfileValidationError(field, "required")
        return None
    if not isinstance(raw, str):
        raise ProfileValidationError(field, "invalid")
    value = " ".join(raw.split())
    if required and not value:
        raise ProfileValidationError(field, "required")
    if len(value) > max_len:
        raise ProfileValidationError(field, "too_long")
    return value or None


def clean_address(raw: Any) -> dict | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ProfileValidationError("address", "invalid")
    out = {
        "line1": _text(raw.get("line1"), "address.line1", max_len=120, required=True),
        "line2": _text(raw.get("line2"), "address.line2", max_len=120),
        "city": _text(raw.get("city"), "address.city", max_len=80, required=True),
        "province": (_text(raw.get("province"), "address.province", max_len=2, required=True) or "").upper(),
        "postal_code": (_text(raw.get("postal_code"), "address.postal_code", max_len=7, required=True) or "").upper(),
        "country": "CA",
    }
    if out["province"] not in PROVINCES:
        raise ProfileValidationError("address.province", "invalid")
    if not _POSTAL.match(out["postal_code"]):
        raise ProfileValidationError("address.postal_code", "invalid")
    pc = out["postal_code"].replace(" ", "")
    out["postal_code"] = f"{pc[:3]} {pc[3:]}"
    return out


def clean_emergency(raw: Any) -> dict | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ProfileValidationError("emergency_contact", "invalid")
    phone = normalize_phone(raw.get("phone"))
    if not phone:
        raise ProfileValidationError("emergency_contact.phone", "invalid")
    rel = str(raw.get("relationship") or "other").lower()
    if rel not in RELATIONSHIPS:
        raise ProfileValidationError("emergency_contact.relationship", "invalid")
    return {
        "name": _text(raw.get("name"), "emergency_contact.name", max_len=120, required=True),
        "relationship": rel,
        "phone": phone,
    }


def clean_photo(raw: Any) -> str | None:
    if raw in (None, ""):
        return None
    if not isinstance(raw, str) or len(raw) > MAX_PHOTO_CHARS:
        raise ProfileValidationError("photo", "too_large" if isinstance(raw, str) else "invalid")
    if not _PHOTO.match(raw):
        raise ProfileValidationError("photo", "invalid")
    return raw


def _emergency(driver: Any) -> dict | None:
    """Single source of truth shared with /support/emergency-contact: driver.documents."""
    c = (driver.documents or {}).get("emergency_contact")
    if not isinstance(c, dict) or not c.get("phone"):
        return None
    return {"name": c.get("name"), "relationship": c.get("relationship") or "other", "phone": c.get("phone")}


def read_profile(driver: Any) -> dict:
    personal = (driver.performance or {}).get("personal") or {}
    return {
        "id": driver.id,
        "full_name": driver.full_name,
        "email": driver.email,
        "phone": driver.phone,
        "address": personal.get("address"),
        "emergency_contact": _emergency(driver),
        "photo_url": personal.get("photo"),
        "updated_at": personal.get("updated_at"),
        "identity_managed_by": "clerk",
    }


EDITABLE = {"full_name", "address", "emergency_contact", "photo"}
IDENTITY_FIELDS = {"email", "phone"}


def update_profile(db: Any, driver: Any, body: dict) -> tuple[dict, list[str]]:
    """Partial update. Returns (profile, changed_field_names). Raises ProfileValidationError."""
    if not isinstance(body, dict):
        raise ProfileValidationError("body", "invalid")
    for key in IDENTITY_FIELDS & body.keys():
        raise ProfileValidationError(key, "verify_via_identity")
    unknown = set(body) - EDITABLE
    if unknown:
        raise ProfileValidationError(sorted(unknown)[0], "unknown_field")

    perf = dict(driver.performance or {})
    personal = dict(perf.get("personal") or {})
    changed: list[str] = []
    if "full_name" in body:
        name = _text(body["full_name"], "full_name", max_len=120, required=True)
        if len(name or "") < 2:
            raise ProfileValidationError("full_name", "too_short")
        if name != driver.full_name:
            driver.full_name = name
            changed.append("full_name")
    if "emergency_contact" in body:
        value = clean_emergency(body["emergency_contact"])
        if value != _emergency(driver):
            docs = dict(driver.documents or {})
            if value:
                docs["emergency_contact"] = {**value, "updated_at": datetime.now(timezone.utc).isoformat()}
            else:
                docs.pop("emergency_contact", None)
            driver.documents = docs
            changed.append("emergency_contact")
    for key, cleaner, store in (
        ("address", clean_address, "address"),
        ("photo", clean_photo, "photo"),
    ):
        if key in body:
            value = cleaner(body[key])
            if value != personal.get(store):
                personal[store] = value
                changed.append(key)
    if changed:
        personal["updated_at"] = datetime.now(timezone.utc).isoformat()
        perf["personal"] = personal
        driver.performance = perf
        db.flush()
    return read_profile(driver), changed


def verified_primary_phone(clerk_user: dict) -> str | None:
    primary_id = clerk_user.get("primary_phone_number_id")
    for entry in clerk_user.get("phone_numbers") or []:
        if entry.get("id") == primary_id and (entry.get("verification") or {}).get("status") == "verified":
            return normalize_phone(entry.get("phone_number"))
    return None


def sync_identity(db: Any, driver: Any, *, email: str | None, phone: str | None) -> list[str]:
    """Copy Clerk-verified primary email/phone onto the driver. Only verified values arrive here."""
    changed: list[str] = []
    if email and email != (driver.email or "").lower():
        driver.email = email
        changed.append("email")
    if phone and phone != driver.phone:
        driver.phone = phone
        changed.append("phone")
    if changed:
        db.flush()
    return changed


def driver_for_clerk_user(db: Any, clerk_user_id: str) -> Any:
    from porterchain_api.admin_models import Driver

    return db.query(Driver).filter(Driver.clerk_user_id == clerk_user_id).first()


def audit_self_change(db: Any, driver_id: str, action: str, fields: list[str]) -> None:
    """Field names only: no personal values in the audit trail (PIPEDA data minimisation)."""
    from porterchain_api.admin_models import AdminAuditLog

    db.add(
        AdminAuditLog(
            actor_user_id=None,
            action=action,
            resource_type="driver",
            resource_id=driver_id,
            payload={"actor": "driver_self", "fields": fields},
        )
    )
