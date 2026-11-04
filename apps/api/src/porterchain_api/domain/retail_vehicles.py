"""Retail vehicle catalog — enabled IDs shared by quotes, merchants, CRM."""

from __future__ import annotations

from sqlalchemy.orm import Session


def enabled_retail_vehicle_ids(db: Session) -> set[str]:
    from porterchain_api.admin_engine.settings_service import AdminSettingsService

    return AdminSettingsService().enabled_retail_vehicle_ids(db)


def validate_preferred_vehicles(
    db: Session, preferred: list[str], existing: list[str] | None = None
) -> list[str]:
    """Preferred vehicles must be a subset of the enabled retail catalog (M-6).

    Vehicles already on file (``existing``) are kept even if the class was later
    disabled in the catalog, so an unrelated edit (e.g. payment terms) is not blocked.
    Only newly added vehicles are checked.
    """
    from porterchain_api.domain.customer_goods import canonical_vehicle_id

    catalog = {canonical_vehicle_id(x) for x in enabled_retail_vehicle_ids(db)}
    grandfathered = {canonical_vehicle_id(str(x or "").strip()) for x in (existing or [])}
    cleaned: list[str] = []
    for raw in preferred:
        vid = canonical_vehicle_id(str(raw or "").strip())
        if not vid:
            continue
        if catalog and vid not in catalog and vid not in grandfathered:
            raise ValueError(f"preferred_vehicle_not_in_catalog:{vid}")
        if vid not in cleaned:
            cleaned.append(vid)
    return cleaned
