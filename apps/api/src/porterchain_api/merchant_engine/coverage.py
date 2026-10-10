"""Merchant coverage — service area and assigned vehicles (not a merchant fleet)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.domain.catalog_labels import vehicle_label
from porterchain_api.merchant_models import Merchant

DEFAULT_SERVICE_AREA = "Ontario"
SERVICE_AREA_NOTE = (
    "Pickup and drop-off must be in Ontario (postal codes starting with K, L, M, N, or P)."
)
COVERAGE_NOTE = (
    "PorterChain sends the vehicle. You book a class for the job — you do not manage a fleet."
)


def profile_service_area(merchant: Merchant) -> str | None:
    profile = getattr(merchant, "profile", None)
    if not isinstance(profile, dict):
        return None
    raw = profile.get("service_area")
    text = str(raw).strip() if raw else ""
    return text or None


def _zone_codes(merchant: Merchant) -> list[str]:
    codes: list[str] = []
    for raw in getattr(merchant, "delivery_zones", None) or []:
        code = str(raw or "").strip()
        if code and code not in codes:
            codes.append(code)
    return codes


def _vehicle_ids(merchant: Merchant) -> list[str]:
    ids: list[str] = []
    for raw in getattr(merchant, "preferred_vehicles", None) or []:
        vid = str(raw or "").strip()
        if vid and vid not in ids:
            ids.append(vid)
    return ids


def coverage_snapshot(merchant: Merchant, db: Session | None = None) -> dict[str, Any]:
    """Read-only picture for Settings, session, and book. Admin owns the writes."""
    label = profile_service_area(merchant)
    if not label and db is not None:
        from porterchain_api.crm_models import CrmCompany

        company = db.query(CrmCompany).filter(CrmCompany.merchant_id == merchant.id).first()
        if company and company.service_area:
            label = str(company.service_area).strip() or None
    codes = _zone_codes(merchant)
    names: dict[str, str] = {}
    if db is not None and codes:
        from porterchain_api.admin_models import PricingZone

        for zone in db.query(PricingZone).filter(PricingZone.code.in_(codes)).all():
            names[zone.code] = zone.name
    vehicles = [{"id": vid, "label": vehicle_label(vid)} for vid in _vehicle_ids(merchant)]
    return {
        "service_area": label or DEFAULT_SERVICE_AREA,
        "service_area_note": SERVICE_AREA_NOTE,
        "delivery_zones": [{"code": code, "name": names.get(code, code)} for code in codes],
        "assigned_vehicles": vehicles,
        "assigned_vehicle_ids": [v["id"] for v in vehicles],
        "coverage_note": COVERAGE_NOTE,
    }


def apply_coverage(
    merchant: Merchant,
    *,
    service_area: object = None,
    delivery_zones: object = None,
) -> list[str]:
    """Admin-owned. Omitted keys stay. Empty string / [] clears."""
    changed: list[str] = []
    if service_area is not None:
        text = str(service_area).strip() or None
        if text and len(text) > 128:
            raise ValueError("service_area is too long")
        raw_profile = getattr(merchant, "profile", None)
        profile = dict(raw_profile) if isinstance(raw_profile, dict) else {}
        if profile.get("service_area") != text:
            profile["service_area"] = text
            merchant.profile = profile
            changed.append("service_area")
    if delivery_zones is not None:
        if not isinstance(delivery_zones, list):
            raise ValueError("delivery_zones must be a list")
        cleaned: list[str] = []
        for raw in delivery_zones:
            code = str(raw or "").strip()
            if not code:
                continue
            if len(code) > 64:
                raise ValueError("delivery_zone is too long")
            if code not in cleaned:
                cleaned.append(code)
            if len(cleaned) > 32:
                raise ValueError("too many delivery zones")
        if list(getattr(merchant, "delivery_zones", None) or []) != cleaned:
            merchant.delivery_zones = cleaned or None
            changed.append("delivery_zones")
    return changed


def recommend_vehicle(
    merchant: Merchant,
    *,
    weight_kg: float | None = None,
    package_type: str | None = None,
) -> dict[str, Any]:
    """Capacity-first recommendation; preferred_vehicles only soft-rank among eligible (M-23)."""
    from porterchain_pricing.catalog import VEHICLE_MINIMUM_CENTS, WEIGHT_THRESHOLD_KG

    from porterchain_api.domain.customer_goods import persist_vehicle_class

    preferred = [persist_vehicle_class(v) for v in _vehicle_ids(merchant)]
    candidates: list[str] = []
    for key in VEHICLE_MINIMUM_CENTS:
        cid = persist_vehicle_class(key)
        if cid not in candidates:
            candidates.append(cid)

    if package_type in ("ltlPallet", "ftlLoad"):
        capacity_pick = "box_20" if "box_20" in candidates else candidates[-1]
    elif package_type == "furniture":
        capacity_pick = "sprinter_van" if "sprinter_van" in candidates else "cargo_van"
    elif weight_kg and weight_kg > 1000:
        capacity_pick = "box_20" if "box_20" in candidates else "box_16"
    elif weight_kg and weight_kg > WEIGHT_THRESHOLD_KG:
        capacity_pick = "sprinter_van" if "sprinter_van" in candidates else "cargo_van"
    elif weight_kg and weight_kg > 50:
        capacity_pick = "cargo_van" if "cargo_van" in candidates else "sprinter_van"
    else:
        capacity_pick = preferred[0] if preferred and preferred[0] in candidates else "sedan_suv"
        if capacity_pick not in candidates:
            capacity_pick = "cargo_van" if "cargo_van" in candidates else candidates[0]

    try:
        floor_idx = candidates.index(capacity_pick)
    except ValueError:
        floor_idx = 0
    eligible = candidates[floor_idx:]

    recommended = capacity_pick
    for pref in preferred:
        if pref in eligible:
            recommended = pref
            break

    coverage = coverage_snapshot(merchant)
    return {
        "recommended_vehicle": recommended,
        "preferred_vehicles": preferred,
        "assigned_vehicles": coverage["assigned_vehicles"],
        "eligible_vehicles": eligible,
        "alternatives": [v for v in eligible if v != recommended][:3],
        "service_area": coverage["service_area"],
        "coverage_note": coverage["coverage_note"],
    }
