"""Field stop exceptions — GTA door codes, attempts, then RTS.

Support-hub incidents (accident, breakdown) stay on IncidentService.
This module owns the stop POST /exception allowlist and attempt math only.
"""

from __future__ import annotations

from typing import Any

MAX_DELIVERY_ATTEMPTS = 2

# Retryable: stay on the stop. Terminal: fail this order. After max retryable → RTS.
STOP_EXCEPTION_TYPES: dict[str, dict[str, Any]] = {
    "customer_not_available": {
        "label": "Not home / no answer",
        "retryable": True,
        "photo_required": False,
    },
    "closed": {
        "label": "Business closed",
        "retryable": True,
        "photo_required": False,
    },
    "no_access": {
        "label": "No access (condo / dock / buzzer)",
        "retryable": True,
        "photo_required": False,
    },
    "weather_ice": {
        "label": "Weather / ice",
        "retryable": True,
        "photo_required": False,
    },
    "refused": {
        "label": "Receiver refused",
        "retryable": False,
        "photo_required": True,
    },
    "damaged_parcel": {
        "label": "Parcel damaged",
        "retryable": False,
        "photo_required": True,
    },
    "unsafe": {
        "label": "Unsafe stop",
        "retryable": False,
        "photo_required": True,
    },
    "unable_to_deliver": {
        "label": "Unable to deliver",
        "retryable": False,
        "photo_required": False,
    },
}

_ALIASES = {
    "failed_delivery": "unable_to_deliver",
    "customer_unavailable": "customer_not_available",
    "parcel_damaged": "damaged_parcel",
    "damaged": "damaged_parcel",
    "damage": "damaged_parcel",
    "access": "no_access",
    "not_home": "customer_not_available",
    "return_to_sender": "unable_to_deliver",
}


def normalize_exception_type(raw: str) -> str:
    key = (raw or "").strip().lower()
    key = _ALIASES.get(key, key)
    if key not in STOP_EXCEPTION_TYPES:
        raise ValueError("unknown_exception_type")
    return key


def exception_meta(exception_type: str) -> dict[str, Any]:
    return STOP_EXCEPTION_TYPES[normalize_exception_type(exception_type)]


def is_retryable(exception_type: str) -> bool:
    return bool(exception_meta(exception_type).get("retryable"))


def photo_required(exception_type: str) -> bool:
    return bool(exception_meta(exception_type).get("photo_required"))


def prior_attempt_rows(rows: Any) -> list[Any]:
    """MagicMock-safe: only a real list of exception rows counts."""
    if not isinstance(rows, list):
        return []
    return [row for row in rows if row is not None]


def retryable_attempt_count(rows: list[Any]) -> int:
    count = 0
    for row in rows:
        raw = getattr(row, "type", None) or (row.get("type") if isinstance(row, dict) else None)
        if not raw:
            continue
        try:
            if is_retryable(str(raw)):
                count += 1
        except ValueError:
            continue
    return count


def resolve_outcome(exception_type: str, retryable_prior: int) -> str:
    """retry | failed | return_to_sender. Attempt number is retryable_prior + 1 when retryable."""
    if not is_retryable(exception_type):
        return "failed"
    if retryable_prior + 1 >= MAX_DELIVERY_ATTEMPTS:
        return "return_to_sender"
    return "retry"
