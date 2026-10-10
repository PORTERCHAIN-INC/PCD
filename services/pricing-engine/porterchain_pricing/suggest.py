"""Booking suggestions — pure. Liftgate when items are heavy or palletised."""

from __future__ import annotations

from typing import Any

DEFAULT_LIFTGATE_KG = 70.0


def suggest_liftgate(
    parcels: list[Any] | None = None,
    *,
    weight_kg: float | None = None,
    package_type: str | None = None,
    threshold_kg: float = DEFAULT_LIFTGATE_KG,
) -> dict[str, Any]:
    """``{"suggest": bool, "reason": str}`` — any item over ``threshold_kg`` or a pallet."""
    if (package_type or "").lower() in {"pallet", "pallets", "skid"}:
        return {"suggest": True, "reason": "Pallets need a liftgate."}
    for p in parcels or []:
        kind = str(getattr(p, "package_type", None) or (p.get("package_type") if isinstance(p, dict) else "") or "")
        w = getattr(p, "weight_kg", None) if not isinstance(p, dict) else p.get("weight_kg")
        if kind.lower() in {"pallet", "skid"}:
            return {"suggest": True, "reason": "Pallets need a liftgate."}
        if w is not None and float(w) > threshold_kg:
            return {"suggest": True, "reason": f"An item is over {threshold_kg:g} kg."}
    if not parcels and weight_kg is not None and float(weight_kg) > threshold_kg:
        return {"suggest": True, "reason": f"Load is over {threshold_kg:g} kg."}
    return {"suggest": False, "reason": ""}
