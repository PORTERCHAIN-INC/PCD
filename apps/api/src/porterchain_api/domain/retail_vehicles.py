"""Retail vehicle catalog — enabled IDs shared by quotes, merchants, CRM."""

from __future__ import annotations

from sqlalchemy.orm import Session


def enabled_retail_vehicle_ids(db: Session) -> set[str]:
    from porterchain_api.admin_engine.settings_service import AdminSettingsService

    return AdminSettingsService().enabled_retail_vehicle_ids(db)


def validate_preferred_vehicles(db: Session, preferred: list[str]) -> list[str]:
    """Preferred vehicles must be a subset of the enabled retail catalog (M-6)."""
    from porterchain_api.domain.customer_goods import canonical_vehicle_id

    catalog = enabled_retail_vehicle_ids(db)
    cleaned: list[str] = []
    for raw in preferred:
        vid = canonical_vehicle_id(str(raw or "").strip())
        if not vid:
            continue
        if catalog and vid not in catalog:
            raise ValueError(f"preferred_vehicle_not_in_catalog:{vid}")
        if vid not in cleaned:
            cleaned.append(vid)
    return cleaned
