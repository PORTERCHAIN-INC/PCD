"""Order-level helpers shared by the customer-experience modules (no engine coupling)."""

from __future__ import annotations

import copy
import re
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order

DELIVERED_STATES = frozenset({"DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"})
TERMINAL_STATES = DELIVERED_STATES | {"CANCELLED", "RETURN_TO_SENDER", "LOST", "REFUNDED", "DAMAGED"}
EN_ROUTE_STATES = frozenset({"PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"})
PRE_DISPATCH_STATES = frozenset({"BOOKED", "DISPATCH_READY", "DRIVER_ASSIGNED", "DRIVER_ACCEPTED"})


def meta_of(order: Order) -> dict[str, Any]:
    return order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}


def cx_meta(order: Order) -> dict[str, Any]:
    block = meta_of(order).get("cx")
    return block if isinstance(block, dict) else {}


def update_cx_meta(order: Order, **changes: Any) -> dict[str, Any]:
    """Copy-on-write so SQLAlchemy sees the JSON column change."""
    meta = copy.deepcopy(meta_of(order))
    block = dict(meta.get("cx") or {})
    for key, value in changes.items():
        if value is None:
            block.pop(key, None)
        else:
            block[key] = value
    meta["cx"] = block
    order.compliance_metadata = meta
    return block


def merchant_for(db: Session, order: Order):
    if not order.merchant_id:
        return None
    from porterchain_api.merchant_models import Merchant

    return db.get(Merchant, order.merchant_id)


def _clean_email(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", text) else None


def _clean_phone(value: Any) -> str | None:
    text = str(value or "").strip()
    digits = re.sub(r"\D", "", text)
    return text if 7 <= len(digits) <= 15 else None


def consignee_contacts(order: Order) -> dict[str, str | None]:
    """Receiver email/phone/name from consignee meta, then the drop-off stop snapshot."""
    meta = meta_of(order)
    consignee = meta.get("consignee") if isinstance(meta.get("consignee"), dict) else {}
    dropoff = order.dropoff if isinstance(order.dropoff, dict) else {}
    return {
        "email": _clean_email(consignee.get("email")) or _clean_email(dropoff.get("contact_email")),
        "phone": _clean_phone(consignee.get("phone")) or _clean_phone(dropoff.get("contact_phone")),
        "name": (str(consignee.get("name") or dropoff.get("contact_name") or "").strip() or None),
    }


def dest_fsa(order: Order) -> str | None:
    dropoff = order.dropoff if isinstance(order.dropoff, dict) else {}
    postal = str(dropoff.get("postal") or dropoff.get("postal_code") or "")
    fsa = re.sub(r"[^A-Z0-9]", "", postal.upper())[:3]
    return fsa or None


def is_bulky(order: Order, rules: dict[str, Any]) -> bool:
    meta = meta_of(order)
    ptype = re.sub(r"[^a-z0-9]", "", str(meta.get("package_type") or "").lower())
    vehicle = str(meta.get("vehicle_class") or "").lower()
    for token in rules.get("bulky_package_types") or []:
        if token and token.replace("_", "") in ptype:
            return True
    return bool(vehicle and vehicle in (rules.get("bulky_vehicle_classes") or []))


def mask_name(name: Any) -> str | None:
    """'Samantha Kowalski' -> 'Samantha K.' ; single names stay first-name only."""
    parts = [p for p in str(name or "").strip().split() if p]
    if not parts:
        return None
    first = parts[0][:24]
    return f"{first} {parts[-1][0].upper()}." if len(parts) > 1 else first


def mask_initials(name: Any) -> str | None:
    parts = [p for p in str(name or "").strip().split() if p]
    return " ".join(f"{p[0].upper()}." for p in parts[:3]) or None


_FR_PROVINCES = frozenset({"QC", "QUEBEC", "QUÉBEC"})


def recipient_language(order: Order, preference: str = "auto") -> str:
    """'fr' or 'en' for receiver emails. Merchant setting wins; 'auto' uses the
    recipient's stated language, then a Quebec drop-off; English otherwise."""
    pref = str(preference or "auto").lower()
    if pref in ("en", "fr"):
        return pref
    meta = meta_of(order)
    consignee = meta.get("consignee") if isinstance(meta.get("consignee"), dict) else {}
    for key in ("language", "locale", "lang"):
        val = str(consignee.get(key) or meta.get(key) or "").strip().lower()
        if val:
            return "fr" if val.startswith("fr") else "en"
    dropoff = order.dropoff if isinstance(order.dropoff, dict) else {}
    province = str(dropoff.get("province") or dropoff.get("state") or dropoff.get("region") or "").strip().upper()
    return "fr" if province in _FR_PROVINCES else "en"
