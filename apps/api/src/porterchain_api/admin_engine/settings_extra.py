"""Settings keys owned outside the legacy settings service (keeps it under its line cap)."""

from __future__ import annotations

from typing import Any

from porterchain_api.platform.gps_policy import (
    default_driver_gps,
    forget_positions,
    normalize_driver_gps,
    set_policy_cache,
)
from porterchain_api.platform.compliance import (
    default_compliance,
    normalize_breaches,
    normalize_compliance,
    normalize_requests,
)
from porterchain_api.platform.future_features import default_future, normalize_future
from porterchain_pricing.cost_settings import (
    COST_DEFAULTS,
    COST_NORMALIZERS,
    COST_SECTIONS,
)


def _save_driver_gps(raw: Any) -> dict[str, Any]:
    value = normalize_driver_gps(raw)
    set_policy_cache(value)  # takes effect now, not after the cache TTL
    # Minimal retention: drop live pins now (all of them when GPS is off globally).
    forget_positions(["*"] if not value["enabled"] else value["disabled_driver_ids"])
    return value


EXTRA_SECTIONS = [
    *COST_SECTIONS,
    {"id": "driver_gps", "label": "Driver GPS", "group": "partners"},
    {"id": "future", "label": "Future", "group": "platform"},
    {"id": "privacy_access", "label": "Privacy Requests", "group": "access"},
    {"id": "compliance", "label": "Compliance", "group": "access"},
]
EXTRA_NORMALIZERS = {**COST_NORMALIZERS, "driver_gps": _save_driver_gps, "future_features": normalize_future,
    "compliance": normalize_compliance, "breach_log": normalize_breaches, "privacy_requests": normalize_requests}


def EXTRA_DEFAULTS() -> dict[str, Any]:
    return {**COST_DEFAULTS(), "driver_gps": default_driver_gps(), "future_features": default_future(),
            "compliance": default_compliance(), "breach_log": [], "privacy_requests": []}
