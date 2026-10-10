"""Settings keys owned by pricing cost/coverage: defaults + validators in one place."""

from __future__ import annotations

from typing import Any

from porterchain_pricing.contract_terms import default_carriage_terms, normalize_carriage_terms
from porterchain_pricing.coverage import default_coverage, normalize_coverage
from porterchain_pricing.margin import default_margin_estimates, normalize_margin_estimates

COST_NORMALIZERS = {
    "pricing_margin_estimates": normalize_margin_estimates,
    "parcel_coverage": normalize_coverage,
    "carriage_terms": normalize_carriage_terms,
}


def COST_DEFAULTS() -> dict[str, Any]:  # noqa: N802 - constant-like factory
    return {
        "pricing_margin_estimates": default_margin_estimates(),
        "parcel_coverage": default_coverage(),
        "carriage_terms": default_carriage_terms(),
    }
