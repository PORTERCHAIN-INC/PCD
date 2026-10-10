"""Enterprise claims management — Application Service (masterrule §3).

Claims are Porterchain business objects; logistics execution context comes from
PorterChain orders.
"""

from __future__ import annotations

from porterchain_api.domain.claims import CLAIM_TYPES, claim_number
from porterchain_api.support_engine.claims_constants import ClaimFilters
from porterchain_api.support_engine.claims_detail import ClaimsDetailMixin
from porterchain_api.support_engine.claims_helpers import ClaimsHelpersMixin
from porterchain_api.support_engine.claims_mutations import ClaimsMutationsMixin
from porterchain_api.support_engine.claims_query import ClaimsQueryMixin
from porterchain_api.support_engine.claims_smart import ClaimsSmartMixin


class AdminClaimsService(
    ClaimsHelpersMixin,
    ClaimsQueryMixin,
    ClaimsDetailMixin,
    ClaimsMutationsMixin,
    ClaimsSmartMixin,
):
    """Unified claims service composed from domain mixins."""


__all__ = ["CLAIM_TYPES", "AdminClaimsService", "ClaimFilters", "claim_number"]
