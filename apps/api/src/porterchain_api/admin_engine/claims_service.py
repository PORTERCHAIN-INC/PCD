"""Backward-compatible re-export — prefer `support_engine.claims_service`."""

from porterchain_api.support_engine.claims_service import *
from porterchain_api.support_engine.claims_service import (
    CLAIM_TYPES,
    AdminClaimsService,
    ClaimFilters,
    claim_number,
)

__all__ = ["CLAIM_TYPES", "AdminClaimsService", "ClaimFilters", "claim_number"]
