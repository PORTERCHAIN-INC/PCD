"""Backward-compatible re-export — prefer `support_engine.claims_service`."""

from porterchain_api.support_engine.claims_service import *  # noqa: F403
from porterchain_api.support_engine.claims_service import (
    AdminClaimsService,
    ClaimFilters,
    CLAIM_TYPES,
    claim_number,
)

__all__ = ["AdminClaimsService", "ClaimFilters", "CLAIM_TYPES", "claim_number"]
