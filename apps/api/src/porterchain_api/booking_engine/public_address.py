"""Public-safe address snapshots — strip street-level PII from unauthenticated track."""

from __future__ import annotations

from typing import Any


def public_address_snapshot(addr: dict[str, Any] | None) -> dict[str, Any] | None:
    """City / region / coords only — no full street address (C-12)."""
    if not addr or not isinstance(addr, dict):
        return None
    out: dict[str, Any] = {}
    city = addr.get("city")
    if city:
        out["city"] = city
    province = addr.get("province") or addr.get("region") or addr.get("state")
    if province:
        out["province"] = province
    country = addr.get("country")
    if country:
        out["country"] = country
    postal = addr.get("postal_code") or addr.get("postal") or addr.get("zip")
    if postal and isinstance(postal, str) and len(postal) >= 3:
        # FSA / ZIP3 only — not full postal for street pinpointing.
        out["postal_code"] = postal[:3].upper() if postal[:1].isalpha() else postal[:3]
    for coord in ("lat", "lng"):
        if addr.get(coord) is not None:
            try:
                out[coord] = float(addr[coord])
            except (TypeError, ValueError):
                pass
    parts = [out[key] for key in ("city", "province", "postal_code", "country") if out.get(key)]
    if parts:
        out["formatted"] = ", ".join(str(part) for part in parts)
    return out or None
