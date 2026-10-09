"""Proof-of-delivery + on-duty rules for completing a dropoff (readiness audit #5).

Rules (all evaluated per order at completion time):
- Every dropoff needs a photo OR a receiver signature.
- Merchant ``customer_experience.delivery_rules.signature_required`` -> signature required.
- Merchant ``delivery_rules.id_required`` -> receiver ID check required.
- Medical / pharmacy (merchant vertical ``medical``, order compliance vertical ``medical`` or a
  chain-of-custody payload) -> signature AND ID check required.
- Merchant OTP opt-in keeps its existing rule (``pod_complete`` with a valid code).
- The driver must be on an active shift (on break counts as on shift).

Kill switches (env, default ON): ``DRIVER_POD_ENFORCED=false`` restores the 2026-10-05 pause;
``DRIVER_DUTY_REQUIRED_FOR_COMPLETION=false`` drops the shift check. A super admin can finish a
stop without proof / off duty through the audited ``complete_delivery_without_proof`` override.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

PHOTO = "photo"
SIGNATURE = "signature"
ID_CHECK = "id_check"
PHOTO_OR_SIGNATURE = "photo_or_signature"

MISSING_LABELS: dict[str, str] = {
    PHOTO_OR_SIGNATURE: "a delivery photo or the receiver's signature",
    PHOTO: "a delivery photo",
    SIGNATURE: "the receiver's signature",
    ID_CHECK: "a receiver ID check",
}


def _flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def pod_enforced() -> bool:
    return _flag("DRIVER_POD_ENFORCED", True)


def duty_enforced() -> bool:
    return _flag("DRIVER_DUTY_REQUIRED_FOR_COMPLETION", True)


class PodMissing(PermissionError):
    """Dropoff completion blocked: proof still missing. ``str()`` stays ``pod_required``."""

    def __init__(self, missing: list[str]):
        super().__init__("pod_required")
        self.missing = list(missing)

    @property
    def payload(self) -> dict[str, Any]:
        return {
            "code": "pod_required",
            "missing": self.missing,
            "message": human_missing(self.missing),
        }


class DriverOffDuty(PermissionError):
    def __init__(self) -> None:
        super().__init__("driver_off_duty")

    @property
    def payload(self) -> dict[str, Any]:
        return {
            "code": "driver_off_duty",
            "message": "Start your shift before completing deliveries.",
        }


def human_missing(missing: list[str]) -> str:
    parts = [MISSING_LABELS.get(m, m) for m in missing]
    if not parts:
        return ""
    return "Capture " + " and ".join(parts) + " before completing this delivery."


def _merchant(db: Session, order: Any) -> Any:
    mid = getattr(order, "merchant_id", None)
    if not mid:
        return None
    from porterchain_api.merchant_models import Merchant

    return db.get(Merchant, mid)


def requirements_for(db: Session, order: Any, *, merchant: Any = None) -> dict[str, Any]:
    from porterchain_api.booking_engine.compliance_metadata import otp_required_at_delivery
    from porterchain_api.customer_experience.settings import cx_for_merchant

    merchant = merchant if merchant is not None else _merchant(db, order)
    rules = cx_for_merchant(merchant)["delivery_rules"]
    meta = getattr(order, "compliance_metadata", None)
    meta = meta if isinstance(meta, dict) else {}
    profile = getattr(merchant, "profile", None) if merchant is not None else None
    merchant_vertical = str((profile or {}).get("vertical") or "") if isinstance(profile, dict) else ""
    medical = (
        merchant_vertical == "medical"
        or str(meta.get("vertical") or "") == "medical"
        or bool(meta.get("chain_of_custody"))
    )
    reasons: list[str] = []
    signature = bool(rules.get("signature_required"))
    id_check = bool(rules.get("id_required"))
    if signature:
        reasons.append("merchant_signature_required")
    if id_check:
        reasons.append("merchant_id_required")
    if medical:
        signature = id_check = True
        reasons.append("pharmacy_medical")
    return {
        "enforced": pod_enforced(),
        "photo_or_signature": True,
        "photo": False,
        "signature": signature,
        "id_check": id_check,
        "otp": otp_required_at_delivery(meta),
        "reasons": reasons,
    }


def captured_types(db: Session, order_id: str) -> set[str]:
    from porterchain_api.driver_models import DriverStopMeta

    row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order_id).first()
    proofs = list((row.meta or {}).get("proofs", [])) if row else []
    return {str(p.get("type") or "") for p in proofs if isinstance(p, dict)}


def missing_for(db: Session, order: Any, *, requirements: dict[str, Any] | None = None) -> list[str]:
    req = requirements or requirements_for(db, order)
    have = captured_types(db, order.id)
    missing: list[str] = []
    if req.get("photo") and PHOTO not in have:
        missing.append(PHOTO)
    if req.get("signature") and SIGNATURE not in have:
        missing.append(SIGNATURE)
    if req.get("id_check") and ID_CHECK not in have:
        missing.append(ID_CHECK)
    if req.get("photo_or_signature") and not ({PHOTO, SIGNATURE} & have) and SIGNATURE not in missing:
        missing.insert(0, PHOTO_OR_SIGNATURE)
    return missing


def assert_pod_satisfied(db: Session, order: Any) -> None:
    if not pod_enforced():
        return
    missing = missing_for(db, order)
    if missing:
        raise PodMissing(missing)


def is_on_duty(db: Session, driver: Any) -> bool:
    from porterchain_api.driver_models import DriverShift

    return (
        db.query(DriverShift)
        .filter(DriverShift.driver_id == driver.id, DriverShift.status.in_(("active", "on_break")))
        .first()
        is not None
    )


def assert_on_duty(db: Session, driver: Any) -> None:
    if duty_enforced() and not is_on_duty(db, driver):
        raise DriverOffDuty()
