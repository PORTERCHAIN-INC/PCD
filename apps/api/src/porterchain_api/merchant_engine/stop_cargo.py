"""Shared stop + parcel helpers for single book and route import.

``packages`` table is SoT (labels/scans). ``compliance_metadata.stops[].packages``
is a Fleetbase projection cache written by PackageService.project_packages_onto_stops —
not a second cargo authority.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def iso_dt(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def clean_packages(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    packages: list[dict[str, Any]] = []
    for pkg in raw:
        if not isinstance(pkg, dict):
            continue
        packages.append(
            {
                "id": pkg.get("id"),
                "name": pkg.get("name") or pkg.get("sku") or "Parcel",
                "sku": pkg.get("sku"),
                "quantity": pkg.get("quantity") or 1,
                "weight_kg": pkg.get("weight_kg"),
                "length_cm": pkg.get("length_cm"),
                "width_cm": pkg.get("width_cm"),
                "height_cm": pkg.get("height_cm"),
                "dimensions": pkg.get("dimensions"),
                "notes": pkg.get("notes"),
                "package_type": pkg.get("package_type"),
            }
        )
    return packages


def meaningful_packages(raw: Any) -> list[dict[str, Any]]:
    """Drop blank default rows so an untouched book does not persist empty cargo."""
    out: list[dict[str, Any]] = []
    for pkg in clean_packages(raw):
        name = str(pkg.get("name") or "").strip()
        has_name = bool(name) and name.lower() not in {"parcel", "package"}
        if (
            pkg.get("weight_kg")
            or pkg.get("length_cm")
            or pkg.get("width_cm")
            or pkg.get("height_cm")
            or pkg.get("sku")
            or pkg.get("notes")
            or pkg.get("dimensions")
            or has_name
        ):
            out.append(pkg)
    return out


def legacy_cargo(stops: list[dict[str, Any]]) -> tuple[float | None, str | None]:
    groups: dict[str, int] = {}
    total = 0.0
    found = False
    for stop in stops:
        for pkg in stop.get("packages") or []:
            if not isinstance(pkg, dict):
                continue
            found = True
            total += float(pkg.get("weight_kg") or 0)
            spec = str(pkg.get("dimensions") or "parcel")
            groups[spec] = groups.get(spec, 0) + 1
    if not found:
        return None, None
    dimensions = " | ".join(f"{count}x [{spec}]" for spec, count in groups.items())
    return round(total, 3), dimensions or None


def write_legacy_cargo(cfg: dict[str, Any], stops: list[dict[str, Any]]) -> None:
    weight_kg, dimensions = legacy_cargo(stops)
    if weight_kg is not None:
        cfg["weight_kg"] = weight_kg
    if dimensions:
        cfg["dimensions"] = dimensions


def _is_pickup(stop: dict[str, Any]) -> bool:
    kind = str(stop.get("stop_type") or stop.get("type") or "").strip().lower()
    return kind in {"pickup", "pick", "pu", "origin"}


def fleetbase_stop(stop: dict[str, Any]) -> dict[str, Any]:
    kind = "pickup" if _is_pickup(stop) else "dropoff"
    sequence = stop.get("sequence")
    payload: dict[str, Any] = {
        "id": stop.get("id") or f"pc-stop-{sequence}",
        "type": kind,
        "sequence": sequence,
        "formatted": stop.get("formatted") or stop.get("address"),
        "address": stop.get("formatted") or stop.get("address"),
        "lat": stop.get("lat"),
        "lng": stop.get("lng"),
        "postal_code": stop.get("postal") or stop.get("postal_code"),
        "city": stop.get("city"),
        "province": stop.get("province") or "ON",
        "notes": stop.get("notes"),
        "packages": clean_packages(stop.get("packages")),
        "time_window_start": iso_dt(stop.get("time_window_start")),
        "time_window_end": iso_dt(stop.get("time_window_end")),
    }
    return payload


def _addr_fields(addr: Any) -> dict[str, Any]:
    if hasattr(addr, "model_dump"):
        data = addr.model_dump()
    elif isinstance(addr, dict):
        data = addr
    else:
        data = {}
    formatted = str(data.get("formatted") or data.get("address") or "")
    return {
        "formatted": formatted,
        "address": formatted,
        "lat": data.get("lat"),
        "lng": data.get("lng"),
        "postal": data.get("postal"),
    }


def book_stops_for_request(body: Any) -> list[dict[str, Any]]:
    """Two-stop (plus extras) cargo for a merchant A→B book."""
    packages = meaningful_packages(
        [p.model_dump() if hasattr(p, "model_dump") else p for p in (getattr(body, "packages", None) or [])]
    )
    # Bulk / merchant-api often send weight_kg with no packages[] — one box so labels/scan work.
    if not packages:
        weight = getattr(body, "weight_kg", None)
        if weight is not None and str(weight).strip() != "":
            packages = [
                {
                    "name": "Parcel",
                    "weight_kg": weight,
                    "quantity": 1,
                    "package_type": getattr(body, "package_type", None),
                }
            ]
    pickup = {
        **_addr_fields(body.pickup),
        "sequence": 1,
        "stop_type": "pickup",
        "packages": packages,
        "time_window_start": iso_dt(getattr(body, "pickup_window_start", None)),
        "time_window_end": iso_dt(getattr(body, "pickup_window_end", None)),
    }
    extras: list[dict[str, Any]] = []
    for i, stop in enumerate(getattr(body, "additional_stops", None) or []):
        extras.append(
            {
                **_addr_fields(stop),
                "sequence": i + 2,
                "stop_type": "drop",
                "packages": [],
            }
        )
    dropoff = {
        **_addr_fields(body.dropoff),
        "sequence": 2 + len(extras),
        "stop_type": "drop",
        "packages": [],
    }
    return [pickup, *extras, dropoff]


def cargo_dims_for_pricing(body: Any) -> dict[str, float] | str | None:
    """Largest L×W×H from parcels, or explicit body.dimensions, for size_weight."""
    explicit = getattr(body, "dimensions", None)
    if isinstance(explicit, dict):
        return explicit
    if isinstance(explicit, str) and explicit.strip():
        return explicit
    best: dict[str, float] | None = None
    best_vol = -1.0
    for stop in book_stops_for_request(body):
        for pkg in stop.get("packages") or []:
            if not isinstance(pkg, dict):
                continue
            try:
                l = float(pkg.get("length_cm") or 0)
                w = float(pkg.get("width_cm") or 0)
                h = float(pkg.get("height_cm") or 0)
            except (TypeError, ValueError):
                continue
            if l <= 0 or w <= 0 or h <= 0:
                raw = pkg.get("dimensions")
                if isinstance(raw, dict):
                    try:
                        l = float(raw.get("length") or raw.get("length_cm") or 0)
                        w = float(raw.get("width") or raw.get("width_cm") or 0)
                        h = float(raw.get("height") or raw.get("height_cm") or 0)
                    except (TypeError, ValueError):
                        continue
                elif isinstance(raw, str) and "x" in raw.lower():
                    return raw
                else:
                    continue
            vol = l * w * h
            if vol > best_vol:
                best_vol = vol
                best = {"length": l, "width": w, "height": h}
    return best


def cargo_rollup(body: Any) -> tuple[float | None, dict[str, float] | str | None]:
    weight, _legacy_dims = legacy_cargo(book_stops_for_request(body))
    explicit_weight = getattr(body, "weight_kg", None)
    dims = cargo_dims_for_pricing(body)
    return (
        explicit_weight if explicit_weight is not None else weight,
        dims,
    )


def pickup_stop(stops: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    if not isinstance(stops, list):
        return None
    pickups = [s for s in stops if isinstance(s, dict) and _is_pickup(s)]
    if pickups:
        return sorted(pickups, key=lambda s: int(s.get("sequence") or 0))[0]
    first = stops[0] if stops and isinstance(stops[0], dict) else None
    return first


def packages_from_stops(stops: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    first = pickup_stop(stops)
    if not first:
        return []
    return meaningful_packages(first.get("packages"))
