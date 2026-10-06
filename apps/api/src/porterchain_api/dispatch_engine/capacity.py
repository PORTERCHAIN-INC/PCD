"""Fit one job to one van. A missing cap means that dimension is unlimited."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleCapacity:
    kg: float | None = None
    volume_m3: float | None = None
    pallets: float | None = None
    parcels: float | None = None


def _over(demand: float, cap: float | None) -> bool:
    if cap is None:
        return False
    return float(demand) > float(cap)


def reject_reason(
    *,
    kg: float = 0,
    volume_m3: float = 0,
    pallets: float = 0,
    parcels: float = 0,
    capacity: VehicleCapacity | None = None,
) -> str | None:
    """Return ``capacity`` when the job cannot fit. Otherwise None."""
    caps = capacity or VehicleCapacity()
    if (
        _over(kg, caps.kg)
        or _over(volume_m3, caps.volume_m3)
        or _over(pallets, caps.pallets)
        or _over(parcels, caps.parcels)
    ):
        return "capacity"
    return None
