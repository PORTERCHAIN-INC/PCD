"""Vertical compliance payloads on orders — medical chain-of-custody + food cold chain (§8.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class _ComplianceBooking(Protocol):
    package_type: str
    custodian_name: str | None
    specimen_id: str | None
    seal_number: str | None
    requires_cold_chain: bool
    temperature_min_c: float | None
    temperature_max_c: float | None
    delivery_window_start: datetime | None
    delivery_window_end: datetime | None


def build_compliance_metadata(body: _ComplianceBooking) -> dict[str, Any] | None:
    meta: dict[str, Any] = {}

    chain: dict[str, str] = {}
    if body.custodian_name and body.custodian_name.strip():
        chain["custodian_name"] = body.custodian_name.strip()
    if body.specimen_id and body.specimen_id.strip():
        chain["specimen_id"] = body.specimen_id.strip()
    if body.seal_number and body.seal_number.strip():
        chain["seal_number"] = body.seal_number.strip()
    if chain or body.package_type == "medical":
        if chain:
            meta["chain_of_custody"] = chain
        meta["vertical"] = "medical"

    cold_required = body.requires_cold_chain or body.package_type == "foodBeverage"
    if cold_required or body.temperature_min_c is not None or body.temperature_max_c is not None:
        cold: dict[str, Any] = {"required": cold_required, "readings": []}
        if body.temperature_min_c is not None:
            cold["min_c"] = body.temperature_min_c
        if body.temperature_max_c is not None:
            cold["max_c"] = body.temperature_max_c
        meta["cold_chain"] = cold
        if meta.get("vertical") is None:
            meta["vertical"] = "food"

    if body.delivery_window_start or body.delivery_window_end:
        meta["delivery_window"] = {
            "start": body.delivery_window_start.isoformat() if body.delivery_window_start else None,
            "end": body.delivery_window_end.isoformat() if body.delivery_window_end else None,
        }
        if meta.get("vertical") is None:
            meta["vertical"] = "food"

    if bool(getattr(body, "otp_required", False)):
        proof = dict(meta.get("proof") or {})
        proof["otp_required"] = True
        meta["proof"] = proof

    return meta or None


def otp_required_at_delivery(compliance_metadata: dict[str, Any] | None) -> bool:
    """True only when the merchant opted in on the booking."""
    if not isinstance(compliance_metadata, dict):
        return False
    if compliance_metadata.get("otp_required") is True:
        return True
    proof = compliance_metadata.get("proof")
    return isinstance(proof, dict) and bool(proof.get("otp_required"))


def requires_medical_certified(compliance_metadata: dict[str, Any] | None) -> bool:
    if not isinstance(compliance_metadata, dict):
        return False
    return bool(compliance_metadata.get("chain_of_custody"))


def delivery_window_end(compliance_metadata: dict[str, Any] | None) -> datetime | None:
    if not isinstance(compliance_metadata, dict):
        return None
    window = compliance_metadata.get("delivery_window") or {}
    end = window.get("end")
    if not end:
        return None
    return datetime.fromisoformat(str(end).replace("Z", "+00:00"))


def is_temperature_excursion(compliance_metadata: dict[str, Any] | None, celsius: float) -> bool:
    if not isinstance(compliance_metadata, dict):
        return False
    cold = compliance_metadata.get("cold_chain") or {}
    if not cold.get("required"):
        return False
    min_c = cold.get("min_c")
    max_c = cold.get("max_c")
    if min_c is not None and celsius < float(min_c):
        return True
    if max_c is not None and celsius > float(max_c):
        return True
    return False


def append_temperature_reading(
    compliance_metadata: dict[str, Any] | None,
    *,
    celsius: float,
    recorded_at: datetime,
) -> dict[str, Any]:
    meta = dict(compliance_metadata or {})
    cold = dict(meta.get("cold_chain") or {"required": True, "readings": []})
    readings = list(cold.get("readings") or [])
    readings.append({"c": celsius, "at": recorded_at.isoformat()})
    cold["readings"] = readings
    meta["cold_chain"] = cold
    return meta
