"""Backward-compatible re-export — prefer `collaboration_engine.crm_service`."""

from porterchain_api.collaboration_engine.crm_service import (
    CrmSalesService,
    province_from_postal,
)

__all__ = ["CrmSalesService", "province_from_postal"]
